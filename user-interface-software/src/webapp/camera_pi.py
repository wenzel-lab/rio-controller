#import time
import io
import threading
import picommon
from pistrobecam import PiStrobeCam
from PIL import Image
from datetime import datetime

class Camera(object):
    thread = None
    frame = None
#    last_access = 0
    
    def __init__( self, exit_event, socketio ):
      print( "Init Camera ----------------------" )
      self.exit_event = exit_event
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
      
      self.cam_data = { 'camera': 'none', 'status': '' }
      
      # ROI storage (x, y, width, height) in image coordinates
      self.roi = None
      
      @self.socketio.on( 'cam' )
      def on_cam( data ):
        self.on_cam( data )

      @self.socketio.on( 'strobe' )
      def on_strobe( data ):
        self.on_strobe( data )
      
      @self.socketio.on( 'roi' )
      def on_roi( data ):
        self.on_roi( data )

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
      self.initialize()
      return self.frame
    
    def save( self ):
      img=Image.open( io.BytesIO( self.frame ))
      current_time =  datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
      new_file_name = "snapshot_" + current_time + ".jpg"
      folder_path = "home/pi/snapshots/"
      img.save(folder_path + "/" + new_file_name, "JPEG")
#      self.strobe_cam.camera.capture( "snapshot.jpg" )
    
#    @classmethod
    def _thread( self ):
#        with picamera.PiCamera() as camera:
#        with self.camera as camera:
            # Camera setup using new abstraction
            self.camera.set_config({
                "Width": 1024,
                "Height": 768,
                "FrameRate": 30
            })
            self.camera.start()

            # Use new camera abstraction - generate_frames() returns JPEG bytes
            for frame_data in self.camera.generate_frames():
                # store frame (frame_data is already JPEG bytes)
                self.frame = frame_data

#                time.sleep( 0.1 )
                
                # if there hasn't been any clients asking for frames in
                # the last 10 seconds stop the thread
#                if time.time() - self.last_access > 10:
#                  print( "Stop Camera thread" )
#                  break
                if self.exit_event.isSet():
                  print( "Pi Camera thread exiting" )
                  break
            self.camera.close()
            self.thread = None
    
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
      
      # Get framerate from camera config (new abstraction)
      self.strobe_framerate = int( self.strobe_cam.camera.config.get("FrameRate", 30) )
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
    
    def on_roi( self, data ):
      """
      Handle ROI WebSocket commands
      
      Commands:
        - 'set': Set ROI coordinates
        - 'get': Get current ROI
        - 'clear': Clear ROI
      """
      if ( data['cmd'] == 'set' ):
        params = data['parameters']
        self.roi = {
          'x': int(params.get('x', 0)),
          'y': int(params.get('y', 0)),
          'width': int(params.get('width', 0)),
          'height': int(params.get('height', 0))
        }
        print( f"ROI set: ({self.roi['x']}, {self.roi['y']}) {self.roi['width']}×{self.roi['height']}" )
        # Echo back to all clients
        self.socketio.emit( 'roi', { 'roi': self.roi } )
      elif ( data['cmd'] == 'get' ):
        # Send current ROI
        if self.roi:
          self.socketio.emit( 'roi', { 'roi': self.roi } )
        else:
          self.socketio.emit( 'roi', { 'roi': None } )
      elif ( data['cmd'] == 'clear' ):
        self.roi = None
        print( "ROI cleared" )
        self.socketio.emit( 'roi', { 'roi': None } )
    
    def get_roi( self ):
      """
      Get current ROI coordinates
      
      Returns:
        tuple: (x, y, width, height) or None if not set
      """
      if self.roi:
        return (self.roi['x'], self.roi['y'], self.roi['width'], self.roi['height'])
      return None
    
