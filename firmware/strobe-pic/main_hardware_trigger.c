/*
 * Hardware Trigger Mode for Strobe Synchronization
 * 
 * This file contains modifications to main.c to support hardware-triggered strobe
 * synchronization. The strobe is triggered by camera frame start signal (XVS/fstrobe)
 * instead of software timing.
 * 
 * Key Changes:
 * - Added hardware trigger mode selection (SPI command)
 * - Added TMR1 interrupt handler for hardware trigger
 * - Modified strobe enable to work with hardware trigger mode
 * 
 * Hardware Connection:
 * - Camera XVS/fstrobe pin → GPIO → PIC T1G input (pin RB5, already configured)
 */

#include "mcc_generated_files/mcc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pic16f18856.h>
#include "common.h"
#include "spi.h"

#pragma warning disable 520     // Disable "not used" messages

/* Strobe Constants */
#define CLOCK_FREQ          32000000
#define PS_PER_TICK         ( 1000000000 / ( CLOCK_FREQ / 1000 ) )      // 31250 ps/tick
#define TIME_SCALING        10                                          // 31250 can be divided by 10 whole
#define MAX_TIME_NS         ( ( ( (uint32_t)PS_PER_TICK << 7 ) / 1000 ) * 16 * 255 )    // Max timer period = 522240 ticks = 16,320,000ns

/* Comms Constants */
#define PACKET_TYPE_SET_STROBE_ENABLE   1
#define PACKET_TYPE_SET_STROBE_TIMING   2
#define PACKET_TYPE_SET_STROBE_HOLD     3
#define PACKET_TYPE_GET_CAM_READ_TIME   4
#define PACKET_TYPE_SET_TRIGGER_MODE   5  // NEW: Hardware trigger mode selection

/* Packet Data */
spi_packet_buf_t spi_packet;
uint8_t packet_type;
uint8_t packet_data[SPI_PACKET_BUF_SIZE];
uint8_t packet_data_size;
uint8_t return_buf[9];

/* Strobe Data */
uint16_t cam_read_time_us;
uint8_t trigger_mode = 0;  // 0 = software trigger (current), 1 = hardware trigger (T1G input)
uint8_t strobe_enabled = 0;  // Track if strobe should be enabled (for hardware trigger mode)

/* Forward declarations */
uint32_t find_scalers_time( uint32_t target_time_ns, uint8_t *prescale, uint8_t *postscale, uint8_t *period );
void set_strobe_enable( uint8_t enable );
void set_strobe_hold( uint8_t hold );
void set_strobe_timing( uint32_t *wait_target_ns, uint32_t *duration_target_ns );
void set_trigger_mode( uint8_t mode );
void hardware_trigger_strobe( void );

/* Copy of find_scalers_time from original - unchanged */
uint32_t find_scalers_time( uint32_t target_time_ns, uint8_t *prescale, uint8_t *postscale, uint8_t *period )
{
    uint32_t ticks;
    uint32_t rem;
    uint32_t period_loop;
    int8_t postscale_loop;
    int8_t prescale_loop;
    uint32_t time_ns_loop;
    uint32_t time_ns_best;
    uint8_t postscale_best;
    uint8_t prescale_best;
    uint32_t period_best;
    
    if ( target_time_ns > MAX_TIME_NS )
        return 0;
    
    ticks = ( target_time_ns * ( 1000 / TIME_SCALING ) + ( ( PS_PER_TICK >> 1 ) / TIME_SCALING ) ) / ( PS_PER_TICK / TIME_SCALING );

    time_ns_best = 0;
    postscale_best = 0;
    prescale_best = 0;
    period_best = 0;

    for ( postscale_loop=16; postscale_loop>=1; postscale_loop-- )
    {
        rem = ticks / postscale_loop;

        for ( prescale_loop=7; prescale_loop>=0; prescale_loop-- )
        {
            if ( prescale_loop == 0 )
                period_loop = rem;
            else
                period_loop = ( ( rem >> ( prescale_loop - 1 ) ) + 1 ) >> 1;  // Round

            if ( ( period_loop > 0 ) && ( period_loop <= 0xFF ) && ( ( period_loop > 1 ) || ( prescale_loop > 0 ) ) )
            {
                time_ns_loop = ( ( ( ( (uint32_t)PS_PER_TICK / TIME_SCALING ) << prescale_loop ) * period_loop ) * postscale_loop ) / ( 1000 / TIME_SCALING );
                
                if ( labs( time_ns_loop - target_time_ns ) < labs( time_ns_best - target_time_ns ) )
                {
                    time_ns_best = time_ns_loop;
                    postscale_best = postscale_loop;
                    prescale_best = prescale_loop;
                    period_best = period_loop;
                }

                if ( time_ns_loop == target_time_ns )
                    break;
            }
        }
    }
    
    *prescale = prescale_best;
    *postscale = postscale_best - 1;
    *period = (uint8_t)( period_best - 1 );

    return time_ns_best;
}

