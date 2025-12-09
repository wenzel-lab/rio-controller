import picommon
from guizero import App, Text, Slider, PushButton, MenuBar, TextBox, Box, Window
from pistrobebox import strobe_box

WINDOW_X = 1024
WINDOW_Y = 600

global running
running = True

app = App( title="Microfluidics Station", width=WINDOW_X, height=WINDOW_Y, layout="grid", visible=False, bg="white" )
menubar = MenuBar( app,
                   toplevel=["File"],
                   options=[
                       [ ["Exit", exit] ],
                   ])

def update_gui():
  strobe1.update()

def exit():
  global running
  running = False

picommon.spi_init( 0, 2, 30000 )

strobe1 = strobe_box( app, picommon.PORT_STROBE, 0, 0 )

app.full_screen = True
app.when_closed = exit
app.show()
app.update()

while running:
  try:
    update_gui()
    app.update()
  except:
    running = False
    pass

try:
  strobe1.strobe_cam.camera.stop_preview()
  strobe1.strobe_cam.strobe.set_enable( False )
  strobe1.strobe_cam.close()
  picommon.spi_close()
  app.destroy()
except:
  pass
