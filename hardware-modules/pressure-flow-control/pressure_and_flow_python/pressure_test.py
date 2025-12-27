import time
import picommon
import piflow

picommon.spi_init( 0, 2, 30000 )
flow = piflow.PiFlow( picommon.PORT_FLOW, 0.2 )

valid, id, id_valid = flow.get_id()
print( valid, id, id_valid )

valid = flow.set_pressure( [1000, 200, 300, 4000] )
print( valid )

valid, pressures = flow.get_pressure_actual()
print( valid, pressures )

picommon.spi_close()
