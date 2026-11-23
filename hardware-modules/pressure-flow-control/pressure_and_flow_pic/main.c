/*
 * I2C Addresses:
 *   ADS1115 = 0x48
 *   PCA... = 0x70
 *   Sensirion SLF3S = 0x08
 *   Sensirion LG16 = 0x40
 */

#include <xc.h>
#include "common.h"
#include <libpic30.h>
#include <string.h>
#include <stdio.h>
#include "mcc_generated_files/mcc.h"
#include "spi.h"
#include "ads1115.h"
#include "eeprom.h"
#include "storage.h"
#include "sensirion_lg16.h"
#include "pca9544a.h"

/* Pressure Constants */
#define PRESSURE_SHL                        3
#define PRESSURE_ADC_REF_MV                 6144
#define PRESSURE_ADC_BITRES                 15
#define PRESSURE_ADC_MAX                    ( ( (uint16_t)1 << PRESSURE_ADC_BITRES ) - 1 )
#define PRESSURE_CTLR_REF_MV                5000
#define PRESSURE_CTLR_ZERO_MV               1000
#define PRESSURE_CTLR_RANGE_MV              ( PRESSURE_CTLR_REF_MV - PRESSURE_CTLR_ZERO_MV )
#define PRESSURE_CTLR_MBAR                  5000
#define PRESSURE_ADC_SCALE                  ( (int32_t)PRESSURE_ADC_MAX * PRESSURE_CTLR_RANGE_MV / PRESSURE_ADC_REF_MV )
#define PRESSURE_ADC_ZERO                   ( (int32_t)PRESSURE_ADC_MAX * PRESSURE_CTLR_ZERO_MV / PRESSURE_ADC_REF_MV )

/* Flow Constants */
#define FPID_DEFAULT_P                      200
#define FPID_DEFAULT_I                      100
#define FPID_DEFAULT_D                      1000
#define FPID_DIFF_FILT_SHIFT                3
#define FPID_DIFF_FILT_MUL                  ( ( 1 << FPID_DIFF_FILT_SHIFT ) - 1 )
#define FPID_TERM_MAX                       ( INT32_MAX >> 2 )  // Allows for 4 terms to be added in PID
#define FPID_P_TERM_LIMIT                   ( (int32_t)1000 << FPID_I_SHIFT )
#define FPID_I_CHANGE_LIMIT                 ( (int32_t)1000 << FPID_I_SHIFT )
//#define FPID_P_TERM_LIMIT                   FPID_TERM_MAX
#define FPID_OUTPUT_SLEW_LIMIT              100
#define FPID_I_SHIFT                        12

/* Flow / Pressure Macros */
#define ADC_CHAN_MAX                        ( NUM_PRESSURE_CLTRLS - 1 )

// MODIFIED: ADC datarate configuration for 100 Hz flow updates
// ADC datarate options and their conversion times:
//   DATARATE_128SPS  -> 7.81 ms/conversion x 4 ch = 31.2 ms scan
//   DATARATE_250SPS  -> 4.00 ms/conversion x 4 ch = 16.0 ms scan  
//   DATARATE_475SPS  -> 2.11 ms/conversion x 4 ch =  8.4 ms scan
//   DATARATE_860SPS  -> 1.16 ms/conversion x 4 ch =  4.6 ms scan (highest noise)
//
// Set ADC_DATARATE and ADC_PERIOD_MS together - ADC_PERIOD_MS must be >=
// (conversion_time_ms x NUM_PRESSURE_CLTRLS + margin_ms).
#define ADC_DATARATE          DATARATE_475SPS // Optimized for stable operation
#define ADC_PERIOD_MS_860SPS  6      // 4.6ms scan + 1.4ms margin
#define ADC_PERIOD_MS_475SPS  8      // 8.4ms scan + 0.6ms margin (optimized)
#define ADC_PERIOD_MS_250SPS  18     // 16.0ms scan + 2.0ms margin
#define ADC_PERIOD_MS_128SPS  35     // 31.2ms scan + 3.8ms margin

// Active period - change ADC_DATARATE above and update this line:
#undef  ADC_PERIOD_MS
#define ADC_PERIOD_MS         ADC_PERIOD_MS_475SPS // Optimized 475SPS timing
#define PRESSURE_ADC_TO_MBARSHL(adc)        ( ( ( ( ( (int32_t)( (int16_t)(adc) ) ) - PRESSURE_ADC_ZERO ) << PRESSURE_SHL ) * PRESSURE_CTLR_MBAR / PRESSURE_ADC_SCALE ) )
//#define PRESSURE_ADC_TO_MBARSHL(adc)        ( ( ( ( ( (int32_t)( (int16_t)(adc) ) ) - PRESSURE_ADC_ZERO ) << PRESSURE_SHL ) * 1000 / PRESSURE_ADC_SCALE ) )

/* Comms Constants */
#define PACKET_TYPE_GET_ID                  1
#define PACKET_TYPE_SET_PRESSURE_TARGET     2
#define PACKET_TYPE_GET_PRESSURE_TARGET     3
#define PACKET_TYPE_GET_PRESSURE_ACTUAL     4
#define PACKET_TYPE_SET_FLOW_TARGET         5
#define PACKET_TYPE_GET_FLOW_TARGET         6
#define PACKET_TYPE_GET_FLOW_ACTUAL         7
#define PACKET_TYPE_SET_CONTROL_MODE        8
#define PACKET_TYPE_GET_CONTROL_MODE        9
#define PACKET_TYPE_SET_FPID_CONSTS         10
#define PACKET_TYPE_GET_FPID_CONSTS         11
#define PACKET_TYPE_SET_ACTIVE_SENSORS       12
#define PACKET_TYPE_GET_ACTIVE_SENSORS       13
/* v3 additions (existing packet formats are unchanged) */
#define PACKET_TYPE_GET_FLOW_STATS           14  /* [chan U8] -> [err][ok U32][crc_err U32][i2c_err U32][not_ready U32][saturated U32 desde v3.3] */
#define PACKET_TYPE_SET_FLOW_RESOLUTION      15  /* [bits U8 9..16] -> [err] */
#define PACKET_TYPE_GET_FLOW_RESOLUTION      16  /* [] -> [err][bits U8] */
#define PACKET_TYPE_GET_FW_VERSION           17  /* [] -> [err][major U8][minor U8] */
/* v3.2 */
#define PACKET_TYPE_GET_FLOW_BATCH           18  /* [chan U8][since_seq U16] -> [err][n U8][seq0 U16][scale U16][n x (t_ms U32, flow_raw I16)][crc8] (t_ms U16 hasta v3.2) */

#define FW_VERSION_MAJOR                     3
#define FW_VERSION_MINOR                     4

/* v3.3: |raw| at which the LG16 clips (+-120 ul/min); readings at the rail are
 * valid transfers but not valid measurements, so they are counted per channel. */
#define FLOW_SATURATION_COUNTS               32400

/* v3.2: per-channel history of accepted readings, indexed by the ok counter.
 * 128 samples = 1.1 s at 13 bit, 0.6 s at 12 bit: covers host hiccups. */
#define FLOW_RING_SIZE                       128
#define FLOW_RING_MASK                       ( FLOW_RING_SIZE - 1 )
#define FLOW_BATCH_MAX_SAMPLES               16
#if ( FLOW_RING_SIZE & ( FLOW_RING_SIZE - 1 ) )
#error "FLOW_RING_SIZE must be a power of two"
#endif

typedef struct
{
    uint32_t t_ms;      /* PIC millisecond timer at the time the reading was accepted (v3.3: 32 bit, wrap 49.7 days) */
    int16_t flow_raw;   /* sensor raw value; ul/h = raw * 60 / scale */
} flow_sample_t;

/* DAC Constants */
typedef enum
{
    DAC_CHAN_A      = 0b000,
    DAC_CHAN_B      = 0b001,
    DAC_CHAN_C      = 0b010,
    DAC_CHAN_D      = 0b011,
    DAC_CHAN_ALL    = 0b111,
} E_DAC_CHAN;

/* ADC Constants */
typedef enum
{
    ADC_STATE_START,
    ADC_STATE_SAMPLE,
    ADC_STATE_WAIT,
} E_ADC_STATE;

const uint8_t adc_map[NUM_PRESSURE_CLTRLS] = {3, 2, 0, 1};

typedef enum
{
    PRESSURE_CTRL_STATE_UNCONFIGURED,
    PRESSURE_CTRL_STATE_READY,
    PRESSURE_CTRL_STATE_RUNNING,
    PRESSURE_CTRL_STATE_ERROR
} E_PRESSURE_CTRL_STATE;

