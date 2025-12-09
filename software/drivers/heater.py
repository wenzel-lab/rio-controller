import time
import sys
import os

# Import from sibling module
# Note: We import from the parent package to ensure we get the same module instance
# that main.py uses, avoiding import path issues
import sys as sys_module
import os as os_module
parent_dir = os_module.path.dirname(os_module.path.dirname(os_module.path.abspath(__file__)))
if parent_dir not in sys_module.path:
    sys_module.path.insert(0, parent_dir)
from drivers import spi_handler
# Note: spi_handler.spi is a global variable set by spi_init()
# We access it as spi_handler.spi after initialization
# spi_handler handles simulation mode automatically

class PiHolder:
  DEVICE_ID                         = 'SAMPLE_HOLDER'
  STX                               = 2
  PRESSURE_SHIFT                    = 3
  TEMP_SCALE                        = 100
  PRESSURE_SCALE                    = ( 1 << PRESSURE_SHIFT )
  PACKET_TYPE_GET_ID                = 1
  PACKET_TYPE_TEMP_SET_TARGET       = 2
  PACKET_TYPE_TEMP_GET_TARGET       = 3
  PACKET_TYPE_TEMP_GET_ACTUAL       = 4
  PACKET_TYPE_PID_SET_COEFFS        = 5
  PACKET_TYPE_PID_GET_COEFFS        = 6
  PACKET_TYPE_PID_SET_RUNNING       = 7
  PACKET_TYPE_PID_GET_STATUS        = 8
  PACKET_TYPE_AUTOTUNE_SET_RUNNING  = 9
  PACKET_TYPE_AUTOTUNE_GET_RUNNING  = 10
  PACKET_TYPE_AUTOTUNE_GET_STATUS   = 11
  PACKET_TYPE_STIR_SET_RUNNING      = 12
  PACKET_TYPE_STIR_GET_STATUS       = 13
  PACKET_TYPE_STIR_SPEED_GET_ACTUAL = 14
  PACKET_TYPE_HEAT_POWER_LIMIT_SET  = 15
  PACKET_TYPE_HEAT_POWER_LIMIT_GET  = 16
  
  def __init__( self, device_port, reply_pause_s ):
    self.device_port = device_port
    self.reply_pause_s = reply_pause_s
  
  def read_bytes( self, bytes ):
    data = []
    # Ensure spi is initialized
    if spi_handler.spi is None:
      import logging
      logger = logging.getLogger(__name__)
      logger.error("SPI not initialized! Call spi_init() before using drivers.")
      return []
    for x in range( bytes ):
      data.extend( spi_handler.spi.xfer2( [0] ) )
    return data
  
  def packet_read( self ):
    valid = False
    spi_handler.spi_select_device( self.device_port )
    data = self.read_bytes( 1 )
    if ( data[0] == self.STX ):
      data.extend( self.read_bytes( 2 ) )
      size = data[1]
      type = data[2]
      data.extend( self.read_bytes( size - 3 ) )
      checksum = sum( data ) & 0xFF
      if ( checksum == 0 ):
        data = data[3:(size-1)]
        valid = True
    if not valid:
      data = []
    return valid, type, data
  
  def packet_write( self, type, data ):
    # Ensure spi is initialized
    if spi_handler.spi is None:
      import logging
      logger = logging.getLogger(__name__)
      logger.error("SPI not initialized! Call spi_init() before using drivers.")
      return
    msg = [2, len(data)+4, type] + data
    checksum = ( -( sum( msg ) & 0xFF ) ) & 0xFF
    msg.append( checksum )
    spi_handler.spi_select_device( self.device_port )
    spi_handler.spi.xfer2( msg )
    
  def packet_query( self, type, data ):
    valid = False  # Initialize before try block
    data_read = []  # Initialize before try block
    try:
      spi_handler.spi_lock()
      self.packet_write( type, data )
