/*
 * Strobe PIC firmware v3 — free-run + hardware trigger (camera LineOut -> RC5).
 *
 * Packet types:
 *   1 SET_STROBE_ENABLE
 *   2 SET_STROBE_TIMING   (wait_ns, flash_ns; both clamped to 65535 us)
 *   3 SET_STROBE_HOLD
 *   4 GET_CAM_READ_TIME
 *   5 SET_TRIGGER_MODE    (0=software free-run, 1=hardware, camera LineOut -> RC5)
 *   6 GET_DIAG            (version, RC5 level, edge/flash counters, state)
 *   7 SELF_TEST           (5 LED blinks; verifies the LED path without a programmer)
 *
 * The MCC design had three independent defects, all bypassed here:
 *   - TMR1 is gated by RC5 (T1GE=1), so it only counts while the trigger line is
 *     high and cannot time the flash. Trigger detection is polled instead.
 *   - The TMR1 interrupt is the overflow flag, not gate-complete, so it does not
 *     fire once per frame.
 *   - CLC1/2 + TMR2/TMR4 latch after one cycle (TMR2==PR2 sticks while TMR2 is
 *     off, and TMR4 is held in reset by TMR2_postscaled), so the LED could sit
 *     dark or stuck on depending on the order timers were touched.
 *
 * LED drive is therefore taken off the CLC: RC7PPS is switched to LATxy so RC7 is
 * a plain GPIO. LC3G3POL is still written in the same places, so if the PPS change
 * were ineffective the previously working CLC3 hold path still drives the pin.
 *
 * The trigger input is active low: RC5 has a weak pull-up (WPUC) and the camera
 * opto-isolated output pulls it down, so exposure start is a falling edge.
 *
 * Build/flash: MPLAB X project strobe_pic (PICkit3/4). See FLASH_HARDWARE_TRIGGER.md
 */

/* Device header comes from <xc.h> via mcc.h, selected by the project's -mcpu.
 * Including a specific pic16f188xx.h here breaks every configuration whose
 * device differs (duplicate typedefs).
 */
#include "mcc_generated_files/mcc.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "common.h"
#include "spi.h"

#pragma warning disable 520

#ifndef _XTAL_FREQ
#define _XTAL_FREQ          32000000
#endif

#define FW_VERSION          3

#define STROBE_MAX_US       65535u

#define PACKET_TYPE_SET_STROBE_ENABLE   1
#define PACKET_TYPE_SET_STROBE_TIMING   2
#define PACKET_TYPE_SET_STROBE_HOLD     3
#define PACKET_TYPE_GET_CAM_READ_TIME   4
#define PACKET_TYPE_SET_TRIGGER_MODE    5
#define PACKET_TYPE_GET_DIAG            6
#define PACKET_TYPE_SELF_TEST           7

spi_packet_buf_t spi_packet;
uint8_t packet_type;
uint8_t packet_data[SPI_PACKET_BUF_SIZE];
uint8_t packet_data_size;
uint8_t return_buf[12];

uint16_t cam_read_time_us;
uint8_t trigger_mode = 0;
uint8_t strobe_enabled = 0;
uint8_t strobe_hold_active = 0;

/* Diagnostics read over SPI (packet 6). Only touched from the main loop. */
static uint16_t edge_count = 0;
static uint16_t trigger_count = 0;
static uint8_t rc5_last = 1;

static uint16_t strobe_wait_us = 32;
static uint16_t strobe_flash_us = 1000;

void set_trigger_mode( uint8_t mode );
void hardware_trigger_strobe( void );

static void delay_ms_var( uint16_t ms )
{
    while ( ms-- )
        __delay_ms( 1 );
}

/* 10 us granularity keeps loop overhead near 10% instead of ~100% at 1 us. */
static void delay_us_var( uint16_t us )
{
    uint16_t units = us / 10u;

    if ( units == 0u )
        units = 1u;

    while ( units-- )
        __delay_us( 10 );
}

/* Aborts early when a host command arrives, so long waits cannot stall SPI. */
static void delay_us_var_yield( uint16_t us )
{
    uint16_t units = us / 10u;

    if ( units == 0u )
        units = 1u;

    while ( units-- )
    {
        __delay_us( 10 );

        if ( spi_read_bytes_available() )
            return;
    }
}

static uint16_t ns_to_us( uint32_t ns )
{
    uint32_t us = ns / 1000u;

    if ( us == 0u )
        us = 1u;
    if ( us > STROBE_MAX_US )
        us = STROBE_MAX_US;

    return (uint16_t)us;
}

static void strobe_led_on( void )
{
    LATCbits.LATC7 = 1;
    LC3G3POL = 1;
}

static void strobe_led_off( void )
{
    LATCbits.LATC7 = 0;
    LC3G3POL = 0;
}

static void strobe_fire_pulse( void )
{
    strobe_led_on();
    delay_us_var( strobe_flash_us );
    strobe_led_off();
    trigger_count++;
}

static void strobe_self_test( void )
{
    uint8_t i;

    for ( i = 0; i < 5; i++ )
    {
        strobe_led_on();
        delay_ms_var( 250 );
        strobe_led_off();
        delay_ms_var( 250 );
    }

    if ( strobe_hold_active )
        strobe_led_on();
}

void set_strobe_enable( uint8_t enable )
{
    strobe_enabled = enable ? 1 : 0;

    if ( !enable && !strobe_hold_active )
        strobe_led_off();
}

void set_strobe_hold( uint8_t hold )
{
    strobe_hold_active = hold ? 1 : 0;

    if ( strobe_hold_active )
        strobe_led_on();
    else
        strobe_led_off();
}