/* Flow Constants */
const uint8_t flow_map[NUM_PRESSURE_CLTRLS] = {1, 0, 2, 3};

typedef enum
{
    FLOW_CTRL_STATE_UNCONFIGURED,
    FLOW_CTRL_STATE_READY,
    FLOW_CTRL_STATE_RUNNING,
    FLOW_CTRL_STATE_ERROR
} E_FLOW_CTRL_STATE;

/* String Constants */
const char *OK_STR = "OK";
const char *FAIL_STR = "FAIL";

/* System Constants */
typedef enum
{
    CTRL_MODE_ZERO,
    CTRL_MODE_PRESSURE_OPEN_LOOP,
    CTRL_MODE_PRESSURE,
    CTRL_MODE_FLOW
} E_CTRL_MODE;

/* System Data */
uint8_t device_id[] = "MICROFLOW";
bool eeprom_okay;
bool adc_okay;
bool mux_okay;
volatile uint16_t timer_ms;
volatile uint16_t timer_ms_hi;  /* v3.3: high word; timer_now32() composes the 32-bit time */
E_CTRL_MODE ctrl_modes[NUM_PRESSURE_CLTRLS];

/* Pressure Data */
E_PRESSURE_CTRL_STATE pressure_ctrl_state[NUM_PRESSURE_CLTRLS];
volatile int16_t pressure_mbar_shl_actual[NUM_PRESSURE_CLTRLS];
volatile uint16_t pressure_mbar_shl_output[NUM_PRESSURE_CLTRLS];
uint16_t pressure_mbar_shl_target[NUM_PRESSURE_CLTRLS];
E_ADC_STATE adc_state;
uint8_t adc_go = 0;
uint8_t adc_chan;
uint16_t adc_time;
// MODIFIED: Use configurable ADC datarate
ads1115_datarate adc_datarate = ADC_DATARATE;
ads1115_fsr_gain adc_gain = FSR_6_144;
uint8_t adc_i2c_addr = ADS1115_ADDR_GND;
ads1115_task_t adc_task;

/* Flow Data */
E_FLOW_CTRL_STATE flow_ctrl_state[NUM_PRESSURE_CLTRLS];
volatile int16_t flow_raw_actual[NUM_PRESSURE_CLTRLS];
int16_t flow_raw_target[NUM_PRESSURE_CLTRLS];
uint16_t flow_scales_ul_min[NUM_PRESSURE_CLTRLS];
bool flow_present[NUM_PRESSURE_CLTRLS];

// MODIFIED: Added flow refresh counter for duplicate detection
volatile uint16_t flow_refresh_counter = 0;   // v3.1: advances only when a channel accepted a new reading
// MODIFIED: Added active sensor mask for dynamic sensor selection
volatile uint8_t active_sensor_mask = 0b1111;  // All 4 sensors active by default (bit 0=sensor0, bit3=sensor3)
/* v3: per-channel read statistics (wrap at 2^32; host computes deltas) */
uint32_t flow_stats_ok[NUM_PRESSURE_CLTRLS];        // readings accepted (I2C ok + CRC ok)
uint32_t flow_stats_crc_err[NUM_PRESSURE_CLTRLS];   // readings rejected by CRC-8
uint32_t flow_stats_i2c_err[NUM_PRESSURE_CLTRLS];   // mux or sensor I2C failures (timeouts, bus errors)
uint32_t flow_stats_not_ready[NUM_PRESSURE_CLTRLS]; // polls NACKed because the measurement was still running (benign)
uint32_t flow_stats_saturated[NUM_PRESSURE_CLTRLS]; // v3.3: accepted readings at the +-32400 rail (sensor out of range)
/* v3: sensor measurement resolution applied to all present sensors */
uint8_t flow_resolution_bits = SENSIRION_RESOLUTION_DEFAULT_BITS;
/* v3.2: free-running measurement scheduler (see poll_flows) */
flow_sample_t flow_ring[NUM_PRESSURE_CLTRLS][FLOW_RING_SIZE];
bool flow_pending[NUM_PRESSURE_CLTRLS];     /* a measurement is believed to be in progress */
uint16_t flow_trig_ms[NUM_PRESSURE_CLTRLS]; /* timer_ms when it was triggered */
uint16_t flow_poll_ms[NUM_PRESSURE_CLTRLS]; /* timer_ms of the last read attempt (max one poll per ms) */
uint8_t flow_tmin_ms = 8;                   /* min processing time of the active resolution */
int8_t mux_selected = -1;                   /* PCA9544A channel currently routed, -1 = unknown */
uint8_t pca9544a_i2c_addr = 0b1110000;
volatile int32_t fpid_integrated[NUM_PRESSURE_CLTRLS];
int32_t fpid_windup_limit = 100;
uint16_t fpid_p[NUM_PRESSURE_CLTRLS];
uint16_t fpid_i[NUM_PRESSURE_CLTRLS];
uint16_t fpid_d[NUM_PRESSURE_CLTRLS];
volatile int32_t fpid_diff[NUM_PRESSURE_CLTRLS];
volatile int32_t fpid_error_prev[NUM_PRESSURE_CLTRLS];

/* Packet Data */
uint8_t slave_select;
spi_packet_buf_t spi_packet;
uint8_t packet_type;
uint8_t packet_data[SPI_PACKET_BUF_SIZE];
uint8_t packet_data_size;

static inline int32_t constrain_i32( int32_t value, int32_t min, int32_t max )
{
    if ( value < min )
        return min;
    else if ( value > max )
        return max;
    else return value;
}

void dac_cmd( uint8_t cmd, E_DAC_CHAN chan, uint16_t value )
{
    struct
    {
        uint8_t unused_byte;
        uint8_t value_low;
        uint8_t value_high;
        uint8_t chan : 3;
        uint8_t cmd : 3;
        uint8_t unused : 2;
    } data;
    
    data.cmd = cmd;
    data.chan = chan;
    data.value_high = value >> 8;
    data.value_low = value & 0xFF;
    
    SPI2_Exchange32bit( *(uint32_t *)&data );
}

void dac_reset( void )
{
    dac_cmd( 0b101, 0, 0 );                 // Software reset
}

void dac_ref_internal( uint8_t internal )
{
    dac_cmd( 0b111, 0, internal ? 1 : 0 );  // Internal reference -> 5V range
}

void dac_write_and_update( E_DAC_CHAN dac_chan, uint16_t value )
{
    dac_cmd( 0b011, dac_chan, value );
}

void dac_write_ldac( E_DAC_CHAN dac_chan, uint16_t value, uint8_t update_all )
{
    dac_cmd( update_all ? 0b010 : 0b000, dac_chan, value );
}

void set_pressures( void )
{
    dac_write_ldac( DAC_CHAN_A, ( ( (int32_t)pressure_mbar_shl_output[0] * 0xFFFF ) >> PRESSURE_SHL ) / PRESSURE_CTLR_MBAR, 0 );
    dac_write_ldac( DAC_CHAN_B, ( ( (int32_t)pressure_mbar_shl_output[1] * 0xFFFF ) >> PRESSURE_SHL ) / PRESSURE_CTLR_MBAR, 0 );
    dac_write_ldac( DAC_CHAN_C, ( ( (int32_t)pressure_mbar_shl_output[2] * 0xFFFF ) >> PRESSURE_SHL ) / PRESSURE_CTLR_MBAR, 0 );
    dac_write_ldac( DAC_CHAN_D, ( ( (int32_t)pressure_mbar_shl_output[3] * 0xFFFF ) >> PRESSURE_SHL ) / PRESSURE_CTLR_MBAR, 1 );
    /*
    dac_write_ldac( DAC_CHAN_B, pressure_mbar_shl_output[1], 0 );
    dac_write_ldac( DAC_CHAN_C, pressure_mbar_shl_output[2], 0 );
    dac_write_ldac( DAC_CHAN_D, pressure_mbar_shl_output[3], 1 );
    */
}

/* v3.2 forward declarations (defined after the packet handlers) */
err select_flow_mux( uint8_t chan );
void flow_apply_resolution_timing( void );

