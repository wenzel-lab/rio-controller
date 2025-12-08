import time
import spidev
import picommon

class PiStrobe:
  STX = 2
  
  def __init__( self, device_port, reply_pause_s ):
    self.device_port = device_port
    self.reply_pause_s = reply_pause_s
  
  def read_bytes( self, bytes ):
    data = []
    for x in range( bytes ):
      data.extend( picommon.spi.xfer2( [0] ) )
    return data
  
  def packet_read( self ):
    valid = False
    picommon.spi_select_device( self.device_port )
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
    msg = [2, len(data)+4, type] + data
    checksum = ( -( sum( msg ) & 0xFF ) ) & 0xFF
    msg.append( checksum )
    picommon.spi_select_device( self.device_port )
    picommon.spi.xfer2( msg )
    
  def packet_query( self, type, data ):
    try:
      picommon.spi_lock()
      self.packet_write( type, data )
#      time.sleep( self.reply_pause_s )
      picommon.pi_wait_s( self.reply_pause_s )
      valid = True
      data_read = []
      type_read = 0x100
      try:
        while valid and ( type_read != type ) and ( type_read != 0 ):
          valid, type_read, data_read = self.packet_read()
      except:
        valid = False
      picommon.spi_deselect_current()
    except:
      pass
    finally:
      picommon.spi_release()
    return valid, data_read
    
  def set_enable( self, enable ):
    enabled = 1 if enable else 0
    valid, data = self.packet_query( 1, [enabled] )
    return ( valid and ( data[0] == 0 ) )

  def set_timing( self, wait_ns, period_ns ):
    wait_ns_bytes = list( wait_ns.to_bytes( 4, 'little', signed=False ) )
    period_ns_bytes = list( period_ns.to_bytes( 4, 'little', signed=False ) )
    valid, data = self.packet_query( 2, wait_ns_bytes + period_ns_bytes )
    actual_wait_ns = int.from_bytes( data[1:5], byteorder='little', signed=False )
    actual_period_ns = int.from_bytes( data[5:9], byteorder='little', signed=False )
    #print( "data={}, wait={}, period={}, wait_bytes={}".format( data, actual_wait_ns, actual_period_ns, data[1:5] ) )
    return ( ( valid and ( data[0] == 0 ) ), actual_wait_ns, actual_period_ns )

  def set_hold( self, hold ):
    valid, data = self.packet_query( 3, [1 if hold else 0] )
    return ( valid and ( data[0] == 0 ) )

  def get_cam_read_time( self ):
    valid, data = self.packet_query( 4, [] )
    cam_read_time_us = int.from_bytes( data[1:3], byteorder='little', signed=False )
    return ( valid and ( data[0] == 0 ), cam_read_time_us )

  def set_trigger_mode( self, hardware_trigger ):
    """
    Set trigger mode for strobe synchronization.
    
    Args:
        hardware_trigger: True for hardware trigger mode (camera triggers strobe),
                         False for software trigger mode (current behavior)
    
    Returns:
        bool: True if successful, False otherwise
    """
    mode = 1 if hardware_trigger else 0
    valid, data = self.packet_query( 5, [mode] )
    return ( valid and ( data[0] == 0 ) )