void set_strobe_timing( uint32_t *wait_target_ns, uint32_t *flash_target_ns )
{
    strobe_wait_us = ns_to_us( *wait_target_ns );
    strobe_flash_us = ns_to_us( *flash_target_ns );

    /* Report back what will actually be used, in nanoseconds. */
    *wait_target_ns = (uint32_t)strobe_wait_us * 1000u;
    *flash_target_ns = (uint32_t)strobe_flash_us * 1000u;
}

void set_trigger_mode( uint8_t mode )
{
    trigger_mode = ( mode == 1 ) ? 1 : 0;

    /* Trigger detection is polled; the gated TMR1 interrupt stays disabled. */
    PIE4bits.TMR1IE = 0;
    rc5_last = (uint8_t)PORTCbits.RC5;
}

/* Kept because interrupt_manager.c references it. Polling replaced it, and
 * TMR1IE is held at 0, so this must stay empty to avoid touching counters
 * from interrupt context.
 */
void hardware_trigger_strobe( void )
{
}

static void strobe_service_trigger( void )
{
    uint8_t rc5_now = (uint8_t)PORTCbits.RC5;

    if ( rc5_now == rc5_last )
        return;

    rc5_last = rc5_now;
    edge_count++;

    if ( rc5_now == 0 )
    {
        /* TMR1 is gated by RC5, so it holds how long the line stayed high:
         * the camera readout gap. Saturate rather than report a wrapped value.
         */
        cam_read_time_us = PIR4bits.TMR1IF ? 0xFFFFu : TMR1_ReadTimer();

        /* Active low: exposure starts on the falling edge. */
        if ( strobe_enabled && ( trigger_mode == 1 ) && !strobe_hold_active )
            strobe_fire_pulse();
    }
    else
    {
        TMR1_WriteTimer( 0 );
        PIR4bits.TMR1IF = 0;
    }
}

static void strobe_service_free_run( void )
{
    if ( !strobe_enabled || ( trigger_mode != 0 ) || strobe_hold_active )
        return;

    /* Let pending host commands through before blocking on another cycle. */
    if ( spi_read_bytes_available() )
        return;

    strobe_fire_pulse();
    delay_us_var_yield( strobe_wait_us );
}

void main(void)
{
    err rc;

    SYSTEM_Initialize();

    /* Take RC7 off CLC3 so the LED is a plain GPIO (TRISC already makes it an
     * output). LC3G3POL is still written alongside LATC7 as a fallback.
     */
    RC7PPS = 0x00;
    strobe_led_off();

    /* Reproduce the CLC state the board is known to behave in: TMR4 running,
     * TMR2 pulsed once then stopped, so the CLC3 timer term cannot drive RC7.
     */
    T4CONbits.T4ON = 1;
    T2CONbits.T2ON = 1;
    delay_ms_var( 20 );
    T2CONbits.T2ON = 0;
    strobe_led_off();

    /* Boot blink: proves build, flash and LED path with no host or camera. */
    delay_ms_var( 300 );
    strobe_led_on();
    delay_ms_var( 300 );
    strobe_led_off();
    delay_ms_var( 300 );
    strobe_led_on();
    delay_ms_var( 300 );
    strobe_led_off();
    delay_ms_var( 300 );
    strobe_led_on();
    delay_ms_var( 300 );
    strobe_led_off();

    spi_init();
    spi_packet_clear( &spi_packet );

    cam_read_time_us = 0;
    trigger_mode = 0;
    strobe_enabled = 0;
    strobe_hold_active = 0;
    rc5_last = (uint8_t)PORTCbits.RC5;

    INTERRUPT_GlobalInterruptEnable();
    INTERRUPT_PeripheralInterruptEnable();

    while ( 1 )
    {
        if ( spi_packet_read( &spi_packet, &packet_type, (uint8_t *)&packet_data, &packet_data_size, SPI_PACKET_BUF_SIZE ) == ERR_OK )
        {
            switch ( packet_type )
            {
                case 0:
                    break;
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
                        uint32_t *strobe_flash_ns = (uint32_t *)&return_buf[5];
                        *strobe_wait_ns = *(uint32_t *)&packet_data[0];
                        *strobe_flash_ns = *(uint32_t *)&packet_data[4];
                        set_strobe_timing( strobe_wait_ns, strobe_flash_ns );
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
                case PACKET_TYPE_SET_TRIGGER_MODE:
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
                case PACKET_TYPE_GET_DIAG:
                {
                    if ( packet_data_size == 0 )
                    {
                        return_buf[0] = ERR_OK;
                        return_buf[1] = FW_VERSION;
                        return_buf[2] = (uint8_t)PORTCbits.RC5;
                        *(uint16_t *)&return_buf[3] = edge_count;
                        *(uint16_t *)&return_buf[5] = trigger_count;
                        return_buf[7] = trigger_mode;
                        return_buf[8] = (uint8_t)( ( strobe_enabled ? 1 : 0 ) | ( strobe_hold_active ? 2 : 0 ) );
                        spi_packet_write( packet_type, return_buf, 9 );
                    }
                    else
                    {
                        rc = ERR_PACKET_INVALID;
                        spi_packet_write( packet_type, &rc, 1 );
                    }
                    break;
                }
                case PACKET_TYPE_SELF_TEST:
                {
                    if ( packet_data_size == 0 )
                    {
                        rc = ERR_OK;
                        spi_packet_write( packet_type, &rc, 1 );
                        strobe_self_test();
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

        strobe_service_trigger();
        strobe_service_free_run();
    }
}
