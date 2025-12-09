"""
MAKO Camera Implementation
Based on tested MakoCamera code from flow-microscopy-platform

Uses Vimba library for Allied Vision MAKO cameras
"""

import cv2
import time
from typing import Callable, Optional, Dict, Tuple, Generator
import numpy as np
from queue import Queue
from threading import Event

from .camera_base import BaseCamera

try:
    from vimba import (
        Vimba,
        Camera,
        Frame,
        FrameStatus,
        VimbaCameraError,
        VimbaFeatureError,
    )
    VIMBA_AVAILABLE = True
except ImportError:
    VIMBA_AVAILABLE = False
    Camera = None
    Frame = None


class MakoCamera(BaseCamera):
    """
    MAKO Camera implementation using Vimba library
    
    Based on tested code from flow-microscopy-platform/module-user_interface/webapp/plugins/devices/mako_camera/core.py
    """
    
    def __init__(self, cam_id: Optional[str] = None):
        super().__init__()
        
        if not VIMBA_AVAILABLE:
            raise RuntimeError(
                "Vimba library not available. Install with: pip install vimba-python"
            )
        
        self.cam_id = cam_id
        self.cam: Optional[Camera] = None
        
        # Initialize threading components (from tested code)
        self.cam_running_event = Event()
        self.capture_flag = Event()
        self.capture_queue = Queue(1)
        
        # Get camera instance
        with Vimba.get_instance():
            self.cam = self.get_camera(self.cam_id)
            if self.cam is None:
                raise RuntimeError("Failed to initialize MAKO camera")
    
    def get_camera(self, cam_id: Optional[str] = None) -> Optional[Camera]:
        """
        Get camera instance by ID or first available
        
        Based on tested implementation from flow-microscopy-platform
        """
        try:
            with Vimba.get_instance() as vimba:
                if cam_id:
                    try:
                        return vimba.get_camera_by_id(cam_id)
                    except VimbaCameraError:
                        print(f"Failed to access Camera '{cam_id}'. Abort.")
                        return None
                else:
                    cams = vimba.get_all_cameras()
                    if not cams:
                        print("No MAKO cameras accessible. Abort.")
                        return None
                    return cams[0]
        except Exception as e:
            print(f"Error getting MAKO camera: {e}")
            return None
    
    def start(self) -> None:
        """Start camera"""
        if self.cam is None:
            raise RuntimeError("Camera not initialized")
        
        # Camera is started when generate_frames is called
        pass
    
    def stop(self) -> None:
        """Stop camera"""
        self.cam_running_event.clear()
        if self.cam:
            try:
                self.cam.stop_streaming()
            except:
                pass
    
    def generate_frames(self, config: Optional[Dict] = None) -> Generator:
        """
        Generate frames (generator) - for streaming
        
        Based on tested implementation from flow-microscopy-platform
        Returns JPEG-encoded frames for web streaming
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")
        
        try:
            with Vimba.get_instance():
                with self.cam:
                    self.setup_camera(config)
                    self.cam_running_event.set()
                    
                    try:
                        while self.cam_running_event.is_set():
                            # Call frame callback if set (for strobe trigger)
                            if self.frame_callback:
                                self.frame_callback()
                            
                            # Get frame (from tested code)
                            frame: Frame = self.cam.get_frame()
                            
                            # Convert to OpenCV image (from tested code)
                            opencv_image = frame.as_opencv_image()
                            
                            # Encode as JPEG
                            _, buffer = cv2.imencode(".jpg", opencv_image)
                            
                            # Handle capture request
                            if self.capture_flag.is_set():
                                self.capture_queue.put(buffer)
                                self.capture_flag.clear()
                            
                            yield buffer.tobytes()
                    finally:
                        self.stop()
        except VimbaCameraError as e:
            print(f"MAKO camera error: {e}")
            yield b''
    
    def get_frame_array(self) -> np.ndarray:
        """
        Get single frame as numpy array
        
        Returns:
            numpy.ndarray: Frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")
        
        with Vimba.get_instance():
            with self.cam:
                frame: Frame = self.cam.get_frame()
                opencv_image = frame.as_opencv_image()
                # Vimba returns BGR, convert to RGB
                rgb_image = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2RGB)
                return rgb_image
    
    def get_frame_roi(self, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Get ROI frame using software cropping
        
        Args:
            roi: (x, y, width, height) tuple
        
        Returns:
            numpy.ndarray: ROI frame as RGB numpy array
        """
        if self.cam is None:
            raise RuntimeError("Camera not initialized")
        
        x, y, width, height = roi
        
        # Capture full frame
        frame = self.get_frame_array()
        
        # Crop ROI: frame[y:y+h, x:x+w]
        roi_frame = frame[y:y+height, x:x+width]
        
        return roi_frame
    
    def setup_camera(self, config: Optional[Dict] = None):
        """
        Setup camera configuration
        
        Based on tested implementation from flow-microscopy-platform
        """
        if self.cam is None:
            return
        
        if config:
            # Update resolution if specified
            if "Width" in config:
                try:
                    self.cam.Width.set(int(config["Width"]))
                except VimbaFeatureError:
                    pass
            if "Height" in config:
                try:
                    self.cam.Height.set(int(config["Height"]))
                except VimbaFeatureError:
                    pass
            if "FrameRate" in config:
                try:
                    self.cam.AcquisitionFrameRate.set(float(config["FrameRate"]))
                except VimbaFeatureError:
                    pass
    
    def set_config(self, configs: Dict):
        """
        Update camera configuration
        """
        # Configuration is applied in setup_camera
        self.config.update(configs)
    
    def close(self):
        """Cleanup and close camera"""
        self.stop()
        self.cam = None
    
    def list_features(self) -> list:
        """
        List available camera features for UI
        
        Based on tested implementation from flow-microscopy-platform
        """
        features = []
        if self.cam is None:
            return features
        
        try:
            with Vimba.get_instance():
                with self.cam:
                    for feature in self.cam.get_all_features():
                        try:
                            feature_dict = {
                                "name": feature.get_name(),
                                "display_name": feature.get_display_name(),
                                "tooltip": feature.get_tooltip(),
                                "description": feature.get_description(),
                                "type": str(feature.get_type()),
                                "access_mode": feature.get_access_mode(),
                            }
                            
                            # Try to get value and range
                            try:
                                feature_dict["value"] = feature.get()
                            except:
                                pass
                            
                            try:
                                feature_dict["range"] = feature.get_range()
                            except:
                                pass
                            
                            try:
                                feature_dict["flags"] = feature.get_flags()
                            except:
                                pass
                            
                            features.append(feature_dict)
                        except:
                            pass
        except VimbaCameraError:
            pass
        
        return features