/* Modified set_strobe_enable - now respects trigger mode */
void set_strobe_enable( uint8_t enable )
{
    strobe_enabled = enable ? 1 : 0;
    
    if ( trigger_mode == 0 )
    {
        /* Software trigger mode (original behavior) */
        T2CONbits.T2ON = enable;
        T4CONbits.T4ON = 1;
    }
    else
    {
        /* Hardware trigger mode - don't start TMR2 yet, wait for hardware trigger */
        /* TMR2 will be started by hardware trigger interrupt */
        T2CONbits.T2ON = 0;  // Keep TMR2 off until hardware trigger
        T4CONbits.T4ON = 1;  // Keep TMR4 on (duration timer)
    }
}

void set_strobe_hold( uint8_t hold )
{
    /* Hold strobe on regardless */
    LC3G3POL = hold ? 1 : 0;
}

void set_strobe_timing( uint32_t *wait_target_ns, uint32_t *duration_target_ns )
{
    uint8_t wait_prescale;
    uint8_t wait_postscale;
    uint8_t wait_period;
    uint8_t duration_prescale;
    uint8_t duration_postscale;
    uint8_t duration_period;
    uint32_t wait_ns;
    uint32_t duration_ns;
    uint8_t t4con_copy;
    
    *wait_target_ns = find_scalers_time( *wait_target_ns, &wait_prescale, &wait_postscale, &wait_period );
    *duration_target_ns = find_scalers_time( *duration_target_ns, &duration_prescale, &duration_postscale, &duration_period );
    
    if ( ( *wait_target_ns > 0 ) && ( *duration_target_ns > 0 ) )
    {
        /* Stop output temporarily */
        t4con_copy = T4CON;
        T4CON = 0;
        
        /* Configure timers and re-enable output if necessary */
        PR2 = wait_period;
        PR4 = duration_period;
        T2CON = ( T2CON & 0b10000000 ) | ( wait_prescale << 4 ) | wait_postscale;
        T4CON = ( t4con_copy & 0b10000000 ) | ( duration_prescale << 4 ) | duration_postscale;
    }
}

/* NEW: Set trigger mode (software vs hardware) */
void set_trigger_mode( uint8_t mode )
{
    trigger_mode = ( mode == 1 ) ? 1 : 0;
    
    if ( trigger_mode == 1 )
    {
        /* Hardware trigger mode - enable TMR1 interrupt */
        /* TMR1 is already configured for T1G input (pin RB5) */
        PIE4bits.TMR1IE = 1;  // Enable TMR1 interrupt
        PIR4bits.TMR1IF = 0;  // Clear interrupt flag
        
        /* Configure TMR1 for gate mode (already done in initialization) */
        /* TMR1 will trigger on T1G input (camera frame start signal) */
    }
    else
    {
        /* Software trigger mode - disable TMR1 interrupt */
        PIE4bits.TMR1IE = 0;  // Disable TMR1 interrupt
    }
}

/* NEW: Hardware trigger handler - called from interrupt manager */
/* This function is called by interrupt_manager.c when TMR1 interrupt occurs */

/* TMR1 Interrupt Handler - called from interrupt_manager.c */
/* This function is called by the interrupt manager when TMR1 interrupt occurs */
void hardware_trigger_strobe( void )
{
    if ( strobe_enabled && ( trigger_mode == 1 ) )
    {
        /* Hardware trigger detected - start strobe pulse sequence */
        /* Reset and start TMR2 (wait timer) */
        TMR2 = 0;  // Reset wait timer
        T2CONbits.T2ON = 1;  // Start wait timer
        /* TMR4 already running (duration timer) */
        
        /* Restart single pulse acquisition for next trigger */
        TMR1_StartSinglePulseAcquisition();
    }
}