#      time.sleep( self.reply_pause_s )
      spi_handler.pi_wait_s( self.reply_pause_s )
      valid = True
      data_read = []
      type_read = 0x100
      try:
        while valid and ( type_read != type ) and ( type_read != 0 ):
          valid, type_read, data_read = self.packet_read()
      except Exception:
        valid = False
        data_read = []
      spi_handler.spi_deselect_current()
    except Exception as e:
      import logging
      logger = logging.getLogger(__name__)
      logger.error(f"SPI communication error in packet_query: {e}")
      valid = False
      data_read = []
      try:
        spi_handler.spi_deselect_current()
      except Exception:
        pass
    finally:
      try:
        spi_handler.spi_release()
      except Exception:
        pass
    return valid, data_read
    
  def get_id( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_ID, [] )
    if valid:
      id = bytes(data[1:-1]).decode("ascii")
      id_valid = ( id == self.DEVICE_ID )
      try:
        checksum_okay = data[0] == 0
      except:
        checksum_okay = False
    else:
      id = 0
      id_valid = False
    return ( valid and checksum_okay, id, id_valid )

  def get_temp_target( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_TEMP_GET_TARGET, [] )
    if valid:
      temp_c = int.from_bytes( data[1:3], byteorder='big', signed=True ) / self.TEMP_SCALE
    else:
      temp_c = 0
    return ( valid and ( data[0] == 0 ), temp_c )

  def set_pid_coeffs( self, pid_p, pid_i, pid_d ):
    send_bytes = list( pid_p.to_bytes( 2, 'little', signed=False ) )
    send_bytes.extend( list( pid_i.to_bytes( 2, 'little', signed=False ) ) )
    send_bytes.extend( list( pid_d.to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_PID_SET_COEFFS, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_pid_coeffs( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_PID_GET_COEFFS, [] )
    if valid:
      pid_p = int.from_bytes( data[1:3], byteorder='big', signed=False )
      pid_i = int.from_bytes( data[3:5], byteorder='big', signed=False )
      pid_d = int.from_bytes( data[5:7], byteorder='big', signed=False )
    else:
      pid_p = 0
      pid_i = 0
      pid_d = 0
    return ( valid and ( data[0] == 0 ), pid_p, pid_i, pid_d )

  def set_pid_running( self, running, temp_c=[] ):
    send_bytes = list( running.to_bytes( 1, 'little', signed=False ) )
    if ( temp_c != [] ):
      temp_c_scaled = round( temp_c * 100 )
      send_bytes.extend( list( temp_c_scaled.to_bytes( 2, 'little', signed=True ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_PID_SET_RUNNING, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def set_pid_temp( self, temp_c ):
    temp_c_scaled = round( temp_c * 100 )
    send_bytes = list( temp_c_scaled.to_bytes( 2, 'little', signed=True ) )
    valid, data = self.packet_query( self.PACKET_TYPE_TEMP_SET_TARGET, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_pid_status( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_PID_GET_STATUS, [] )
    if valid:
      pid_status = data[1]
      pid_error = data[2]
    else:
      pid_status = 0
      pid_error = 0
    return ( valid and ( data[0] == 0 ), pid_status, pid_error )

  def get_temp_actual( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_TEMP_GET_ACTUAL, [] )
    if valid:
      temp_c = int.from_bytes( data[1:3], byteorder='big', signed=True ) / self.TEMP_SCALE
    else:
      temp_c = 0
    return ( valid and ( data[0] == 0 ), temp_c )

  def set_autotune_running( self, running, temp_c ):
    temp_c_scaled = round( temp_c * 100 )
    send_bytes = list( running.to_bytes( 1, 'little', signed=False ) )
    send_bytes.extend( list( temp_c_scaled.to_bytes( 2, 'little', signed=True ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_AUTOTUNE_SET_RUNNING, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_autotune_running( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_AUTOTUNE_GET_RUNNING, [] )
    if valid:
      autotune_running = data[1]
    else:
      autotune_running = 0
    return ( valid and ( data[0] == 0 ), autotune_running )
  
  def get_autotune_status( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_AUTOTUNE_GET_STATUS, [] )
    if valid:
      autotune_status = data[1]
      autotune_fail = data[2]
    else:
      autotune_status = 0
      autotune_fail = 0
    return ( valid and ( data[0] == 0 ), autotune_status, autotune_fail )
  
  def get_stir_speed_actual( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_STIR_SPEED_GET_ACTUAL, [] )
    if valid:
      stir_speed_rps = int.from_bytes( data[1:3], byteorder='big', signed=False )
    else:
      stir_speed_rps = 0
    return ( valid and ( data[0] == 0 ), stir_speed_rps )
  
  def get_stir_status( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_STIR_GET_STATUS, [] )
    if valid:
      stir_status = data[1]
    else:
      stir_status = 0
    return ( valid and ( data[0] == 0 ), stir_status )
  
  def set_stir_running( self, running, stir_speed_rps ):
    send_bytes = list( running.to_bytes( 1, 'little', signed=False ) )
    send_bytes.extend( list( stir_speed_rps.to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_STIR_SET_RUNNING, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def set_heat_power_limit_pc( self, power_limit_pc ):
    send_bytes = list( power_limit_pc.to_bytes( 1, 'little', signed=False ) )
    valid, data = self.packet_query( self.PACKET_TYPE_HEAT_POWER_LIMIT_SET, send_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_heat_power_limit_pc( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_HEAT_POWER_LIMIT_GET, [] )
    if valid:
      heat_power_limit_pc = data[1]
    else:
      heat_power_limit_pc = 0
    return ( valid and ( data[0] == 0 ), heat_power_limit_pc )