err parse_packet_get_id( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    err rc = ERR_OK;
    uint8_t i;
    uint8_t return_buf[ sizeof(err) + sizeof(device_id)];
    return_buf[0] = ERR_OK;
    for ( i=0; i<sizeof(device_id); i++ )
        return_buf[i+1] = device_id[i];
//    memcpy( &return_buf[1], device_id, sizeof(device_id) );
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_set_pressure_target( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data: n*[ [Controller Mask U8][Pressure mbar U16>>PRESSURE_SHL] ] */

    err rc = ERR_OK;
    uint8_t *press_data_ptr = packet_data;
    uint8_t chan_mask;
    uint8_t chan;
    uint16_t pressures_mbar[NUM_PRESSURE_CLTRLS];
    uint16_t pressure_mbar_shl;
    int16_t data_size = packet_data_size;
    
    memcpy( pressures_mbar, pressure_mbar_shl_target, sizeof(pressure_mbar_shl_target) );
    
    while ( data_size >= ( 1 + sizeof(pressure_mbar_shl) ) )
    {
        /* U8 mask + U16 flow */
        chan_mask = *press_data_ptr++;
        pressure_mbar_shl = ( press_data_ptr[1] << 8 ) | press_data_ptr[0];
        press_data_ptr += sizeof(pressure_mbar_shl);
        data_size -= ( 1 + sizeof(pressure_mbar_shl) );

        for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        {
            if ( chan_mask & 0x01 )
                pressures_mbar[chan] = pressure_mbar_shl;
            chan_mask >>= 1;
        }
    }
    
    if ( data_size != 0 )
        rc = ERR_PACKET_INVALID;
    else
    {
        memcpy( pressure_mbar_shl_target, pressures_mbar, sizeof(pressures_mbar) );
//        set_pressures();
        spi_packet_write( packet_type, &rc, 1 );
    }
    
    return rc;
}

err parse_packet_get_pressure_target( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8]4x[Pressure mbar U16>>PRESSURE_SHL] */
    
    err rc = ERR_OK;
    uint8_t i;
    uint8_t return_buf[ sizeof(err) + (NUM_PRESSURE_CLTRLS*sizeof(int16_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    for ( i=0; i<NUM_PRESSURE_CLTRLS; i++ )
    {
        COPY_16BIT_TO_PTR( return_buf_ptr, pressure_mbar_shl_target[i] );
        return_buf_ptr += sizeof(int16_t);
    }
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_get_pressure_actual( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8]4x[Pressure mbar I16>>PRESSURE_SHL] */
    
    err rc = ERR_OK;
    uint8_t i;
    uint8_t return_buf[ sizeof(err) + (NUM_PRESSURE_CLTRLS*sizeof(int16_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    for ( i=0; i<NUM_PRESSURE_CLTRLS; i++ )
    {
        COPY_16BIT_TO_PTR( return_buf_ptr, pressure_mbar_shl_actual[i] );
//        *(int16_t *)return_buf_ptr = pressure_mbar_shl_actual[i];
        return_buf_ptr += sizeof(int16_t);
    }
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_set_flow_target( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data: n*[ [Controller Mask U8][Flow ul/hr I16] ] */

    err rc = ERR_OK;
    uint8_t *flow_data_ptr = packet_data;
    uint8_t chan_mask;
    uint8_t chan;
    int16_t flows_raw_target[NUM_PRESSURE_CLTRLS];
    int16_t flow_target_ul_hr;
    int16_t data_size = packet_data_size;
    bool valid = true;
    
    memcpy( flows_raw_target, flow_raw_target, sizeof(flow_raw_target) );
    
    while ( data_size >= ( 1 + sizeof(flow_target_ul_hr) ) )
    {
        /* U8 mask + U16 flow */
        chan_mask = *flow_data_ptr++;
        flow_target_ul_hr = ( flow_data_ptr[1] << 8 ) | flow_data_ptr[0];
        flow_data_ptr += sizeof(flow_target_ul_hr);
        data_size -= ( 1 + sizeof(flow_target_ul_hr) );
        
        if ( flow_target_ul_hr > ( (int32_t)INT16_MAX * 60 / flow_scales_ul_min[chan] ) )
        {
            /* Target too large to fit */
            valid = false;
        }
        else
        {
            for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
            {
                if ( chan_mask & 0x01 )
                    flows_raw_target[chan] = (int32_t)flow_target_ul_hr * flow_scales_ul_min[chan] / 60;
                chan_mask >>= 1;
            }
        }
    }
    
    if ( ( data_size != 0 ) || ( !valid ) )
        rc = ERR_PACKET_INVALID;
    else
    {
        memcpy( (void *)flow_raw_target, flows_raw_target, sizeof(flows_raw_target) );
        spi_packet_write( packet_type, &rc, 1 );
    }
    
    return rc;
}

err parse_packet_get_flow_target( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8]4x[Flow target ul/hr I16] */
    
    err rc = ERR_OK;
    uint8_t chan;
    uint8_t return_buf[ sizeof(err) + (NUM_PRESSURE_CLTRLS*sizeof(int16_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        int16_t flow_scaled = (int32_t)flow_raw_target[chan] * 60 / flow_scales_ul_min[chan];
        COPY_16BIT_TO_PTR( return_buf_ptr, flow_scaled );
        return_buf_ptr += sizeof(int16_t);
    }
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_get_flow_actual( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    // MODIFIED: Response layout now includes refresh counter
    // Return: [err U8][refresh_counter U16][4 × flow_ul_hr I16]
    
    err rc = ERR_OK;
    uint8_t chan;
    // MODIFIED: Increased buffer size to accommodate refresh counter
    uint8_t return_buf[ sizeof(err) + sizeof(uint16_t) + (NUM_PRESSURE_CLTRLS*sizeof(int16_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    // MODIFIED: Insert refresh counter before flow data
    uint16_t counter_snapshot = flow_refresh_counter;
    COPY_16BIT_TO_PTR(return_buf_ptr, counter_snapshot);
    return_buf_ptr += sizeof(uint16_t);
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        int16_t flow_scaled = (int32_t)flow_raw_actual[chan] * 60 / flow_scales_ul_min[chan];   // ul/hr
        COPY_16BIT_TO_PTR( return_buf_ptr, flow_scaled );
//        *(int16_t *)return_buf_ptr = flow_raw_actual[chan] / flow_scales_ul_min[chan];
        return_buf_ptr += sizeof(int16_t);
    }
    
    // MODIFIED: Response size now includes refresh counter (11 bytes vs 9 bytes)
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err flow_ctrl_start( uint8_t chan, int16_t flow_rate_raw )
{
    err rc = ERR_OK;
    
    if ( ( flow_ctrl_state[chan] != FLOW_CTRL_STATE_READY ) &&
         ( flow_ctrl_state[chan] != FLOW_CTRL_STATE_RUNNING ) )
        rc = ERR_ERROR;
    else
    {
        /** Disable interrupt */
        flow_raw_target[chan] = flow_rate_raw;
        fpid_integrated[chan] = 0;
        fpid_error_prev[chan] = flow_raw_target[chan] - flow_raw_actual[chan];
        flow_ctrl_state[chan] = FLOW_CTRL_STATE_RUNNING;
        ctrl_modes[chan] = CTRL_MODE_FLOW;
        /** Enable interrupt */
    }
    
    return rc;
}

void set_ctrl_modes( E_CTRL_MODE *ctrl_modes_new )
{
    uint8_t chan;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        ctrl_modes[chan] = ctrl_modes_new[chan];
        
        switch ( ctrl_modes[chan] )
        {
            case CTRL_MODE_ZERO:
                // Intentional drop-through
            case CTRL_MODE_PRESSURE_OPEN_LOOP:
                if ( pressure_ctrl_state[chan] == PRESSURE_CTRL_STATE_RUNNING )
                    pressure_ctrl_state[chan] = PRESSURE_CTRL_STATE_READY;
                if ( flow_ctrl_state[chan] == FLOW_CTRL_STATE_RUNNING )
                    flow_ctrl_state[chan] = FLOW_CTRL_STATE_READY;
                break;
            case CTRL_MODE_PRESSURE:
                if ( flow_ctrl_state[chan] == FLOW_CTRL_STATE_RUNNING )
                    flow_ctrl_state[chan] = FLOW_CTRL_STATE_READY;
//                if ( pressure_ctrl_state[chan] == PRESSURE_CTRL_STATE_READY )
//                    pressure_ctrl_state[chan] = PRESSURE_CTRL_STATE_RUNNING;
                break;
            case CTRL_MODE_FLOW:
                if ( pressure_ctrl_state[chan] == PRESSURE_CTRL_STATE_RUNNING )
                    pressure_ctrl_state[chan] = PRESSURE_CTRL_STATE_READY;
                if ( flow_ctrl_state[chan] == FLOW_CTRL_STATE_READY )
                {
                    flow_ctrl_start( chan, flow_raw_target[chan] );
//                    flow_ctrl_state[chan] = FLOW_CTRL_STATE_RUNNING;
                }
                break;
            default:;
        }
    }
}

err parse_packet_set_control_mode( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data: n*[ [Controller Mask U8][Control Mode U8] ] */

    err rc = ERR_OK;
    uint8_t *ctrl_mode_data_ptr = packet_data;
    uint8_t chan_mask;
    uint8_t chan;
    E_CTRL_MODE ctrl_modes_new[NUM_PRESSURE_CLTRLS];
    uint8_t ctrl_mode;
    int16_t data_size = packet_data_size;
    bool valid = true;
    
    memcpy( ctrl_modes_new, ctrl_modes, sizeof(ctrl_modes) );
    
    while ( ( data_size >= ( 1 + sizeof(ctrl_mode) ) ) && valid )
    {
        /* U8 mask + U16 flow */
        chan_mask = *ctrl_mode_data_ptr++;
        ctrl_mode = ( ctrl_mode_data_ptr[1] << 8 ) | ctrl_mode_data_ptr[0];
        ctrl_mode_data_ptr += sizeof(ctrl_mode);
        data_size -= ( 1 + sizeof(ctrl_mode) );
        
        if ( ctrl_mode > CTRL_MODE_FLOW )
            valid = false;
        else
        {
            for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
            {
                if ( chan_mask & 0x01 )
                    ctrl_modes_new[chan] = ctrl_mode;
                chan_mask >>= 1;
            }
        }
    }
    
    if ( ( data_size != 0 ) || ( !valid ) )
        rc = ERR_PACKET_INVALID;
    else
    {
        set_ctrl_modes( ctrl_modes_new );
        spi_packet_write( packet_type, &rc, 1 );
    }
    
    return rc;
}

err parse_packet_get_control_mode( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8]4x[Control Mode U8] */
    
    err rc = ERR_OK;
    uint8_t chan;
    uint8_t return_buf[ sizeof(err) + (NUM_PRESSURE_CLTRLS*sizeof(uint8_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        *return_buf_ptr = ctrl_modes[chan];
        return_buf_ptr += sizeof(uint8_t);
    }
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_set_fpid_consts( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data: n*[ [Controller Mask U8][PID_P U16][PID_I U16][PID_D U16] ] */

    err rc = ERR_OK;
    uint8_t *data_ptr = packet_data;
    uint8_t chan_mask;
    uint8_t chan;
    uint16_t pid_consts[3];
    int16_t data_size = packet_data_size;
    bool valid = true;
    
    while ( ( data_size >= ( 1 + ( 3 * sizeof(uint16_t) ) ) ) && valid && ( rc == ERR_OK ) )
    {
        /* U8 mask + 3x U16 PID  */
        chan_mask = *data_ptr++;
        pid_consts[0] = ( data_ptr[1] << 8 ) | data_ptr[0];
        pid_consts[1] = ( data_ptr[3] << 8 ) | data_ptr[2];
        pid_consts[2] = ( data_ptr[5] << 8 ) | data_ptr[4];
        data_ptr += 3 * sizeof(uint16_t);
        data_size -= ( 1 + ( 3 * sizeof(uint16_t) ) );
        
        for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        {
            if ( chan_mask & 0x01 )
            {
                /** Disable interrupt */
                fpid_p[chan] = pid_consts[0];
                fpid_i[chan] = pid_consts[1];
                fpid_d[chan] = pid_consts[2];
                /** Enable interrupt */
                rc = store_save_fpid_consts( chan, pid_consts );
            }
            chan_mask >>= 1;
        }
    }
    
    if ( ( data_size != 0 ) || ( !valid ) )
        rc = ERR_PACKET_INVALID;
    else
        spi_packet_write( packet_type, &rc, 1 );
    
    return rc;
}

err parse_packet_get_fpid_consts( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8]4x([PID_P U16][PID_I U16][PID_D U16]) */
    
    err rc = ERR_OK;
    uint8_t chan;
    uint8_t return_buf[ sizeof(err) + (NUM_PRESSURE_CLTRLS*3*sizeof(uint16_t)) ];
    uint8_t *return_buf_ptr;
    
    return_buf_ptr = return_buf;
    *return_buf_ptr++ = ERR_OK;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        COPY_16BIT_TO_PTR( return_buf_ptr, fpid_p[chan] );
        return_buf_ptr += sizeof(uint16_t);
        COPY_16BIT_TO_PTR( return_buf_ptr, fpid_i[chan] );
        return_buf_ptr += sizeof(uint16_t);
        COPY_16BIT_TO_PTR( return_buf_ptr, fpid_d[chan] );
        return_buf_ptr += sizeof(uint16_t);
    }
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    
    return rc;
}

err parse_packet_set_active_sensors( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data: [Sensor Mask U8] - bit 0=sensor0, bit3=sensor3 */
    
    err rc = ERR_OK;
    uint8_t sensor_mask;
    
    if ( packet_data_size != 1 )
    {
        rc = ERR_PACKET_INVALID;
    }
    else
    {
        sensor_mask = packet_data[0];
        
        // MODIFIED: Validate sensor mask - only allow bits 0-3
        if ( sensor_mask & 0xF0 )
        {
            // Invalid bits set
            rc = ERR_PACKET_INVALID;
        }
        else
        {
            // MODIFIED: Set active sensor mask
            active_sensor_mask = sensor_mask;
        }
    }
    
    /* v3.2: reply only on success; on error the main loop sends the single [err]
     * reply (previously both were sent, leaving a stale packet in the buffer). */
    if ( rc == ERR_OK )
        spi_packet_write( packet_type, &rc, 1 );
    return rc;
}

err parse_packet_get_active_sensors( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8][Sensor Mask U8] */
    
    err rc = ERR_OK;
    uint8_t return_buf[ sizeof(err) + sizeof(uint8_t) ];
    
    return_buf[0] = ERR_OK;
    return_buf[1] = active_sensor_mask;
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    return rc;
}

/* ---- v3 packets ---------------------------------------------------------- */

err parse_packet_get_flow_stats( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data:   [chan U8]
     * Return: [err U8][ok U32][crc_err U32][i2c_err U32][not_ready U32][saturated U32]  (little-endian)
     * saturated (v3.3) appended at the end: old hosts read the first 17 bytes unchanged. */

    err rc = ERR_OK;
    uint8_t chan;
    uint8_t return_buf[ sizeof(err) + 5*sizeof(uint32_t) ];
    uint8_t *return_buf_ptr = return_buf;
    
    if ( packet_data_size != 1 )
        rc = ERR_PACKET_INVALID;
    else
    {
        chan = packet_data[0];
        if ( chan >= NUM_PRESSURE_CLTRLS )
            rc = ERR_PACKET_INVALID;
    }
    
    /* On error the caller (main loop) sends the [err] reply, like the other handlers. */
    if ( rc == ERR_OK )
    {
        *return_buf_ptr++ = ERR_OK;
        COPY_32BIT_TO_PTR( return_buf_ptr, flow_stats_ok[chan] );      return_buf_ptr += sizeof(uint32_t);
        COPY_32BIT_TO_PTR( return_buf_ptr, flow_stats_crc_err[chan] ); return_buf_ptr += sizeof(uint32_t);
        COPY_32BIT_TO_PTR( return_buf_ptr, flow_stats_i2c_err[chan] ); return_buf_ptr += sizeof(uint32_t);
        COPY_32BIT_TO_PTR( return_buf_ptr, flow_stats_not_ready[chan] ); return_buf_ptr += sizeof(uint32_t);
        COPY_32BIT_TO_PTR( return_buf_ptr, flow_stats_saturated[chan] ); return_buf_ptr += sizeof(uint32_t);

        spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    }
    
    return rc;
}

err parse_packet_set_flow_resolution( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Data:   [bits U8]  9..16 (9 bit = 1 ms, 16 bit = 74 ms per measurement)
     * Return: [err U8]
     * Applied to every present sensor; measurement is restarted afterwards.
     * Not persisted: the PIC boots at SENSIRION_RESOLUTION_DEFAULT_BITS. */
    
    err rc = ERR_OK;
    err chan_rc;
    uint8_t bits;
    uint8_t chan;
    
    if ( packet_data_size != 1 )
        rc = ERR_PACKET_INVALID;
    else
    {
        bits = packet_data[0];
        if ( ( bits < SENSIRION_RESOLUTION_MIN_BITS ) || ( bits > SENSIRION_RESOLUTION_MAX_BITS ) )
            rc = ERR_SENSIRION_RESOLUTION_INVALID;
    }
    
    if ( rc == ERR_OK )
    {
        /* v3.2: packet handlers run before the ADC state machine in the main
         * loop, so an ADC transaction may still be in flight.  Let it finish
         * (< 0.3 ms) instead of queueing behind it or aborting it. */
        uint16_t wait_start = timer_ms;
        while ( ( adc_task.status == I2C2_MESSAGE_PENDING ) && ( (uint16_t)( timer_ms - wait_start ) <= 3 ) );
        
        for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        {
            if ( !flow_present[chan] )
                continue;
            
            chan_rc = select_flow_mux( chan );
            if ( chan_rc == ERR_OK )
                chan_rc = sensirion_set_resolution( bits );
            if ( chan_rc == ERR_OK )
                chan_rc = sensirion_measurement_start();
            
            /* v3.2: tell the scheduler what state the sensor is in now */
            flow_pending[chan] = ( chan_rc == ERR_OK );
            flow_trig_ms[chan] = timer_ms;
            
            if ( chan_rc != ERR_OK )
                rc = chan_rc;   /* report the failure but keep configuring the others */
        }
        
        if ( rc == ERR_OK )
        {
            flow_resolution_bits = bits;
            flow_apply_resolution_timing();
        }
    }
    
    /* Success reply here; on error the main loop sends the [err] reply. */
    if ( rc == ERR_OK )
        spi_packet_write( packet_type, &rc, 1 );
    
    return rc;
}

err parse_packet_get_flow_resolution( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8][bits U8] */
    
    uint8_t return_buf[ sizeof(err) + sizeof(uint8_t) ];
    
    return_buf[0] = ERR_OK;
    return_buf[1] = flow_resolution_bits;
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    return ERR_OK;
}

err parse_packet_get_fw_version( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* Return: [err U8][major U8][minor U8] */
    
    uint8_t return_buf[ sizeof(err) + 2 ];
    
    return_buf[0] = ERR_OK;
    return_buf[1] = FW_VERSION_MAJOR;
    return_buf[2] = FW_VERSION_MINOR;
    
    spi_packet_write( packet_type, return_buf, sizeof(return_buf) );
    return ERR_OK;
}

err parse_packet_get_flow_batch( uint8_t packet_type, uint8_t *packet_data, uint8_t packet_data_size )
{
    /* v3.2 (v3.3: t_ms widened to U32, 6 bytes/sample, max reply 103 B within the 128 B SPI buffer)
     * Data:   [chan U8][since_seq U16]   since_seq = last sequence number the host already has
     * Return: [err U8][n U8][seq0 U16][scale U16][n x (t_ms U32, flow_raw I16)][crc8 U8]
     *   - seq is the per-channel ok counter (GET_FLOW_STATS) truncated to 16 bit; the k-th
     *     accepted reading has seq k.  Samples are delivered in order from seq0 = since_seq+1.
     *   - err = ERR_OK and n = 0 means nothing new yet.
     *   - err = ERR_FLOW_BATCH_GAP: since_seq is outside the ring (host too slow, PIC reset,
     *     or first request); delivery restarts from the oldest sample kept, so the host sees
     *     the hole as seq0 != since_seq+1.  The packet is still a valid data packet.
     *   - crc8 (Sensirion polynomial 0x31) covers all preceding bytes of the data field.
     * Stateless on the PIC: repeating a request returns the same data (idempotent). */
    
    err rc = ERR_OK;
    uint8_t chan;
    uint16_t since_seq;
    uint16_t head_seq;
    uint16_t seq0;
    uint16_t kept;
    int16_t avail;
    uint8_t n;
    uint8_t i;
    /* 6 B/sample on the wire (t_ms U32 + flow_raw I16), independent of struct padding */
    uint8_t return_buf[ 1 + 1 + 2 + 2 + FLOW_BATCH_MAX_SAMPLES * 6 + 1 ];
    uint8_t *ptr = return_buf;
    err status = ERR_OK;
    
    if ( packet_data_size != 3 )
        return ERR_PACKET_INVALID;
    chan = packet_data[0];
    if ( chan >= NUM_PRESSURE_CLTRLS )
        return ERR_PACKET_INVALID;
    since_seq = (uint16_t)packet_data[1] | ( (uint16_t)packet_data[2] << 8 );
    
    head_seq = (uint16_t)flow_stats_ok[chan];
    kept = ( flow_stats_ok[chan] < FLOW_RING_SIZE ) ? (uint16_t)flow_stats_ok[chan] : FLOW_RING_SIZE;
    avail = (int16_t)( head_seq - since_seq );
    
    if ( ( avail < 0 ) || ( avail > (int16_t)kept ) )
    {
        /* Outside what we still hold: resynchronise from the oldest kept sample. */
        status = ERR_FLOW_BATCH_GAP;
        avail = (int16_t)kept;
    }
    seq0 = (uint16_t)( head_seq - avail + 1 );
    n = ( avail > FLOW_BATCH_MAX_SAMPLES ) ? FLOW_BATCH_MAX_SAMPLES : (uint8_t)avail;
    
    *ptr++ = status;
    *ptr++ = n;
    COPY_16BIT_TO_PTR( ptr, seq0 );                      ptr += 2;
    COPY_16BIT_TO_PTR( ptr, flow_scales_ul_min[chan] );  ptr += 2;
    for ( i = 0; i < n; i++ )
    {
        flow_sample_t *smp = &flow_ring[chan][ (uint16_t)( seq0 + i ) & FLOW_RING_MASK ];
        COPY_32BIT_TO_PTR( ptr, smp->t_ms );     ptr += 4;
        COPY_16BIT_TO_PTR( ptr, smp->flow_raw ); ptr += 2;
    }
    *ptr = sensirion_crc8( return_buf, (uint8_t)( ptr - return_buf ) );
    ptr++;
    
    spi_packet_write( packet_type, return_buf, (uint8_t)( ptr - return_buf ) );
    
    return rc;
}

void init( void )
{
    uint8_t chan;
    
    /* Comms */
    slave_select = 1;
    
    /* System Init */
    eeprom_okay = false;
    adc_okay = false;
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        ctrl_modes[chan] = CTRL_MODE_ZERO;
    
    /* ADC Init */
    adc_state = ADC_STATE_START;
    adc_chan = 0;
    adc_time = 0;
    timer_ms = 0;
    
    /* Pressure Control Init */
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        pressure_ctrl_state[chan] = PRESSURE_CTRL_STATE_UNCONFIGURED;
    memset( (void *)pressure_mbar_shl_output, 0, sizeof(pressure_mbar_shl_output) );
    memset( (void *)pressure_mbar_shl_target, 0, sizeof(pressure_mbar_shl_target) );
    memset( (void *)pressure_mbar_shl_actual, 0, sizeof(pressure_mbar_shl_actual) );
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        pressure_ctrl_state[chan] = PRESSURE_CTRL_STATE_READY;
    
    /* Flow Control Init */
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        flow_ctrl_state[chan] = FLOW_CTRL_STATE_UNCONFIGURED;
        fpid_p[chan] = FPID_DEFAULT_P;
        fpid_i[chan] = FPID_DEFAULT_I;
        fpid_d[chan] = FPID_DEFAULT_D;
    }
    memset( (void *)flow_raw_target, 0, sizeof(flow_raw_target) );
    memset( (void *)flow_raw_actual, 0, sizeof(flow_raw_actual) );
    memset( (void *)fpid_integrated, 0, sizeof(fpid_integrated) );
    memset( (void *)fpid_diff, 0, sizeof(fpid_diff) );
    memset( (void *)fpid_error_prev, 0, sizeof(fpid_error_prev) );
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
        flow_ctrl_state[chan] = FLOW_CTRL_STATE_READY;
}

void adc_rdy_isr( void )
{
    /*
    switch ( adc_state )
    {
        case ADC_STATE_INIT:
            ads1115_start_single( adc_i2c_addr, 0, DATARATE_128SPS, FSR_6_144 );
            adc_state = ADC_STATE_SAMPLE;
            break;
        case ADC_STATE_SAMPLE:
            pressure_mbar_shl_actual[0] = PRESSURE_ADC_TO_MBARSHL( ads1115_get_result( adc_i2c_addr ) );
            ads1115_start_single( adc_i2c_addr, 0, DATARATE_128SPS, FSR_6_144 );
            break;
        default:;
    }
    */
    adc_go = 1;
}

void __attribute__ ((weak)) timer_isr(void)
{
//    PORTAbits.RA1 = ( ( !PORTAbits.RA1 ) && OSCCONbits.LOCK ) ? 1 : 0;
//    PORTAbits.RA1 = !PORTAbits.RA1;
//    PORTAbits.RA1 = OSCCONbits.LOCK ? 1 : 0;
//    PORTAbits.RA1 = OSCCONbits.OSWEN;
    timer_ms++;
    if ( timer_ms == 0 )
        timer_ms_hi++;
}

/* v3.3: 32-bit millisecond time. Read hi/lo with a retry so a timer tick between
 * the two reads (lo wrapping, hi advancing) cannot produce a torn value. */
static uint32_t timer_now32( void )
{
    uint16_t hi, lo;

    do
    {
        hi = timer_ms_hi;
        lo = timer_ms;
    } while ( hi != timer_ms_hi );

    return ( (uint32_t)hi << 16 ) | lo;
}

void storage_save_defaults()
{
    err rc;
    uint8_t chan;
    uint16_t pid_consts[3] = {FPID_DEFAULT_P, FPID_DEFAULT_I, FPID_DEFAULT_D};
    
    /* Store EEPROM version */
    rc = store_save_eeprom_ver( EEPROM_VER );
    
    /* Store default Flow PID Constants */
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        if ( rc == ERR_OK )
           rc = store_save_fpid_consts( chan, pid_consts );
    }
    
    printf( "Save Defaults %s\n", (rc==ERR_OK) ? "OK" : "FAIL" );
}

void storage_startup()
{
    uint8_t eeprom_ver;
    uint8_t chan;
    uint16_t pid_consts[NUM_PRESSURE_CLTRLS][3];

    store_load_eeprom_ver( &eeprom_ver );
    printf( "EEPROM Version %hu\n", eeprom_ver );
    
    store_load_fpid_consts( (uint16_t *)pid_consts );
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        fpid_p[chan] = pid_consts[chan][0];
        fpid_i[chan] = pid_consts[chan][1];
        fpid_d[chan] = pid_consts[chan][2];
        printf( "Flow %hu PID Constants P %u I %u D %u\n", chan, fpid_p[chan], fpid_i[chan], fpid_d[chan] );
    }
    
    if ( eeprom_ver == EEPROM_BLANK_U8 )
    {
        /* Blank EEPROM */
        printf( "Saving Defaults\n" );
        storage_save_defaults();
    }
    
    printf( "\n" );
}

err select_flow_mux( uint8_t chan )
{
    /* v3.2: route the I2C mux to the sensor of `chan`, skipping the transaction
     * when it is already routed there.  Any failure forgets the cached state. */
    err rc = ERR_OK;
    
    if ( mux_selected != (int8_t)flow_map[chan] )
    {
        rc = pca9544a_write( pca9544a_i2c_addr, 1, flow_map[chan] );
        mux_selected = ( rc == ERR_OK ) ? (int8_t)flow_map[chan] : -1;
    }
    return rc;
}

void flow_apply_resolution_timing( void )
{
    flow_tmin_ms = sensirion_processing_time_min_ms( flow_resolution_bits );
}

void poll_flows( void )
{
    /* v3.2: free-running measurement scheduler, called from the main loop on
     * every iteration in which the ADC state machine has no I2C transaction in
     * flight (the MCC queue holds a single transaction).
     *
     * Per present+active channel (Sensirion I2C guide 4.1/4.5, hold-master off):
     *   - no measurement pending  -> trigger one (0xF1 + read header), note the time
     *   - pending and >= t_min elapsed -> read; the sensor NACKs cheaply if still busy
     *   - accepted reading -> store in the ring, advance counters, trigger the next
     *     measurement immediately (continuous coverage, no blind spots)
     * Error handling keeps the previous value (as before) and never blocks the loop
     * beyond one I2C transaction. */
    err rc;
    uint8_t chan;
    int16_t flow;
    bool new_data = false;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        if ( !( active_sensor_mask & ( 1 << chan ) ) || !flow_present[chan] )
            continue;
        
        if ( !flow_pending[chan] )
        {
            rc = select_flow_mux( chan );
            if ( rc == ERR_OK )
                rc = sensirion_measurement_start();
            if ( ( rc == ERR_OK ) || ( rc == ERR_SENSIRION_NOT_READY ) )
            {
                /* NOT_READY here = sensor already measuring (e.g. after a CRC
                 * failure the read header itself restarted it): same outcome. */
                flow_pending[chan] = true;
                flow_trig_ms[chan] = timer_ms;
            }
            else
            {
                flow_stats_i2c_err[chan]++;
                mux_selected = -1;
            }
            continue;
        }
        
        if ( (uint16_t)( timer_ms - flow_trig_ms[chan] ) < flow_tmin_ms )
            continue;
        /* At most one read attempt per millisecond: a NACK costs ~50 us of bus
         * time, polling every loop iteration would add ~20 of them per sample. */
        if ( timer_ms == flow_poll_ms[chan] )
            continue;
        flow_poll_ms[chan] = timer_ms;
        
        rc = select_flow_mux( chan );
        if ( rc == ERR_OK )
            rc = sensirion_measurement_read( &flow );
        
        if ( rc == ERR_OK )
        {
            uint16_t seq;
            
            flow_raw_actual[chan] = flow;
            flow_stats_ok[chan]++;
            if ( ( flow >= FLOW_SATURATION_COUNTS ) || ( flow <= -FLOW_SATURATION_COUNTS ) )
                flow_stats_saturated[chan]++;
            seq = (uint16_t)flow_stats_ok[chan];
            flow_ring[chan][seq & FLOW_RING_MASK].t_ms = timer_now32();
            flow_ring[chan][seq & FLOW_RING_MASK].flow_raw = flow;
            new_data = true;
            
            /* Trigger the next measurement right away (datasheet recommendation). */
            rc = sensirion_measurement_start();
            flow_pending[chan] = ( ( rc == ERR_OK ) || ( rc == ERR_SENSIRION_NOT_READY ) );
            flow_trig_ms[chan] = timer_ms;
            if ( !flow_pending[chan] )
            {
                flow_stats_i2c_err[chan]++;
                mux_selected = -1;
            }
        }
        else if ( rc == ERR_SENSIRION_NOT_READY )
        {
            flow_stats_not_ready[chan]++;
            /* Give up waiting if the measurement should long have finished
             * (sensor reset / power glitch): re-trigger on the next pass. */
            if ( (uint16_t)( timer_ms - flow_trig_ms[chan] ) > (uint16_t)( 2 * flow_tmin_ms + 20 ) )
                flow_pending[chan] = false;
        }
        else if ( rc == ERR_SENSIRION_CRC_FAIL )
        {
            flow_stats_crc_err[chan]++;
            /* Re-trigger explicitly on the next pass (0xF1 + read header):
             * whether or not the failed read header restarted the sensor,
             * start() answers OK or NOT_READY and the scheduler stays in sync. */
            flow_pending[chan] = false;
        }
        else
        {
            flow_stats_i2c_err[chan]++;
            mux_selected = -1;
            flow_pending[chan] = false;
        }
    }
    
    /* v3.1 rule: the refresh counter is a measurement sequence number. */
    if ( new_data )
        flow_refresh_counter++;
}

void update_outputs( void )
{
    uint8_t chan;
    int32_t diff;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        if ( ( flow_ctrl_state[chan] == FLOW_CTRL_STATE_RUNNING ) && flow_present[chan] )
        {
            /* Flow control loop */
            
            int32_t error;
            int32_t output;
            int32_t output_change;
            int32_t fpid_p_term;
            int32_t fpid_d_term;
            
            error = flow_raw_target[chan] - flow_raw_actual[chan];
            fpid_p_term = constrain_i32( ( error * fpid_p[chan] ), -(int32_t)FPID_P_TERM_LIMIT, FPID_P_TERM_LIMIT );
            fpid_integrated[chan] += constrain_i32( error * fpid_i[chan], -(int32_t)FPID_I_CHANGE_LIMIT, FPID_I_CHANGE_LIMIT );
            fpid_integrated[chan] = constrain_i32( fpid_integrated[chan], -fpid_windup_limit << FPID_I_SHIFT, fpid_windup_limit << FPID_I_SHIFT );
            diff = ( constrain_i32( error - fpid_error_prev[chan], INT16_MIN, INT16_MAX ) * fpid_d[chan] );
            fpid_diff[chan] = ( ( fpid_diff[chan] * FPID_DIFF_FILT_MUL ) + diff ) >> FPID_DIFF_FILT_SHIFT;
            fpid_d_term = constrain_i32( fpid_diff[chan], -(int32_t)FPID_TERM_MAX, FPID_TERM_MAX );
            fpid_error_prev[chan] = error;
            
            output = ( fpid_p_term ) +
                     ( fpid_integrated[chan] ) +
                     ( fpid_d_term );
            
            output_change = constrain_i32( output >> FPID_I_SHIFT, -(int32_t)FPID_OUTPUT_SLEW_LIMIT, FPID_OUTPUT_SLEW_LIMIT );
            output = output_change + pressure_mbar_shl_output[chan];
            output = constrain_i32( output, 0, (int32_t)PRESSURE_CTLR_MBAR << PRESSURE_SHL );
            pressure_mbar_shl_output[chan] = (uint16_t)output;
            
           printf( "Chan %hu, error %6li, output %5li, %6li, %6li, %6li, change %5li\n", chan, error, output, fpid_p_term >> FPID_I_SHIFT, fpid_integrated[chan] >> FPID_I_SHIFT, fpid_d_term >> FPID_I_SHIFT, output_change );
        }
        else if ( ( pressure_ctrl_state[chan] == PRESSURE_CTRL_STATE_RUNNING ) && true )
        {
            /* Pressure control loop */
            
        }
        else if ( ctrl_modes[chan] == CTRL_MODE_PRESSURE_OPEN_LOOP )
        {
            /* Pressure open loop */
            
            pressure_mbar_shl_output[chan] = pressure_mbar_shl_target[chan];
        }
        else if ( ctrl_modes[chan] == CTRL_MODE_ZERO )
        {
            /* Pressure zero */
            
            pressure_mbar_shl_output[chan] = 0;
        }
    }
        
    set_pressures();
}

void startup_test( void )
{
    bool all_okay = true;
    
    eeprom_okay = eeprom_comms_check();
    all_okay &= eeprom_okay;
    printf( "EEPROM %s\n", eeprom_okay ? OK_STR : FAIL_STR );
    
    adc_okay = ( ads1115_set_ready_pin( adc_i2c_addr ) == ERR_OK );
    all_okay &= adc_okay;
    printf( "ADC %s\n", adc_okay ? OK_STR : FAIL_STR );
    
    mux_okay = ( pca9544a_write( pca9544a_i2c_addr, 0, 0 ) == ERR_OK );
    all_okay &= mux_okay;
    printf( "I2C MUX %s\n", mux_okay ? OK_STR : FAIL_STR );
    
    printf( "Startup test %s\n", all_okay ? OK_STR : FAIL_STR );
    printf( "\n" );
    
    /* If something fails, shut down */
    if ( !all_okay )
    {
        printf( "Shutting down\n" );
        while (1);
    }
    else if ( 0 )
    {
        dac_reset();
        dac_ref_internal( 1 );
        dac_write_ldac( DAC_CHAN_A, 1ul * 0xFFFF / 5, 0 );
        dac_write_ldac( DAC_CHAN_B, 2ul * 0xFFFF / 5, 0 );
        dac_write_ldac( DAC_CHAN_C, 3ul * 0xFFFF / 5, 0 );
        dac_write_ldac( DAC_CHAN_D, 4ul * 0xFFFF / 5, 1 );
        while (1);
    }
}

void init_sensirion_lg16( void )
{
    err rc;
    uint8_t chan;
//    char sensirion_part_num[SENSIRION_PART_NAME_STR_LEN];
    uint16_t adv_user_reg;
    int16_t flow;
    uint16_t flow_scale;
    
    for ( chan=0; chan<NUM_PRESSURE_CLTRLS; chan++ )
    {
        rc = pca9544a_write( pca9544a_i2c_addr, 1, flow_map[chan] );
        
        if ( rc == ERR_OK )
            sensirion_measurement_read( &flow );   // In case we got stuck in a read
        if ( rc == ERR_OK )
            rc = sensirion_reset( true );
        if ( rc == ERR_OK )
            rc = sensirion_read_reg( SENSIRION_REG_ADV_USER_READ, &adv_user_reg );
        if ( rc == ERR_OK )
        {
            adv_user_reg &= ~0x02;  // Disable hold-master
            /* v3: pin the resolution explicitly (default 16 bit = factory value,
             * so the register written at boot is the same as before). */
            adv_user_reg &= ~SENSIRION_ADV_USER_RESOLUTION_MASK;
            adv_user_reg |= (uint16_t)( flow_resolution_bits - SENSIRION_RESOLUTION_MIN_BITS ) << SENSIRION_ADV_USER_RESOLUTION_SHIFT;
        }
        if ( rc == ERR_OK )
            rc = sensirion_write_reg( SENSIRION_REG_ADV_USER_WRITE, adv_user_reg );
        if ( rc == ERR_OK )
            rc = sensirion_read_scale( SENSIRION_EEPROM_ADDR_SCALE0, &flow_scale );
        else
            flow_scale = 1;
        if ( rc == ERR_OK )
            sensirion_measurement_start();
        
        /* v3.2: scheduler state after init */
        flow_pending[chan] = ( rc == ERR_OK );
        flow_trig_ms[chan] = timer_ms;
        
        flow_scales_ul_min[chan] = flow_scale;
        flow_present[chan] = ( rc == ERR_OK ) ? true : false;
        
        /* We can't start flow loop without flow scaling units */
        if ( !flow_present[chan] )
            flow_ctrl_state[chan] = FLOW_CTRL_STATE_ERROR;
        
        printf( "Sensirion LG16 channel %hu %s, scale %u\n", chan+1, (rc==ERR_OK)?OK_STR:FAIL_STR, flow_scale );
    }
    
    printf( "\n" );
    
    mux_selected = -1;              /* v3.2: mux was driven directly above */
    flow_apply_resolution_timing();
    
    /* Allow enough time for first measurements. */
    __delay_ms( 100 );
    
    /*
    rc = pca9544a_write( pca9544a_i2c_addr, 1, flow_map[0] );
    rc = sensirion_read_part_name( sensirion_part_num );
    printf( "Sensirion Read ID RC: %hu\n", rc );
    printf( "Sensirion Part Name: %s\n", sensirion_part_num );
    rc = sensirion_read_reg( SENSIRION_REG_ADV_USER_READ, &adv_user_reg );
    printf( "Sensirion Read Adv User Reg RC: %u\n", rc );
    printf( "Sensirion Adv User Reg: %u\n", adv_user_reg );
    adv_user_reg &= ~0x02;          // Disable hold-master
    rc = sensirion_write_reg( SENSIRION_REG_ADV_USER_WRITE, adv_user_reg );
    printf( "Sensirion Write Adv User Reg RC: %u, %u\n", rc, adv_user_reg );
    rc = sensirion_read_reg( SENSIRION_REG_ADV_USER_READ, &adv_user_reg );
    printf( "Sensirion Read Adv User Reg RC: %u\n", rc );
    printf( "Sensirion Adv User Reg: %u\n", adv_user_reg );
    
    rc = sensirion_read_scale( SENSIRION_EEPROM_ADDR_SCALE0, &flow_scale );
    printf( "Sensirion Read Scale RC: %u\n", rc );
    printf( "Sensirion Scale: %u\n", flow_scale );
    
    rc = sensirion_measurement_start();
    printf( "Sensirion Measurement Start RC: %hu\n", rc );
    __delay_ms( 100 );
    rc = sensirion_measurement_read( &flow );
    printf( "Sensirion Measurement Read RC: %hu\n", rc );
	printf( "Sensirion Measurement Flow: %i\n", flow );
    */
}

int main(void)
{
    err rc = 0;
    err comms_rc;
    bool adc_i2c_wait;
//    uint8_t ints, enabled, channel;
    
    SYSTEM_Initialize();
    init();
    
    /* Print Header */
    printf( "\033\143" );  // Clear / reset terminal
    __delay_ms( 100 );
    printf( "\r\nStarting...\n\n" );
    
    /* Init Timers */
    TMR1_SetInterruptHandler( &timer_isr );
    
    /* Test Peripherals */
    startup_test();
    
    /* Load Settings from EEPROM */
    storage_startup();
    
    /* Init ADC */
    ads1115_set_ready_pin( adc_i2c_addr );
//    ADC_RDY_SetInterruptHandler( adc_rdy_isr );
    
    /* Init DAC */
    dac_reset();
    dac_ref_internal( 1 );
    set_pressures();
    
    /* Init I2C MUX */
    rc = pca9544a_write( pca9544a_i2c_addr, 0, flow_map[0] );
    /*
    rc = pca9544a_write( pca9544a_i2c_addr, 1, flow_map[0] );
    printf( "I2C Mux Write RC: %hu\n", rc );
    rc = pca9544a_read( pca9544a_i2c_addr, &ints, &enabled, &channel );
    printf( "I2C Mux Read RC: %hu\n", rc );
    printf( "I2C Mux ints %hu, enabled %hu, channel %hu\n", ints, enabled, channel );
    */
    
    /* Init Sensirion flow sensor */
    init_sensirion_lg16();
    
    /* Test Code */
//    read_flows();
//    flow_ctrl_start( 0, (int16_t)( (int32_t)10 * flow_scales_ul_min[1] / 60 ) );    // in ul/hr
    
//    while ( 1 );
    
    /* Init SPI */
    spi_init();
    spi_packet_init( &spi_packet, (uint16_t *)&timer_ms, 300 );
    
    __delay_ms( 100 );

    adc_time = timer_ms;
    adc_i2c_wait = 0;
    
    while (1)
    {
        // MODIFIED: SPI processing moved here to handle packets every iteration
        comms_rc = spi_packet_read( &spi_packet, &packet_type, (uint8_t *)&packet_data, &packet_data_size, SPI_PACKET_BUF_SIZE );
        
        if ( ( comms_rc == ERR_OK ) && ( packet_type != 0 ) )
        {
            rc = ERR_OK;
            
            // MODIFIED: Commented out printf to reduce SPI processing overhead
            // printf( "Packet received: Cmd %hu\n", packet_type );
            spi_clear_write();
            
            switch ( packet_type )
            {
                case 0:
                {
                    /* No or invalid packet */
                    rc = ERR_PACKET_INVALID;
                    break;
                }
                case PACKET_TYPE_GET_ID:
                    rc = parse_packet_get_id( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_PRESSURE_TARGET:
                    rc = parse_packet_set_pressure_target( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_PRESSURE_TARGET:
                    rc = parse_packet_get_pressure_target( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_PRESSURE_ACTUAL:
                    rc = parse_packet_get_pressure_actual( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_FLOW_TARGET:
                    rc = parse_packet_set_flow_target( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FLOW_TARGET:
                    rc = parse_packet_get_flow_target( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FLOW_ACTUAL:
                    rc = parse_packet_get_flow_actual( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_CONTROL_MODE:
                    rc = parse_packet_set_control_mode( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_CONTROL_MODE:
                    rc = parse_packet_get_control_mode( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_FPID_CONSTS:
                    rc = parse_packet_set_fpid_consts( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FPID_CONSTS:
                    rc = parse_packet_get_fpid_consts( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_ACTIVE_SENSORS:
                    rc = parse_packet_set_active_sensors( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_ACTIVE_SENSORS:
                    rc = parse_packet_get_active_sensors( packet_type, packet_data, packet_data_size );
                    break;
                /* v3 */
                case PACKET_TYPE_GET_FLOW_STATS:
                    rc = parse_packet_get_flow_stats( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_SET_FLOW_RESOLUTION:
                    rc = parse_packet_set_flow_resolution( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FLOW_RESOLUTION:
                    rc = parse_packet_get_flow_resolution( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FW_VERSION:
                    rc = parse_packet_get_fw_version( packet_type, packet_data, packet_data_size );
                    break;
                case PACKET_TYPE_GET_FLOW_BATCH:
                    rc = parse_packet_get_flow_batch( packet_type, packet_data, packet_data_size );
                    break;
                default:
                    rc = ERR_PACKET_INVALID;
            }
            
            if ( rc != ERR_OK )
                spi_packet_write( packet_type, &rc, 1 );
        }
        else if ( ( spi_write_bytes_written() > 0 ) && spi_packet_timeout( &spi_packet ) )
        {
            spi_clear_write();
            // MODIFIED: Commented out printf to reduce timeout handling overhead
            // printf( "Cleared\n" );
        }
        else if ( SS1_GetValue() != slave_select )
        {
            /* If slave select dropped, clear SPI interface */
            
            slave_select = !slave_select;
            
            if ( slave_select == 1 )
            {
                spi_packet_clear( &spi_packet );
                spi_clear_write();
            }
        }
        
        if ( I2C2_Aborted() )
        {
            adc_state = ADC_STATE_WAIT;
            adc_i2c_wait = 0;
            mux_selected = -1;      /* v3.2: peripheral was re-initialised */
        }
        
        /* v3.2: sensor scheduler runs whenever the ADC has no I2C transaction
         * in flight, so the two never interleave on the single-entry queue. */
        if ( !adc_i2c_wait )
            poll_flows();
        
        if ( adc_i2c_wait )
        {
            int8_t adc_rc;
            uint16_t adc_value;
            int8_t channel;
            
            /* See what's happening on ADC I2C */
            adc_rc = ads1115_read_adc_return( &adc_value, &channel, &adc_task );

            switch ( adc_rc )
            {
                case 0:
                {
                    /* Still waiting */
                    break;
                }
                case 1:
                {
                    /* I2C success */
                    adc_i2c_wait = 0;
                    
                    if ( channel >= 0 )
                    {
//                        printf( "Pressure: %u\n", adc_value );
                        /* Value returned */
                        pressure_mbar_shl_actual[adc_map[channel]] = PRESSURE_ADC_TO_MBARSHL( adc_value );
                        /*
                        printf( "State %u, Channel %hi, Pressures: %i %i %i %i\n",
                                adc_state, channel,
                                pressure_mbar_shl_actual[0],
                                pressure_mbar_shl_actual[1],
                                pressure_mbar_shl_actual[2],
                                pressure_mbar_shl_actual[3] );
                        */
                    }
                    
                    break;
                }
                case -1:
                {
                    /* Timeout */
                    adc_state = ADC_STATE_WAIT;
                    adc_i2c_wait = 0;
                    break;
                }
                default:
                    ;
            }
            
//            printf( "adc_state=%hu, adc_rc=%hi\n", (uint8_t)adc_state, adc_rc );
            /* When we have read all ADCs (or error), update outputs */
            if ( ( adc_state == ADC_STATE_WAIT ) && ( adc_rc != 0 ) )
            {
                /* v3.2: flow readings are no longer taken here (see poll_flows);
                 * the control loop uses the latest accepted value. */
                update_outputs();
            }
        }
        else switch ( adc_state )
        {
            case ADC_STATE_START:
            {
                // MODIFIED: Find first active ADC channel to start scanning
                adc_chan = 0;
                while ( adc_chan < NUM_PRESSURE_CLTRLS && !(active_sensor_mask & (1 << adc_chan)) )
                {
                    adc_chan++;
                }
                
                if ( adc_chan >= NUM_PRESSURE_CLTRLS )
                {
                    // No active sensors - skip to wait state
                    adc_state = ADC_STATE_WAIT;
                }
                else
                {
                    ads1115_read_adc_start( adc_i2c_addr, -1, adc_chan, adc_datarate, adc_gain, &adc_task );
                    adc_i2c_wait = 1;
                    adc_state = ADC_STATE_SAMPLE;
                }
                break;
            }
            case ADC_STATE_SAMPLE:
            {
                if ( !ADC_RDY_GetValue() )
                {
                    uint8_t read_chan = adc_chan;
                    
                    /* Read back ADC and start next channel */
                    if ( read_chan >= ADC_CHAN_MAX )
                    {
                        /* Read last channel */
                        ads1115_read_adc_start( adc_i2c_addr, read_chan, -1, adc_datarate, adc_gain, &adc_task );
                        adc_state = ADC_STATE_WAIT;
                    }
                    else
                    {
                        /* Find next active channel */
                        uint8_t next_chan = adc_chan + 1;
                        while ( next_chan < NUM_PRESSURE_CLTRLS && !(active_sensor_mask & (1 << next_chan)) )
                        {
                            next_chan++;
                        }
                        
                        if ( next_chan >= NUM_PRESSURE_CLTRLS )
                        {
                            /* No more active channels - read last and go to wait */
                            ads1115_read_adc_start( adc_i2c_addr, read_chan, -1, adc_datarate, adc_gain, &adc_task );
                            adc_state = ADC_STATE_WAIT;
                        }
                        else
                        {
                            /* Read current and start next active channel */
                            adc_chan = next_chan;
                            ads1115_read_adc_start( adc_i2c_addr, read_chan, adc_chan, adc_datarate, adc_gain, &adc_task );
                        }
                    }
                    
                    adc_i2c_wait = 1;
                }
                /* ** Put below back in */
                /*
                else if ( ( timer_ms - adc_time ) > ADC_PERIOD_MS )
                {
                    adc_state = ADC_STATE_START;
                    adc_time += ADC_PERIOD_MS;
                }*/
                
                break;
            }
            case ADC_STATE_WAIT:
            {
//                printf( "State: %hu, time=%u, on=%hu\n", (uint8_t)adc_state, TMR1, T1CONbits.TON );
        
                while ( ( timer_ms - adc_time ) > ADC_PERIOD_MS )
                {
                    adc_state = ADC_STATE_START;
                    adc_time += ADC_PERIOD_MS;
                }
                break;
            }
            default:
                adc_state = ADC_STATE_START;
        }
    }
    
    return 1; 
}
