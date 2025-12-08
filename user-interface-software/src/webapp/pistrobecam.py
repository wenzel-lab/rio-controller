from pistrobe import PiStrobe
from picamera import PiCamera
import RPi.GPIO as GPIO
import time

class PiStrobeCam:
    strobe_wait_ns = 0
    strobe_period_ns = 0
    framerate_set = 0
    TRIGGER_GPIO_PIN = 18  # GPIO pin for PIC trigger
    
    def __init__( self, port, reply_pause_s, trigger_gpio_pin=18 ):
        self.strobe = PiStrobe( port, reply_pause_s )
        self.trigger_gpio_pin = trigger_gpio_pin
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
        
        # Initialize GPIO for PIC trigger (software-triggered mode)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trigger_gpio_pin, GPIO.OUT)
        GPIO.output(self.trigger_gpio_pin, GPIO.LOW)
        
        # Configure strobe for hardware trigger mode (PIC waits for GPIO trigger)
        self.strobe.set_trigger_mode( True )  # Hardware trigger mode
    
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
        # For hardware trigger mode, timing is simpler
        # Camera is master - just set strobe timing parameters
        wait_ns = pre_padding_ns  # Delay after trigger before strobe fires
        
        valid, self.strobe_wait_ns, self.strobe_period_ns = self.strobe.set_timing( wait_ns, strobe_period_ns )
        
        if valid:
            # Set frame callback to trigger PIC on each frame
            self.camera.start_recording( '/dev/null', format='h264' )
            # Note: picamera doesn't have direct frame callback, but we can use
            # the recording callback or capture_continuous with callback
            
            # Configure camera (simpler - no complex calculations needed)
            shutter_speed_us = int( ( strobe_period_ns + pre_padding_ns + post_padding_ns ) / 1000 )
            framerate = 1000000 / shutter_speed_us
            if ( framerate > 60 ):
                framerate = 60
            self.camera.framerate = framerate
            self.camera.shutter_speed = shutter_speed_us
            
            # Enable strobe (will wait for GPIO trigger from frame callback)
            self.strobe.set_enable( True )
            
            self.framerate_set = framerate
        
        return valid
        
    def close( self ):
        self.strobe.set_enable( False )
        self.strobe.set_hold( False )
        self.camera.close()
        