void main(void)
{
    err rc;
    
// --------------------------------------------------------------------------
    
    SYSTEM_Initialize();
    
    spi_init();
    spi_packet_clear( &spi_packet );
    
    cam_read_time_us = 0;
    trigger_mode = 0;  // Default to software trigger mode
    strobe_enabled = 0;
    
// --------------------------------------------------------------------------
    
    INTERRUPT_GlobalInterruptEnable();
    INTERRUPT_PeripheralInterruptEnable();
    
    /* Initialize TMR1 for hardware trigger mode (if needed) */
    /* TMR1 is already initialized by SYSTEM_Initialize() */
    /* T1G input is already configured (pin RB5) */
    
    while ( 1 )
    {
        if ( spi_packet_read( &spi_packet, &packet_type, (uint8_t *)&packet_data, &packet_data_size, SPI_PACKET_BUF_SIZE ) == ERR_OK )
        {
            switch ( packet_type )
            {
                case 0:
                {
                    /* No or invalid packet */
                    break;
                }
                case PACKET_TYPE_SET_STROBE_ENABLE:
                {
                    if ( packet_data_size == 1 )
                    {
                        set_strobe_enable( packet_data[0] ? 1 : 0 );
                        rc = ERR_OK;
                    }
                    else
                        rc = ERR_PACKET_INVALID;
                    spi_packet_write( packet_type, &rc, 1 );
                    break;
                }
                case PACKET_TYPE_SET_STROBE_TIMING:
                {
                    if ( packet_data_size == 8 )
                    {
                        uint32_t *strobe_wait_ns = (uint32_t *)&return_buf[1];
                        uint32_t *strobe_period_ns = (uint32_t *)&return_buf[5];
                        *strobe_wait_ns = *(uint32_t *)&packet_data[0];
                        *strobe_period_ns = *(uint32_t *)&packet_data[4];
                        set_strobe_timing( strobe_wait_ns, strobe_period_ns );
                        return_buf[0] = ERR_OK;
                        spi_packet_write( packet_type, return_buf, 9 );
                    }
                    else
                    {
                        rc = ERR_PACKET_INVALID;
                        spi_packet_write( packet_type, &rc, 1 );
                    }
                    
                    break;
                }
                case PACKET_TYPE_SET_STROBE_HOLD:
                {
                    if ( packet_data_size == 1 )
                    {
                        set_strobe_hold( packet_data[0] ? 1 : 0 );
                        rc = ERR_OK;
                    }
                    else
                        rc = ERR_PACKET_INVALID;
                    spi_packet_write( packet_type, &rc, 1 );
                    break;
                }
                case PACKET_TYPE_GET_CAM_READ_TIME:
                {
                    if ( packet_data_size == 0 )
                    {
                        *(uint16_t *)&return_buf[1] = cam_read_time_us;
                        return_buf[0] = ERR_OK;
                        spi_packet_write( packet_type, return_buf, 3 );
                    }
                    else
                    {
                        rc = ERR_PACKET_INVALID;
                        spi_packet_write( packet_type, &rc, 1 );
                    }
                    break;
                }
                case PACKET_TYPE_SET_TRIGGER_MODE:  // NEW: Hardware trigger mode
                {
                    if ( packet_data_size == 1 )
                    {
                        set_trigger_mode( packet_data[0] ? 1 : 0 );
                        rc = ERR_OK;
                    }
                    else
                        rc = ERR_PACKET_INVALID;
                    spi_packet_write( packet_type, &rc, 1 );
                    break;
                }
                default:;
            }
        }
        
#if 1
        if ( T1GCONbits.T1GGO == 0 )
        {
            /* Strobe input "read back time" measured using Timer 1 */
            /* This is still used for measuring camera read time */
            cam_read_time_us = TMR1_ReadTimer();
            TMR1_WriteTimer( 0 );
            TMR1_StartSinglePulseAcquisition();
        }
#endif
    }
}

