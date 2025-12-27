from guizero import App, Text, PushButton, MenuBar, TextBox, Box
import picommon
import piholder

class heater_box:
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
  
  def __init__( self, app, heater_num, port, locx, locy ):
    self.locx = locx
    self.locy = locy
    self.holder = piholder.PiHolder( port, 0.05 )
    self.autotuning = False
    self.pid_enabled = False
    self.stir_enabled = False
    
    valid, id, id_valid = self.holder.get_id()
#    print( "ID OK:{}".format( valid ) )
    self.enabled = valid and id_valid
    
    box=Box( app, layout="grid", grid=[locx, locy] )
    box.set_border( 1, "black" )
    box.bg = picommon.col_lightgray1 if ( ( locx + locy ) % 2 == 0 ) else picommon.col_lightgray2
    
    Text( box, grid=[0, 0], text="Heater {}".format(heater_num), align="left" )
    Box( box, grid=[1, 0], width=130, height=1 )
    Box( box, grid=[2, 0], width=80, height=1 )
    Box( box, grid=[3, 0], width=80, height=1 )

    Text( box, grid=[0, 1], text="Status:", align="left" )
    self.holder_status_text = Text( box, grid=[1, 1], align="left" )

    Text( box, grid=[0, 2], text="Temp:", align="left" )
    self.holder_temp = Text( box, grid=[1, 2], align="left" )

    Text( box, grid=[0, 3], text="Autotune:", align="left" )
    self.autotune_status_text = Text( box, grid=[1, 3], align="left" )

    Text( box, grid=[0, 4], text="Stir:", align="left" )
    self.stir_speed = Text( box, grid=[1, 4], align="left" )

    self.temp_target_box = TextBox( box, grid=[2, 2], align="left", width=6, enabled=self.enabled )
    self.set_temp_btn = PushButton( box, command=self.set_temp, text="Set Temp", grid=[3, 2], width=12, align="left", pady=1, enabled=self.enabled )
    self.set_pid_enable_btn = PushButton( box, command=self.set_pid_running, text="", grid=[3, 1], width=12, align="left", pady=1, enabled=self.enabled )
    
    self.autotune_target_box = TextBox( box, grid=[2, 3], align="left", width=6, enabled=self.enabled )
    self.autotune_target_box.value = "50.00"
    self.autotune_btn = PushButton( box, command=self.set_autotune, text="", grid=[3, 3], width=12, align="left", pady=1, enabled=self.enabled )
    
    self.stir_target_box = TextBox( box, grid=[2, 4], align="left", width=6, enabled=self.enabled )
    self.stir_target_box.value = "20"
    self.stir_btn = PushButton( box, command=self.set_stir_running, text="", grid=[3, 4], width=12, align="left", pady=1, enabled=self.enabled )
    
#    spacer=Box( box, grid=[0, 4], width=100, height=10 )
#    spacer.bg="black"
    Box( box, grid=[4, 5], width=10, height=10 )
    Box( box, grid=[0, 5], width=80, height=1 )
    
    self.temp_c_target = self.get_temp()

  def get_temp( self ):
    valid, temp_c_target = self.holder.get_temp_target()
    if valid:
      temp_c_target = round( temp_c_target, 2 )
      self.temp_target_box.value = temp_c_target
    self.temp_c_target = temp_c_target
    return temp_c_target

  def set_temp( self ):
    try:
      temp = round( float( self.temp_target_box.value ), 2 )
      self.holder.set_pid_temp( temp )
      self.temp_c_target = self.get_temp()
    except:
      pass
  
  def set_autotune( self ):
    try:
      temp = round( float( self.autotune_target_box.value ), 2 )
      autotuning = 0 if self.autotuning else 1
      self.holder.set_autotune_running( autotuning, temp )
    except:
      pass
    
  def set_pid_running( self ):
    try:
      run = 0 if self.pid_enabled else 1
      #temp = round( float( self.temp_target_box.value ), 2 )
      #self.holder.set_pid_running( run, temp )
      self.holder.set_pid_running( run )
      #self.temp_c_target = self.get_temp()
    except:
      pass
  
  def set_stir_running( self ):
    try:
      run = 0 if self.stir_enabled else 1
      stir_speed_rps = int( self.stir_target_box.value )
      self.holder.set_stir_running( run, stir_speed_rps )
    except:
      pass
  
  def update( self ):
    if not self.enabled:
      self.holder_status_text.value = "Offline"
    else:
      valid, pid_status, pid_error = self.holder.get_pid_status()
      okay = valid
      valid, temp_c = self.holder.get_temp_actual()
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
        self.holder_status_text.value = "Connection Error"
      elif self.autotuning:
        self.holder_status_text.value = "Autotuning"
      else:
        if ( pid_status == 4 ):
          if ( pid_error == 2 ):
            self.holder_status_text.value = "No Sensor"
          else:
            self.holder_status_text.value = "Error ".format( pid_error )
        else:
          try:
            self.holder_status_text.value = "{}".format( self.pid_status_str[pid_status] )
          except:
            pass
      
      try:
        self.holder_temp.value = "{} / {}".format( round( temp_c, 2 ), round( self.temp_c_target, 2 ) )
        self.stir_speed.value = "{} RPS".format( stir_speed_actual_rps )
      except:
        pass
      
      self.pid_enabled = ( pid_status == 2 )
      self.stir_enabled = ( stir_status == 2 )
      
    if ( not self.pid_enabled ):
      self.set_pid_enable_btn.text = "Enable PID"
    else:
      self.set_pid_enable_btn.text = "Disable PID"
    
    if ( not self.autotuning ):
      self.autotune_btn.text = "Start Autotune"
    else:
      self.autotune_btn.text = "Abort Autotune"
    
    if ( not self.stir_enabled ):
      self.stir_btn.text = "Start Stir"
    else:
      self.stir_btn.text = "Stop Stir"
    
    try:
      self.autotune_status_text.value = "{}".format( self.autotune_status_str[autotune_status] )
    except:
      pass
