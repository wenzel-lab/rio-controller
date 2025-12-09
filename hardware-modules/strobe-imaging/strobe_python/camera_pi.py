#import time
import io
import threading
import picommon
from pistrobecam import PiStrobeCam
from PIL import Image

class Camera(object):
    thread = None
    frame = None
#    last_access = 0
    
    def __init__( self, exit_event, socketio ):
      print( "Init Camera Pi -------------------" )
      self.exit_event = exit_event
      self.close_request = False
      self.socketio = socketio
      self.strobe_cam = PiStrobeCam( picommon.PORT_STROBE, 0.1 )
      self.camera = self.strobe_cam.camera
      
      self.strobe_data = { 'hold':0, 'enable':0, 'wait_ns':0, 'period_ns':100000, 'framerate':0, 'cam_read_time_us':0 }
      self.strobe_period_ns = int( self.strobe_data['period_ns'] )
      valid = self.strobe_cam.strobe.set_enable( self.strobe_data['enable'] )
      self.strobe_cam.strobe.set_hold( self.strobe_data['hold'] )
#      self.strobe_cam.strobe.set_timing( self.strobe_data['wait_ns'], self.strobe_period_ns )
      self.set_timing()
      self.enabled = valid
      
      self.cam_read_time_us = 0
      
      self.cam_data = { 'camera': 'rpi', 'status': '' }
      
      @self.socketio.on( 'cam' )
      def on_cam( data ):
        self.on_cam( data )

      @self.socketio.on( 'strobe' )
      def on_strobe( data ):
        self.on_strobe( data )

    def initialize( self ):
        if self.thread is None:
            # start background frame thread
            self.thread = threading.Thread( target=self._thread )
            self.thread.daemon = True
            self.thread.start()
            
            # wait until frames start to be available
            while self.frame is None:
#                time.sleep(0)
              pass

    def get_frame( self ):
#      self.last_access = time.time()
      if self.close_request:
        return None
      else:
        self.initialize()
        return self.frame
    
    def save( self ):
      img=Image.open( io.BytesIO( self.frame ) )
      img.save( "/home/pi/snapshots/snapshot.jpg", "JPEG" )
#      self.strobe_cam.camera.capture( "snapshot.jpg" )
    
#    @classmethod
    def _thread( self ):
#        with picamera.PiCamera() as camera:
#        with self.camera as camera:
            # camera setup
#            self.camera.resolution = ( 320, 240 )
            self.camera.resolution = ( 1024, 768 )
#            self.camera.hflip = True
#            self.camera.vflip = True
            self.camera.awb_mode = 'auto'
            self.camera.exposure_mode = 'off'
            #ISO will not adjust gains when exposure_mode='off'
            #self.camera.iso = 800

            # let camera warm up
#            camera.start_preview()
#            time.sleep(2)

            stream = io.BytesIO()
            for foo in self.camera.capture_continuous( stream, 'jpeg', use_video_port=True ):
                # store frame
                stream.seek(0)
                self.frame = stream.read()

                # reset stream for next frame
                stream.seek(0)
                stream.truncate()

#                time.sleep( 0.1 )
                
                # if there hasn't been any clients asking for frames in
                # the last 10 seconds stop the thread
#                if time.time() - self.last_access > 10:
#                  print( "Stop Camera thread" )
#                  break
                if self.exit_event.isSet() or self.close_request:
                  print( "Pi Camera thread exiting" )
                  break
            self.camera.close()
            self.thread_copy = self.thread
            self.thread = None
#            self.close_request = False
    
    def close( self ):
      self.close_request = True
      
      while self.thread != None:
        pass
      
      self.thread_copy.join()
      print( "Pi Camera thread exited" )
      
    def emit( self ):
      self.socketio.emit( 'cam', self.cam_data )
      self.socketio.emit( 'strobe', self.strobe_data )
    
    def set_timing( self ):
      try:
        self.strobe_period_ns = min( self.strobe_period_ns, 16000000 )
        valid = self.strobe_cam.set_timing( 32, self.strobe_period_ns, 20000000 )
        self.optimize_fps_btn_enabled = True
        if valid:
          self.enabled = True
      except:
        pass
    
    def optimize_fps( self ):
      get_cam_read_time_us = 10000
      get_cam_read_time_us_prev = 0
      strobe_post_padding_ns = 1000000
      tries = 10
      while ( abs( get_cam_read_time_us - get_cam_read_time_us_prev ) > 1000 ):
        get_cam_read_time_us_prev = get_cam_read_time_us
        self.strobe_cam.set_timing( 32, self.strobe_period_ns, strobe_post_padding_ns )
        #print( "strobe wait={}ns, strobe period={}ns, strobe padding={}ns".format( self.strobe_cam.strobe_wait_ns, self.strobe_cam.strobe_period_ns, strobe_post_padding_ns ) )
        valid, get_cam_read_time_us = self.strobe_cam.strobe.get_cam_read_time();
        #print( "get_cam_read_time_us={}".format( get_cam_read_time_us ) )
        strobe_post_padding_ns = ( get_cam_read_time_us + 100 ) * 1000
        
        tries = tries - 1
        if tries <= 0:
          break
    
    def update( self ):
      valid, cam_read_time_us = self.strobe_cam.strobe.get_cam_read_time()
      if valid:
        self.cam_read_time_us = cam_read_time_us
      
      self.strobe_framerate = int( self.strobe_cam.camera.framerate )
#      self.strobe_time_text = "{} us".format( round( float( self.strobe_cam.strobe_period_ns ) / 1000, 3 ) )
    
    def update_strobe_data( self ):
      self.update()
      self.strobe_data['cam_read_time_us'] = self.cam_read_time_us
#      self.strobe_data['strobe_time_text'] = self.strobe_time_text
#      self.strobe_data['wait_ns'] = wait_ns
      self.strobe_data['period_ns'] = self.strobe_period_ns
      self.strobe_data['framerate'] = self.strobe_framerate
    
    def on_strobe( self, data ):
      if ( data['cmd'] == 'hold' ):
        hold_on = 1 if ( data['parameters']['on'] != 0 ) else 0
        valid = self.strobe_cam.strobe.set_hold( hold_on )
        self.strobe_data['hold'] = hold_on
      elif ( data['cmd'] == 'enable' ):
        enabled = data['parameters']['on'] != 0
        valid = self.strobe_cam.strobe.set_enable( enabled )
        self.strobe_data['enable'] = enabled
      elif ( data['cmd'] == 'timing' ):
#        wait_ns = int( data['parameters']['wait_ns'] )
        period_ns = int( data['parameters']['period_ns'] )
#        valid = self.strobe_cam.set_timing( 32, period_ns, 20000000 )
        self.strobe_period_ns = period_ns
        self.set_timing()
      
      self.update_strobe_data()
      self.socketio.emit( 'strobe', self.strobe_data )
    
    def on_cam( self, data ):
      if ( data['cmd'] == 'snapshot' ):
        print( "Snapshot" )
        self.save()
      elif ( data['cmd'] == 'optimize' ):
        print( "Optimize FPS" )
        self.optimize_fps()
      
      self.update_strobe_data()
      self.socketio.emit( 'strobe', self.strobe_data )
    
