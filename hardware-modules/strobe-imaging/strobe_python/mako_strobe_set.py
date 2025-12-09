import picommon
import pistrobe

picommon.spi_init( 0, 2, 30000 )

strobe = pistrobe.PiStrobe( picommon.PORT_STROBE, 0.1 )
result = strobe.set_enable( True )
print( result )
result = strobe.set_timing( 300, 100000 )
print( result )

picommon.spi_close()
