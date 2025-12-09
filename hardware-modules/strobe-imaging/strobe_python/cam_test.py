import spidev
#from pistrobe import PiStrobe
#from picamera import PiCamera
from pistrobecam import PiStrobeCam
from time import sleep
from guizero import App, Text


def spi_init( bus, device, mode, speed_hz ):
  spi = spidev.SpiDev()
  spi.open( bus, device )
  spi.mode = mode
  spi.max_speed_hz = speed_hz
  #spi.no_cs = False
  #spi.cshigh = False
  return spi

app = App( title="Yo", width=200, height = 160, layout="grid", visible=False, bg="black" )
test_text = Text( app, text="Strobe", grid=[0, 0], align="left" )
#app.set_full_screen('')
app.full_screen = True
app.show()
app.update()

spi = spi_init( 0, 0, 2, 125000 )
strobe_cam = PiStrobeCam( spi )
#strobe_cam.camera.resolution = ( 640, 400 )
#strobe_cam.camera.resolution = ( 320, 200 )
#strobe_cam.camera.sensor_mode = 4
print( 'Resolution: {}'.format( strobe_cam.camera.resolution ) )
strobe_cam.set_timing( 10000, 10000000, 24000000 )

#strobe_cam.camera.zoom = ( 0.4, 0.4, 0.6, 0.6 )
strobe_cam.camera.start_preview( fullscreen=False, window=(200,200,500,400) )
sleep(2)
#input()
#camera.capture('capture.jpg')
#camera.start_recording('')
strobe_cam.camera.stop_preview()
#strobe_cam.close()
#sleep(2)

strobe_cam.strobe.set_enable( False )
strobe_cam.close()
spi.close()
app.hide()

