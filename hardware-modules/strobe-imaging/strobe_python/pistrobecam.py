from pistrobe import PiStrobe
from picamera import PiCamera

class PiStrobeCam:
    strobe_wait_ns = 0
    strobe_period_ns = 0
    framerate_set = 0
    
    def __init__( self, port, reply_pause_s ):
        self.strobe = PiStrobe( port, reply_pause_s )
        self.camera = PiCamera(
            #resolution=()
            #framerate=Fraction(1, 1),
            #framerate = 50,
            #sensor_mode=3
        )
        #self.camera.resolution = ( 0, 0 )
        self.camera.awb_mode = 'auto'
        self.camera.exposure_mode = 'off'
        #ISO will not adjust gains when exposure_mode='off'
        #self.camera.iso = 800
    
    def set_timing( self, pre_padding_ns, strobe_period_ns, post_padding_ns ):
        shutter_speed_us = int( ( strobe_period_ns + pre_padding_ns + post_padding_ns ) / 1000 )
        framerate = 1000000 / shutter_speed_us
        if ( framerate > 60 ):
            framerate = 60
        self.camera.framerate = framerate
        self.camera.shutter_speed = shutter_speed_us
        
        # Inter-frame period in microseconds
        frame_rate_period_us = int( 1000000 / float( self.camera.framerate ) )
        
        # Dead time after frame, before sampling next frame
        strobe_pre_wait_us = frame_rate_period_us - self.camera.shutter_speed
        
        # How long the strobe is set to wait before triggering
        pre_padding_ns = pre_padding_ns + ( 1000 * strobe_pre_wait_us )
        
        #print( 'wait {}, strobe {}, framerate {}, frametime {}, shutter {}={}'.format( pre_padding_ns, strobe_period_ns, int( self.camera.framerate ), frame_rate_period_us, int( shutter_speed_us ), int( self.camera.shutter_speed ) ) )
        
        valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing( pre_padding_ns, strobe_period_ns )
#        self.strobe.set_enable( True )
        
        self.framerate_set = framerate
        
        return valid
        
    def close( self ):
        self.strobe.set_enable( False )
        self.strobe.set_hold( False )
        self.camera.close()
        