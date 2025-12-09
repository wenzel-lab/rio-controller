from pistrobe import PiStrobe
import RPi.GPIO as GPIO
import time
import sys
import os

# Add droplet_detection to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from droplet_detection import create_camera, BaseCamera

class PiStrobeCam:
    strobe_wait_ns = 0
    strobe_period_ns = 0
    framerate_set = 0
    TRIGGER_GPIO_PIN = 18  # GPIO pin for PIC trigger
    
    def __init__( self, port, reply_pause_s, trigger_gpio_pin=18 ):
        self.strobe = PiStrobe( port, reply_pause_s )
        self.trigger_gpio_pin = trigger_gpio_pin
        
        # Use new camera abstraction (auto-detects 32-bit vs 64-bit)
        self.camera: BaseCamera = create_camera()
        
        # Configure camera (from tested code patterns)
        self.camera.set_config({
            "Width": 640,
            "Height": 480,
            "FrameRate": 30
        })
        
        # Initialize GPIO for PIC trigger (software-triggered mode)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_gpio_pin, GPIO.OUT)
        GPIO.output(self.trigger_gpio_pin, GPIO.LOW)
        
        # Configure strobe for hardware trigger mode (PIC waits for GPIO trigger)
        self.strobe.set_trigger_mode( True )  # Hardware trigger mode
        
        # Set frame callback for strobe trigger
        self.camera.set_frame_callback(self.frame_callback_trigger)
    
    def frame_callback_trigger( self ):
        """
        Frame callback - triggers PIC via GPIO pin.
        Called on each frame capture (software callback has ~1-5ms jitter,
        but PIC hardware timing is still precise).
        """
        # Generate short pulse to PIC T1G input (hardware trigger)
        GPIO.output( self.trigger_gpio_pin, GPIO.HIGH )
        time.sleep( 0.000001 )  # 1us pulse (PIC detects edge)
        GPIO.output( self.trigger_gpio_pin, GPIO.LOW )
    
    def set_timing( self, pre_padding_ns, strobe_period_ns, post_padding_ns ):
        """
        Set strobe timing - camera is master, strobe follows
        
        For hardware trigger mode, timing is simpler:
        - Camera runs at configured framerate
        - Frame callback triggers PIC via GPIO
        - PIC generates strobe pulse with specified timing
        """
        # For hardware trigger mode, timing is simpler
        # Camera is master - just set strobe timing parameters
        wait_ns = pre_padding_ns  # Delay after trigger before strobe fires
        
        valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing( wait_ns, strobe_period_ns )
        
        if valid:
            # Configure camera (simpler - no complex calculations needed)
            shutter_speed_us = int( ( strobe_period_ns + pre_padding_ns + post_padding_ns ) / 1000 )
            framerate = 1000000 / shutter_speed_us
            if ( framerate > 60 ):
                framerate = 60
            
            # Update camera configuration using new abstraction
            self.camera.set_config({
                "FrameRate": framerate,
                "ShutterSpeed": shutter_speed_us
            })
            
            # Start camera (if not already started)
            self.camera.start()
            
            # Enable strobe (will wait for GPIO trigger from frame callback)
            self.strobe.set_enable( True )
            
            self.framerate_set = framerate
        
        return valid
    
    def get_frame_roi( self, roi ):
        """
        Get ROI frame for droplet detection
        
        Args:
            roi: (x, y, width, height) tuple
        
        Returns:
            numpy.ndarray: ROI frame
        """
        return self.camera.get_frame_roi( roi )
        
    def close( self ):
        self.strobe.set_enable( False )
        self.strobe.set_hold( False )
        if self.camera:
            self.camera.close()
        