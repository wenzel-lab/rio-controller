/*
 * To do:
 * - Report if detected frame rate is slower than configured strobe pulse
 * 
 * #include <pic16f18857.h>
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

/* Packet Data */
spi_packet_buf_t spi_packet;
uint8_t packet_type;
uint8_t packet_data[SPI_PACKET_BUF_SIZE];
uint8_t packet_data_size;
uint8_t return_buf[9];

/* Strobe Data */
uint16_t cam_read_time_us;

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
    
    /* First scale both to ( ps / TIME_SCALING ) */
    /* These ticks are rounded. */
    /* Maximum target_time_ns value we can process without overflow:
     * ( ( UINT32_MAX - ( ( PS_PER_TICK >> 1 ) / TIME_SCALING ) ) / ( 1000 / TIME_SCALING ) )  // 42949657 -> 1374389 ticks = 42949656.25ns
     */
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

void set_strobe_enable( uint8_t enable )
{
    /* <enable> must be 0 or 1 */
    
    /* For some reason TMR2==PR2 input to CLC3 stays TRUE regardless
     * of any amount of TMR2-related register resetting while TMR2 is off.
     * Therefore I am leaving TMR4 on so that it will reach PR4 and cause
     * CLC3 output to go FALSE.
     */
    
//    T4CONbits.T4ON = enable;
    T2CONbits.T2ON = enable;
    T4CONbits.T4ON = 1;
//    CLC3CONbits.LC3EN = enable;
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
    
//    duration_prescale = 0;
//    duration_postscale = 0;
//    duration_period = 0;
    
// 7 0 10 8
// 7 0 20 15
// 7 0 39 25
// 7 0 255 188
    
    if ( ( *wait_target_ns > 0 ) && ( *duration_target_ns > 0 ) )
    {
        /* If time_ns==0 -> couldn't calculate register values */
        
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

void main(void)
{
    err rc;
    
// --------------------------------------------------------------------------
    
    SYSTEM_Initialize();
    
    spi_init();
    spi_packet_clear( &spi_packet );
    
    cam_read_time_us = 0;
    
// --------------------------------------------------------------------------
    
    INTERRUPT_GlobalInterruptEnable();
    INTERRUPT_PeripheralInterruptEnable();
    //INTERRUPT_GlobalInterruptDisable();
    //INTERRUPT_PeripheralInterruptDisable();
    
//    set_strobe_timing( 2000000, 2000000 );
//    set_strobe_enable( 1 );
    
//    while ( 1 );
    
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
                default:;
            }
        }
        
#if 1
        if ( T1GCONbits.T1GGO == 0 )
        {
            /* Strobe input "read back time" measured using Timer 1 */
            
            cam_read_time_us = TMR1_ReadTimer();
            TMR1_WriteTimer( 0 );
            TMR1_StartSinglePulseAcquisition();
        }
#endif
    }
}
