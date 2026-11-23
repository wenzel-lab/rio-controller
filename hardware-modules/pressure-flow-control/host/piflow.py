import time
import spidev
import picommon

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
  PACKET_TYPE_SET_ACTIVE_SENSORS  = 12
  PACKET_TYPE_GET_ACTIVE_SENSORS  = 13
  # Firmware v3
  PACKET_TYPE_GET_FLOW_STATS      = 14
  PACKET_TYPE_SET_FLOW_RESOLUTION = 15
  PACKET_TYPE_GET_FLOW_RESOLUTION = 16
  PACKET_TYPE_GET_FW_VERSION      = 17
  PACKET_TYPE_GET_FLOW_BATCH      = 18   # v3.2
  ERR_FLOW_BATCH_GAP              = 74
  FLOW_BATCH_MAX_SAMPLES          = 16
  
  # SET_FLOW_RESOLUTION blocks the PIC up to ~120 ms per present sensor while it
  # drains the pending measurement. The PIC discards an unread reply after 300 ms,
  # so a single long pause does not work: poll for the reply instead.
  SET_RESOLUTION_POLL_S           = 0.05
  SET_RESOLUTION_TIMEOUT_S        = 1.5
  
  NUM_CONTROLLERS                 = 4
  
  def __init__( self, device_port, reply_pause_s ):
    self.device_port = device_port
    self.reply_pause_s = reply_pause_s
    # MODIFIED: Added flow refresh counter for duplicate detection
    self.flow_refresh_counter = None
  
  def read_bytes( self, n ):
    # MODIFIED: Replace with single bulk transfer for better performance
    # Current (13 individual xfer2 calls per packet_read):
    # def read_bytes( self, bytes ):
    #   data = []
    #   for x in range( bytes ):
    #     data.extend( picommon.spi.xfer2( [0] ) )
    #   return data
    
    # Replace with single bulk transfer:
    return picommon.spi.xfer2( [0] * n )
  
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

  def get_flow_actual( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_ACTUAL, [] )
    if not valid or data[0] != 0:
      return False, []
    
    # MODIFIED: New layout: [err U8][refresh_counter U16][4 × flow I16]
    # Old layout: [err U8][4 × flow I16]
    # Detect layout by response length:
    #   Old: 1 + 4*2 = 9 bytes of data payload
    #   New: 1 + 2 + 4*2 = 11 bytes of data payload
    if len(data) >= 11:
      # New firmware: skip err byte + 2-byte counter
      self.flow_refresh_counter = int.from_bytes(data[1:3], 'little', signed=False)
      offset = 3
    else:
      # Old firmware: backwards-compatible
      self.flow_refresh_counter = None
      offset = 1
    
    count = (len(data) - offset) // 2
    flows_ul_hr = []
    for i in range(count):
      idx = offset + i * 2
      flow_ul_hr = int.from_bytes( data[idx:idx+2], byteorder='little', signed=True )
      flows_ul_hr.extend( [flow_ul_hr] )
    return True, flows_ul_hr

  def get_control_modes( self ):
    valid, data = self.packet_query( self.PACKET_TYPE_GET_CONTROL_MODE, [] )
    count = len(data) - 1
    control_modes=[]
    for i in range(count):
      index = 1 + i
      control_mode = data[index]
      control_modes.extend( [control_mode] )
    return ( valid and ( data[0] == 0 ), control_modes )

  # MODIFIED: Added sensor selection methods
  def set_active_sensors( self, sensor_mask ):
    """Set active sensors using bit mask (0b1111 = all 4 sensors)
    
    Args:
        sensor_mask (int): Bit mask where bit 0 = sensor 0, bit 3 = sensor 3
                          Example: 0b0101 = sensors 0 and 2 active
    
    Returns:
        tuple: (success: bool, error_code: int)
    """
    if not isinstance(sensor_mask, int) or sensor_mask < 0 or sensor_mask > 0b1111:
      return False, -1
    
    valid, data = self.packet_query( self.PACKET_TYPE_SET_ACTIVE_SENSORS, [sensor_mask] )
    return ( valid and ( data[0] == 0 ), data[0] if valid else -1 )

  def get_active_sensors( self ):
    """Get current active sensor mask
    
    Returns:
        tuple: (success: bool, sensor_mask: int)
    """
    valid, data = self.packet_query( self.PACKET_TYPE_GET_ACTIVE_SENSORS, [] )
    return ( valid and ( data[0] == 0 ), data[1] if valid else 0 )

  # ---- Firmware v3 ---------------------------------------------------------
  def get_fw_version( self ):
    """Returns (success, (major, minor)). Firmware < v3 answers ERR_PACKET_INVALID -> (False, None).

    Side effect: remembers the version so get_flow_batch picks the right sample
    format (t_ms U16 up to v3.2, U32 from v3.3)."""
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FW_VERSION, [] )
    if valid and len(data) >= 3 and data[0] == 0:
      self.batch_t32 = ( data[1], data[2] ) >= ( 3, 3 )
      return True, ( data[1], data[2] )
    return False, None

  @staticmethod
  def crc8( data ):
    """Sensirion CRC-8: poly 0x31, init 0x00, no reflection (same as the PIC)."""
    crc = 0
    for b in data:
      crc ^= b
      for _ in range(8):
        crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc

  @classmethod
  def parse_flow_batch( cls, data, t32=False ):
    """Decode a GET_FLOW_BATCH payload.

    v3.2: [err U8][n U8][seq0 U16][scale U16][n x (t_ms U16, flow_raw I16)][crc8]
    v3.3 (t32=True): t_ms is U32 (wrap 49.7 days instead of 65.5 s), 6 B/sample.
    Returns dict(err, n, seq0, scale, samples=[(seq, t_ms, flow_raw), ...]) or None
    if the payload is malformed or fails the CRC.
    """
    tw = 4 if t32 else 2      # width of t_ms on the wire
    sw = tw + 2               # bytes per sample
    if len(data) < 7:
      return None
    n = data[1]
    end = 6 + sw * n
    if len(data) < end + 1:
      return None
    if cls.crc8( data[:end] ) != data[end]:
      return None
    seq0 = int.from_bytes( data[2:4], 'little' )
    scale = int.from_bytes( data[4:6], 'little' )
    samples = []
    for i in range(n):
      o = 6 + sw * i
      t_ms = int.from_bytes( data[o:o+tw], 'little' )
      raw = int.from_bytes( data[o+tw:o+sw], 'little', signed=True )
      samples.append( ( (seq0 + i) & 0xFFFF, t_ms, raw ) )
    return { 'err': data[0], 'n': n, 'seq0': seq0, 'scale': scale, 'samples': samples }

  def get_flow_batch( self, sensor, since_seq ):
    """Accepted readings of `sensor` after sequence number `since_seq` (v3.2).

    seq = per-sensor ok counter & 0xFFFF (GET_FLOW_STATS 'ok' gives the current head).
    Returns (success, batch) with batch as in parse_flow_batch; batch['err'] ==
    ERR_FLOW_BATCH_GAP means since_seq was no longer in the PIC ring and delivery
    restarted from the oldest kept sample (batch['seq0'] != since_seq+1).
    flow ul/h = flow_raw * 60 / scale.  Idempotent: safe to repeat on failure.
    """
    if not isinstance(sensor, int) or sensor < 0 or sensor >= self.NUM_CONTROLLERS:
      return False, None
    since_seq &= 0xFFFF
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_BATCH,
                                     [sensor, since_seq & 0xFF, since_seq >> 8] )
    if not valid:
      return False, None
    batch = self.parse_flow_batch( data, t32=getattr( self, 'batch_t32', False ) )
    if batch is None or batch['err'] not in ( 0, self.ERR_FLOW_BATCH_GAP ):
      return False, None
    return True, batch

  def get_flow_stats( self, sensor ):
    """Per-sensor read counters since PIC boot (uint32, wrap at 2^32).

    Returns (success, dict(ok, crc_err, i2c_err, not_ready[, saturated])) or (False, None).
      ok        - readings accepted (I2C ok + CRC ok)
      crc_err   - readings rejected by CRC-8 (corrupted transfers)
      i2c_err   - bus timeouts / failures (mux or sensor)
      not_ready - polls NACKed because the measurement was still running (benign)
      saturated - accepted readings at the +-32400 rail, i.e. flow out of range (fw >= 3.3)
    """
    if not isinstance(sensor, int) or sensor < 0 or sensor >= self.NUM_CONTROLLERS:
      return False, None
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_STATS, [sensor] )
    if not ( valid and len(data) >= 17 and data[0] == 0 ):
      return False, None
    vals = [ int.from_bytes( data[1+4*i:5+4*i], 'little', signed=False ) for i in range(4) ]
    stats = { 'ok': vals[0], 'crc_err': vals[1], 'i2c_err': vals[2], 'not_ready': vals[3] }
    if len(data) >= 21:
      stats['saturated'] = int.from_bytes( data[17:21], 'little', signed=False )
    return True, stats

  def set_flow_resolution( self, bits ):
    """Set LG16 measurement resolution on all present sensors (9..16 bit).

    16 bit = 74 ms/measurement (default, lowest noise); 12 bit = 4.6 ms; 9 bit = 0.8 ms.
    Volatile: the PIC reverts to 16 bit on reboot. Returns (success, error_code).
    """
    if not isinstance(bits, int) or bits < 9 or bits > 16:
      return False, -1
    valid, data = self.packet_query_poll( self.PACKET_TYPE_SET_FLOW_RESOLUTION, [bits],
                                          self.SET_RESOLUTION_POLL_S, self.SET_RESOLUTION_TIMEOUT_S )
    return ( valid and ( data[0] == 0 ), data[0] if valid else -1 )

  def packet_query_poll( self, type, data, poll_s, timeout_s ):
    """Like packet_query, but for slow commands: re-reads every poll_s until the
    reply of the requested type arrives or timeout_s elapses."""
    valid = False
    data_read = []
    try:
      picommon.spi_lock()
      self.packet_write( type, data )
      deadline = time.time() + timeout_s
      while time.time() < deadline:
        picommon.pi_wait_s( poll_s )
        try:
          ok, type_read, d = self.packet_read()
        except:
          ok = False
        if ok and type_read == type:
          valid, data_read = True, d
          break
      picommon.spi_deselect_current()
    except:
      pass
    finally:
      picommon.spi_release()
    return valid, data_read

  def get_flow_resolution( self ):
    """Returns (success, bits)."""
    valid, data = self.packet_query( self.PACKET_TYPE_GET_FLOW_RESOLUTION, [] )
    if valid and len(data) >= 2 and data[0] == 0:
      return True, data[1]
    return False, None

  def sensors_to_mask( self, sensor_list ):
    """Convert sensor list [0,1,2] to bit mask 0b0111
    
    Args:
        sensor_list (list): List of sensor IDs (0-3)
    
    Returns:
        int: Bit mask for active sensors
    """
    mask = 0
    for sensor_id in sensor_list:
      if 0 <= sensor_id <= 3:
        mask |= (1 << sensor_id)
    return mask

  def mask_to_sensors( self, mask ):
    """Convert bit mask to sensor list
    
    Args:
        mask (int): Bit mask where bit 0 = sensor 0, bit 3 = sensor 3
    
    Returns:
        list: List of active sensor IDs
    """
    sensors = []
    for i in range(4):
      if mask & (1 << i):
        sensors.append(i)
    return sensors

