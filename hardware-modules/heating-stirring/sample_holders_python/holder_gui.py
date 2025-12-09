from guizero import App, Text, Slider, PushButton, MenuBar, TextBox, Box
import picommon
from piholderbox import heater_box

WINDOW_X = 900
WINDOW_Y = 500

global running
running = True

def exit():
  global running
  running = False

app = App( title="Microfluidics Station", width=WINDOW_X, height=WINDOW_Y, layout="grid", visible=False, bg="white" )
menubar = MenuBar( app,
                   toplevel=["File"],
                   options=[
                       [ ["Exit", exit] ],
                   ])

pid_status_str = [ "Unconfigured",
                   "Idle",
                   "Heating",
                   "Suspended",
                   "Error"
                 ]

autotune_status_str = [ "None",
                        "Running",
                        "Aborted",
                        "Finished",
                        "Failed"
                 ]

def update_gui():
  heater1.update()
  heater2.update()
  heater3.update()
  heater4.update()

picommon.spi_init( 0, 2, 30000 )

heater1 = heater_box( app, 1, picommon.PORT_HEATER1, 0, 0 )
heater2 = heater_box( app, 2, picommon.PORT_HEATER2, 0, 6 )
heater3 = heater_box( app, 3, picommon.PORT_HEATER3, 5, 0 )
heater4 = heater_box( app, 4, picommon.PORT_HEATER4, 5, 6 )

#app.set_full_screen('')
#app.full_screen = True
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
  picommon.spi_close()
  app.destroy()
except:
  pass
