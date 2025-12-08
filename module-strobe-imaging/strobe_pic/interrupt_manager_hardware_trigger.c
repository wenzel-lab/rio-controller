/**
  Modified Interrupt Manager for Hardware Trigger Support
  
  This file modifies interrupt_manager.c to add TMR1 interrupt handling
  for hardware trigger mode.
  
  Replace the existing interrupt_manager.c with this version, or merge
  the TMR1 interrupt handling into the existing file.
*/

#include "interrupt_manager.h"
#include "mcc.h"
#include "tmr1.h"

/* External function declaration for hardware trigger handler */
/* This function is defined in main_hardware_trigger.c */
extern void hardware_trigger_strobe( void );

void __interrupt() INTERRUPT_InterruptManager (void)
{
    // interrupt handler
    if(PIE0bits.IOCIE == 1 && PIR0bits.IOCIF == 1)
    {
        PIN_MANAGER_IOC();
    }
    else if(INTCONbits.PEIE == 1)
    {
        /* Check TMR1 interrupt first (hardware trigger) */
        if(PIE4bits.TMR1IE == 1 && PIR4bits.TMR1IF == 1)
        {
            PIR4bits.TMR1IF = 0;  // Clear interrupt flag
            
            /* Check if T1G (gate) triggered */
            if ( T1GCONbits.T1GGO == 0 )
            {
                /* Hardware trigger detected on T1G input */
                hardware_trigger_strobe();
                
                /* Restart single pulse acquisition for next trigger */
                TMR1_StartSinglePulseAcquisition();
            }
        }
        else if(PIE3bits.SSP1IE == 1 && PIR3bits.SSP1IF == 1)
        {
            SPI1_ISR();
        } 
        else
        {
            //Unhandled Interrupt
        }
    }      
    else
    {
        //Unhandled Interrupt
    }
}
/**
 End of File
*/

