class CameraBase(object):
    def __init__( self, exit_event, socketio ):
      print( "Init Camera Base -----------------" )
      self.socketio = socketio
      self.cam_data = { 'camera': 'none', 'status': '' }
      self.strobe_data = {}
      
      @self.socketio.on( 'cam' )
      def on_cam( data ):
        pass
      
      @self.socketio.on( 'strobe' )
      def on_strobe( data ):
        pass
      
    def get_frame( self ):
      return None
    
    def close( self ):
      pass
      
    def emit( self ):
      self.socketio.emit( 'cam', self.cam_data )
      self.socketio.emit( 'strobe', self.strobe_data )
    
    def update_strobe_data( self ):
      pass
