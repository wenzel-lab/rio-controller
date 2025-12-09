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

class PiFlow:
  DEVICE_ID                       = 'MICROFLOW'
  STX                             = 2
  PRESSURE_SHIFT                  = 3
  PRESSURE_SCALE                  = ( 1 << PRESSURE_SHIFT )
  
  PACKET_TYPE_GET_ID              = 1
  PACKET_TYPE_SET_PRESSURE_TARGET = 2
  PACKET_TYPE_GET_PRESSURE_TARGET = 3
  PACKET_TYPE_GET_PRESSURE_ACTUAL = 4
  PACKET_TYPE_SET_FLOW_TARGET     = 5
  PACKET_TYPE_GET_FLOW_TARGET     = 6
  PACKET_TYPE_GET_FLOW_ACTUAL     = 7
  PACKET_TYPE_SET_CONTROL_MODE    = 8
  PACKET_TYPE_GET_CONTROL_MODE    = 9
  PACKET_TYPE_SET_FPID_CONSTS     = 10
  PACKET_TYPE_GET_FPID_CONSTS     = 11
  
  NUM_CONTROLLERS                 = 4
  
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

  def set_pressure_all( self, pressures_mbar ):
    data_bytes = []
    for i in range(self.NUM_CONTROLLERS):
      mask = 1 << i
      pressure_fp = int( pressures_mbar[i] * self.PRESSURE_SCALE );
      data_bytes.extend( [mask] + list( pressure_fp.to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_SET_PRESSURE_TARGET, data_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def set_pressure( self, indices, pressures_mbar ):
    data_bytes = []
    for i in range(len(indices)):
      mask = 1 << indices[i]
      pressure_fp = int( pressures_mbar[i] * self.PRESSURE_SCALE );
      data_bytes.extend( [mask] + list( pressure_fp.to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_SET_PRESSURE_TARGET, data_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def set_control_mode( self, indices, control_modes ):
    data_bytes = []
    for i in range(len(indices)):
      mask = 1 << indices[i]
      control_mode = control_modes[i]
      data_bytes.extend( [mask] + list( control_mode.to_bytes( 1, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_SET_CONTROL_MODE, data_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_pressure_target( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_PRESSURE_TARGET, [] )
    count = int( ( len(data) - 1 ) / 2 )
    pressures_mbar=[]
    for i in range(count):
      index = 1 + ( i << 1 )
      pressure_mbar = int.from_bytes( data[index:index+2], byteorder='little', signed=False ) / self.PRESSURE_SCALE
      pressures_mbar.extend( [pressure_mbar] )
    return ( valid and ( data[0] == 0 ), pressures_mbar )

  def get_pressure_actual( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_PRESSURE_ACTUAL, [] )
    count = int( ( len(data) - 1 ) / 2 )
    pressures_mbar=[]
    for i in range(count):
      index = 1 + ( i << 1 )
      pressure_mbar = int.from_bytes( data[index:index+2], byteorder='little', signed=True ) / self.PRESSURE_SCALE
      pressures_mbar.extend( [pressure_mbar] )
    return ( valid and ( data[0] == 0 ), pressures_mbar )

  def get_flow_target( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_TARGET, [] )
    count = int( ( len(data) - 1 ) / 2 )
    flows_ul_hr=[]
    for i in range(count):
      index = 1 + ( i << 1 )
      flow_ul_hr = int.from_bytes( data[index:index+2], byteorder='little', signed=False )
      flows_ul_hr.extend( [flow_ul_hr] )
    return ( valid and ( data[0] == 0 ), flows_ul_hr )

  def get_flow_actual( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_ACTUAL, [] )
    count = int( ( len(data) - 1 ) / 2 )
    flows_ul_hr=[]
    for i in range(count):
      index = 1 + ( i << 1 )
      flow_ul_hr = int.from_bytes( data[index:index+2], byteorder='little', signed=True )
      flows_ul_hr.extend( [flow_ul_hr] )
    return ( valid and ( data[0] == 0 ), flows_ul_hr )

  def set_flow( self, indices, flows_ul_hr ):
    data_bytes = []
    for i in range(len(indices)):
      mask = 1 << indices[i]
      flow_ul_hr = int( flows_ul_hr[i] )
      data_bytes.extend( [mask] + list( flow_ul_hr.to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_SET_FLOW_TARGET, data_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_control_modes( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_CONTROL_MODE, [] )
    count = len(data) - 1
    control_modes=[]
    for i in range(count):
      index = 1 + i
      control_mode = data[index]
      control_modes.extend( [control_mode] )
    return ( valid and ( data[0] == 0 ), control_modes )

  def set_flow_pid_consts( self, indices, pid_consts ):
    data_bytes = []
    for i in range(len(indices)):
      mask = 1 << indices[i]
      pid_const = pid_consts[i]
      data_bytes.extend( [mask] + list( pid_const[0].to_bytes( 2, 'little', signed=False ) ) )
      data_bytes.extend( list( pid_const[1].to_bytes( 2, 'little', signed=False ) ) )
      data_bytes.extend( list( pid_const[2].to_bytes( 2, 'little', signed=False ) ) )
    valid, data = self.packet_query( self.PACKET_TYPE_SET_FPID_CONSTS, data_bytes )
    return ( ( valid and ( data[0] == 0 ) ) )

  def get_flow_pid_consts( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FPID_CONSTS, [] )
    count = int( ( len(data) - 1 ) / ( 3 * 2 ) )  # 3 constants * 2 bytes each
    pid_consts = []
    for i in range(count):
      consts = []
      for j in range(3):  # P, I, D
        index = 1 + ( 2 * ( 3 * i + j ) )
        const = int.from_bytes( data[index:index+2], byteorder='little', signed=False )
        consts.extend( [const] )
      pid_consts.extend( [consts] )
    return ( valid and ( data[0] == 0 ), pid_consts )

