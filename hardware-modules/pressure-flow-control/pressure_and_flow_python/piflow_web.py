import picommon
import piflow

class flow_web:
  press_status_str = [  "Unconfigured",
                        "Idle",
                        "Active",
                        "Error"
                     ]

  flow_status_str  = [  "Unconfigured",
                        "Idle",
                        "Active",
                        "Error"
                     ]

  ctrl_mode_str    = [  "Off",
                        "Pressure Open Loop",
                        "Pressure Closed Loop",
                        "Flow Closed Loop"
                     ]

  def __init__( self, port ):
    self.flow = piflow.PiFlow( port, 0.1 )
    
#    self.pid_enabled = False
    self.status_text            = [ ("Init")  for i in range(self.flow.NUM_CONTROLLERS) ]
    self.pressure_mbar_text     = [ ("")      for i in range(self.flow.NUM_CONTROLLERS) ]
    self.pressure_mbar_targets  = [ (0.00)    for i in range(self.flow.NUM_CONTROLLERS) ]
    self.flow_ul_hr_text        = [ ("")      for i in range(self.flow.NUM_CONTROLLERS) ]
    self.flow_ul_hr_targets     = [ (0.00)    for i in range(self.flow.NUM_CONTROLLERS) ]
    self.control_modes          = [ (0)       for i in range(self.flow.NUM_CONTROLLERS) ]
    self.control_modes_text     = [ ("")      for i in range(self.flow.NUM_CONTROLLERS) ]
    self.flow_pid_consts        = [ [0, 0, 0] for i in range(self.flow.NUM_CONTROLLERS) ]
    
    valid, id, id_valid = self.flow.get_id()
    print( "ID OK:{}, ID={}".format( id_valid, id ) )
    self.enabled = valid and id_valid
    self.connected = self.enabled
    self.reload = False
    
    self.get_pressure_targets()
    self.get_flow_targets()
    self.get_control_modes()
    self.get_flow_pid_consts()

  def get_pressure_targets( self ):
    valid, pressures_mbar_targets = self.flow.get_pressure_target()
    if valid:
      self.pressure_mbar_targets = pressures_mbar_targets

  def get_flow_targets( self ):
    valid, flows_ul_hr_targets = self.flow.get_flow_target()
    if valid:
      self.flow_ul_hr_targets = flows_ul_hr_targets

  def get_control_modes( self ):
    valid, control_modes = self.flow.get_control_modes()
    if valid:
      self.control_modes = control_modes
      self.control_modes_text = [ (self.ctrl_mode_str[control_mode]) for control_mode in control_modes ]

  def get_flow_pid_consts( self ):
    valid, flow_pid_consts = self.flow.get_flow_pid_consts()
    if valid:
      self.flow_pid_consts = flow_pid_consts

  def set_pressure( self, index, pressure_mbar ):
    try:
#      pressure = round( float( pressure_mbar ), 2 )
      pressure = int( pressure_mbar )
      self.flow.set_pressure( [index], [pressure] )
      self.get_pressure_targets()
    except:
      pass
  
  def set_flow( self, index, flow_ul_hr ):
    try:
      flow = int( flow_ul_hr )
      self.flow.set_flow( [index], [flow] )
      self.get_flow_targets()
    except:
      pass
  
  def set_control_mode( self, index, control_mode ):
    try:
      self.flow.set_control_mode( [index], [control_mode] )
      self.get_control_modes()
    except:
      pass
  
  def set_flow_pid_consts( self, index, pid_consts ):
    try:
      self.flow.set_flow_pid_consts( [index], [pid_consts] )
      self.get_flow_pid_consts()
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
  
  def update( self ):
    if not self.enabled:
      self.status_text = [ ( "Offline" ) for i in range (self.flow.NUM_CONTROLLERS) ]
#      self.status_text = "Offline"
    else:
#      valid, pid_status, pid_error = self.holder.get_pid_status()
      valid = True
      
      okay = valid
      valid, pressures_actual = self.flow.get_pressure_actual();
      if valid:
        self.pressures_actual = pressures_actual
      okay = okay and valid
      
      valid, flows_actual = self.flow.get_flow_actual();
      if valid:
        self.flows_actual = flows_actual
#        self.flows_actual = [11, 22, 33, 44]
      okay = okay and valid
      
      if okay and not self.connected:
        self.get_pressure_targets()
        self.get_flow_targets()
        self.get_control_modes()
        self.get_flow_pid_consts()
        self.reload = okay
      
      self.connected = okay
      
      if not self.connected:
        self.status_text = [ ( "Connection Error" ) for i in range (self.flow.NUM_CONTROLLERS) ]
#        self.status_text = "Connection Error"
      else:
#        if ( pid_status == 4 ):
#          if ( pid_error == 2 ):
#            self.status_text = "No Sensor"
#          else:
#            self.status_text = "Error ".format( pid_error )
#        else:
          try:
#            self.status_text = "{}".format( self.pid_status_str[pid_status] )
            self.status_text = [ ( "Connected" ) for i in range (self.flow.NUM_CONTROLLERS) ]
          except:
            pass
      
      try:
        self.pressure_mbar_text = [ ( "{} / {}".format( round( self.pressures_actual[i], 2 ), round( self.pressure_mbar_targets[i], 2 ) ) ) for i in range (self.flow.NUM_CONTROLLERS) ]
#        self.flow_ul_hr_text = [ ( "{}".format( round( self.flows_actual[i], 2 ) ) ) for i in range (self.flow.NUM_CONTROLLERS) ]
        self.flow_ul_hr_text = [ ( "{} / {}".format( round( self.flows_actual[i], 2 ), round( self.flow_ul_hr_targets[i], 2 ) ) ) for i in range (self.flow.NUM_CONTROLLERS) ]
      except:
        pass
      
#      self.pid_enabled = ( pid_status == 2 )
      
#    if ( not self.pid_enabled ):
#      self.set_pid_enable_btn.text = "Enable PID"
#    else:
#      self.set_pid_enable_btn.text = "Disable PID"
    
    try:
#      self.autotune_status_text = "{}".format( self.autotune_status_str[autotune_status] )
      pass
    except:
      pass
