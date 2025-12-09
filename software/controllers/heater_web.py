import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drivers.heater import PiHolder

class heater_web:
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
  
  INIT_TRIES = 3
  
  def __init__( self, heater_num, port ):
    self.holder = PiHolder( port, 0.05 )
    self.autotuning = False
    self.pid_enabled = False
    self.stir_enabled = False
    self.autotune_target_temp = 50.0
    self.stir_target_speed = 20
    self.temp_c_actual = 0
    self.status_text = ""
    self.autotune_status_text = ""
    self.temp_text = ""
    self.stir_speed_text = ""
    
    for i in range( self.INIT_TRIES ):
      valid, id, id_valid = self.holder.get_id()
      if valid:
        break
#      else:
#        time.sleep( 0.1 )
    # Use logging instead of print (logging configured in main app)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Heater {heater_num} ID OK: {valid}")
    self.enabled = valid and id_valid
    
    self.temp_c_target = self.get_temp_target()
    valid, self.heat_power_limit_pc = self.holder.get_heat_power_limit_pc()

  def get_temp_target( self ):
    valid, temp_c_target = self.holder.get_temp_target()
    if valid:
      temp_c_target = round( temp_c_target, 2 )
    self.temp_c_target = temp_c_target
    return temp_c_target

  def set_temp( self, temp ):
    try:
      temp = round( float( temp ), 2 )
      self.holder.set_pid_temp( temp )
      self.temp_c_target = self.get_temp_target()
    except:
      pass
  
  def set_heat_power_limit_pc( self, power_limit_pc ):
    try:
      limit_pc = int( power_limit_pc )
      valid = self.holder.set_heat_power_limit_pc( limit_pc )
      valid, power_limit_pc = self.holder.get_heat_power_limit_pc()
      if valid:
        self.heat_power_limit_pc = power_limit_pc
    except:
      pass
  
  def set_autotune( self, autotuning ):
    try:
      temp = round( float( self.autotune_target_temp ), 2 )
      #autotuning = 0 if self.autotuning else 1
      self.holder.set_autotune_running( autotuning, temp )
    except:
      pass
    
  def set_pid_running( self, run ):
    try:
      #run = 0 if self.pid_enabled else 1
      #temp = round( float( self.temp_target_box.value ), 2 )
      #self.holder.set_pid_running( run, temp )
      self.holder.set_pid_running( run )
      #self.temp_c_target = self.get_temp_target()
    except:
      pass
  
  def set_stir_running( self, run ):
    try:
      #run = 0 if self.stir_enabled else 1
      stir_speed_rps = int( self.stir_target_speed )
      self.holder.set_stir_running( run, stir_speed_rps )
    except:
      pass
  
  def update( self ):
    if not self.enabled:
      self.status_text = "Offline"
    else:
      valid, pid_status, pid_error = self.holder.get_pid_status()
      okay = valid
      valid, temp_c = self.holder.get_temp_actual()
      if valid:
        self.temp_c_actual = round( temp_c, 2 )
      okay = okay and valid
      valid, autotune_status, autotune_fail = self.holder.get_autotune_status()
      okay = okay and valid
      valid, stir_status = self.holder.get_stir_status()
      okay = okay and valid
      valid, stir_speed_actual_rps = self.holder.get_stir_speed_actual()
      okay = okay and valid
      
      self.autotuning = ( autotune_status == 1 )
      self.autotune_status = autotune_status
      
      if not okay:
        self.status_text = "Connection Error"
      elif self.autotuning:
        self.status_text = "Autotuning"
      else:
        if ( pid_status == 4 ):
          if ( pid_error == 2 ):
            self.status_text = "No Sensor"
          else:
            self.status_text = "Error ".format( pid_error )
        else:
          try:
            self.status_text = "{}".format( self.pid_status_str[pid_status] )
          except:
            pass
      
      try:
        self.temp_text = "{} / {}".format( round( self.temp_c_actual, 2 ), round( self.temp_c_target, 2 ) )
        self.stir_speed_text = "{} RPS".format( stir_speed_actual_rps )
      except:
        pass
      
      self.pid_enabled = ( pid_status == 2 )
      self.stir_enabled = ( stir_status == 2 )
      
    try:
      self.autotune_status_text = "{}".format( self.autotune_status_str[autotune_status] )
    except:
      pass
