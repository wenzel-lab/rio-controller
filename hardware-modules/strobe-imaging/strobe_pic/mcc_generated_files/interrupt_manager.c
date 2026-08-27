/**
  Interrupt Manager — SPI + hardware strobe trigger (TMR1 / T1G)

  Merged from interrupt_manager_hardware_trigger.c so camera LineOut → T1G
  can fire one strobe pulse per frame when trigger_mode=1.
*/

#include "interrupt_manager.h"
#include "mcc.h"
#include "tmr1.h"

extern void hardware_trigger_strobe( void );

void __interrupt() INTERRUPT_InterruptManager (void)
{
    if(PIE0bits.IOCIE == 1 && PIR0bits.IOCIF == 1)
    {
        PIN_MANAGER_IOC();
    }
    else if(INTCONbits.PEIE == 1)
    {
        if(PIE4bits.TMR1IE == 1 && PIR4bits.TMR1IF == 1)
        {
            PIR4bits.TMR1IF = 0;
            if ( T1GCONbits.T1GGO == 0 )
            {
                hardware_trigger_strobe();
                TMR1_StartSinglePulseAcquisition();
            }
        }
        else if(PIE3bits.SSP1IE == 1 && PIR3bits.SSP1IF == 1)
        {
            SPI1_ISR();
        }
        else
        {
            /* Unhandled Interrupt */
        }
    }
    else
    {
        /* Unhandled Interrupt */
    }
}
