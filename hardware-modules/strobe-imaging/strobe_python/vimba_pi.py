import time
import io
import threading
import cv2
from typing import Optional
from vimba import *
import multithreading_opencv as mako

def get_camera(camera_id: Optional[str]) -> Camera:
    with Vimba.get_instance() as vimba:
        if camera_id:
            try:
                return vimba.get_camera_by_id(camera_id)

            except VimbaCameraError:
                abort('Failed to access Camera \'{}\'. Abort.'.format(camera_id))

        else:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')

            return cams[0]


def setup_camera(cam: Camera):
    with cam:
        # Enable auto exposure time setting if camera supports it
        try:
            cam.ExposureAuto.set('Continuous')

        except (AttributeError, VimbaFeatureError):
            pass

        # Enable white balancing if camera supports it
        try:
            cam.BalanceWhiteAuto.set('Continuous')

        except (AttributeError, VimbaFeatureError):
            pass

        # Try to adjust GeV packet size. This Feature is only available for GigE - Cameras.
        try:
            cam.GVSPAdjustPacketSize.run()

            while not cam.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass

        # Query available, open_cv compatible pixel formats
        # prefer color formats over monochrome formats
        cv_fmts = intersect_pixel_formats(cam.get_pixel_formats(), OPENCV_PIXEL_FORMATS)
        color_fmts = intersect_pixel_formats(cv_fmts, COLOR_PIXEL_FORMATS)

        if color_fmts:
            cam.set_pixel_format(color_fmts[0])

        else:
            mono_fmts = intersect_pixel_formats(cv_fmts, MONO_PIXEL_FORMATS)

            if mono_fmts:
                cam.set_pixel_format(mono_fmts[0])

            else:
                abort('Camera does not support a OpenCV compatible format natively. Abort.')


class Handler:
    def __init__(self):
        self.shutdown_event = threading.Event()
        self.img = None
        self.frame = None

    def __call__(self, cam: Camera, frame: Frame):
        ENTER_KEY_CODE = 13

        key = cv2.waitKey(1)
        if key == ENTER_KEY_CODE:
            self.shutdown_event.set()
            return

        elif frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            msg = 'Stream from \'{}\'. Press <Enter> to stop stream.'
            img = frame.as_opencv_image()
            ( flag, encodedImage ) = cv2.imencode( ".jpg", img )
            self.img = img
            self.frame = bytearray(encodedImage)
#            cv2.imshow( msg.format( cam.get_name() ), img )
#            cv2.imshow( "Image", img )

        cam.queue_frame(frame)


class Camera(object):
    thread = None  # background thread that reads frames from camera
    frame = None  # current frame is stored here by background thread
    last_access = 0  # time of last client access to the camera
    
#    handler = None
    handler = Handler()
    
    mako_thread = None
    
    def init2(self):
      print ( "Init2 ********************************" )
      self.mako_thread = mako.MainThread()
      self.mako_thread.start()
#      self.mako_thread.join()
    
    def initialize(self):
      if Camera.thread is None:
          # start background frame thread
          Camera.thread = threading.Thread(target=self._thread)
          Camera.thread.start()
          
    def get_frame(self):
#        Camera.last_access = time.time()
#        cv2.imshow( "Image", self.handler.img )
#        print( "Here 1" )
#        return self.handler.frame
        if self.mako_thread.consumer.frame:
          frame = self.mako_thread.consumer.frame
        else:
          frame = 0
        return frame

    @classmethod
    def _thread(cls):
      with Vimba.get_instance():
        with get_camera(False) as cam:
            setup_camera(cam)
#            Camera.handler = Handler()
            feat = cam.get_feature_by_name( "LineSelector" )
            feat.set( "Line3" )
            feat = cam.get_feature_by_name( "LineSource" )
            feat.set( "ExposureActive" )
            feat = cam.get_feature_by_name( "ExposureTime" )
            feat.set( 1000000 / 30 )
            
            try:
                # Start Streaming with a custom a buffer of 10 Frames (defaults to 5)
                cam.start_streaming(handler=cls.handler, buffer_count=10)
                cls.handler.shutdown_event.wait()

            finally:
                cam.stop_streaming()
