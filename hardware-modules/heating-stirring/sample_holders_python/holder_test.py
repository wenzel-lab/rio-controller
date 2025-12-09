import time
import spidev
import picommon
import piholder
import RPi.GPIO as GPIO

picommon.spi_init( 0, 2, 30000 )

holder = piholder.PiHolder( picommon.PORT_HEATER1, 0.2 )
# Read pause must be less than PIC timeout

valid = False
while not valid:
  print( "Reading ID..." )
  valid, id, id_valid = holder.get_id()
  time.sleep( 0.5 )
print( valid, id, id_valid )

valid = holder.set_pid_coeffs( 1000, 100, 1000 )
valid = holder.set_pid_running( True, 35.0 )

valid, autotune_running = holder.get_autotune_running()
if valid and not autotune_running:
  valid = holder.set_autotune_running( True, 35.0 )
  print( valid )

autotuning = True
while autotuning:
  try:
    valid, temp_c = holder.get_temp_actual()
    if valid:
      valid, pid_status, pid_error = holder.get_pid_status()
    if valid:
      valid, temp_c_target = holder.get_temp_target()
    if valid:
      valid, autotune_running = holder.get_autotune_running()
#    if valid:
#      autotuning = autotune_running
    if valid:
      valid, autotune_status, autotune_fail = holder.get_autotune_status()
    if valid:
      valid, pid_p, pid_i, pid_d = holder.get_pid_coeffs()
    if valid:
      print( "Temp {}/{}, Autotune {}/{}/{}, PID Status {}, PID {} {} {}".format( round(temp_c, 2), round(temp_c_target, 2), 'Active' if autotune_running else 'Idle', autotune_status, autotune_fail, pid_status, pid_p, pid_i, pid_d ) )
    else:
      print( "Invalid" )
  except:
    print( "Exception" )
  
  time.sleep( 0.5 )

PiCommon.spi_close()
GPIO.cleanup()
