/*
 * Advanced User Register:
    adv_user_reg &= ~0x02;          // Disable hold-master
    adv_user_reg &= ~0x0E00;        // Clear resolution
    adv_user_reg |= 0b111 << 9;     // Add resolution
    adv_user_reg &= ~0x1000;        // Clear heater-stay-on
    adv_user_reg |= 0x1000;         // Set heater-stay-on
*/

#include "mcc_generated_files/mcc.h"
#include "common.h"
#include <libpic30.h>
#include <stdio.h>
#include "sensirion_lg16.h"

#define I2C_ADDR            0x40
#define I2C_TIMEOUT_MS      8

/* Macros */
#define COPY_16BIT_TO_PTR_REV(ptr,val)  {*ptr=*((uint8_t *)&val+1); *(ptr+1)=*(uint8_t *)&val;}

/* Static Prototypes */
static err i2c_wait_for_reply( volatile I2C2_MESSAGE_STATUS *status, uint16_t timeout_ms );

/* Extern Functions */

extern err sensirion_read_eeprom( uint16_t addr, uint8_t bytes, uint8_t *reg_data )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[2];
    uint8_t cmd[] = {0xFA, addr>>8, addr&0xFF};
    
    I2C2_MasterWriteTRBBuild( &trBlocks[0], (void *)cmd, 3, I2C_ADDR );
    I2C2_MasterReadTRBBuild( &trBlocks[1], (void *)reg_data, bytes, I2C_ADDR );
    I2C2_MasterTRBInsert( 2, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    return rc;
}

extern err sensirion_read_reg( uint8_t reg, uint16_t *reg_data )
{
    // Default adv user reg value = 32406
    
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[2];
    uint8_t cmd = reg;
    uint16_t buf;
    
    I2C2_MasterWriteTRBBuild( &trBlocks[0], (void *)&cmd, 1, I2C_ADDR );
    I2C2_MasterReadTRBBuild( &trBlocks[1], (void *)&buf, 2, I2C_ADDR );
    I2C2_MasterTRBInsert( 2, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    if ( rc != ERR_OK )
    {
        *reg_data = 0;
    }
    else
    {
        COPY_16BIT_TO_PTR_REV( (uint8_t *)reg_data, buf );
    }
    
    return rc;
}

extern err sensirion_write_reg( uint8_t reg, uint16_t reg_data )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[1];
    uint8_t writeBuffer[3];
    
    writeBuffer[0] = reg;
    writeBuffer[1] = reg_data >> 8;
    writeBuffer[2] = reg_data & 0xFF;
    I2C2_MasterWriteTRBBuild( &trBlocks[0], (void *)writeBuffer, 3, I2C_ADDR );
    I2C2_MasterTRBInsert( 1, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    return rc;
}

extern err sensirion_reset( bool wait )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    uint8_t cmd = 0xFE;
    
    I2C2_MasterWrite( &cmd, 1, I2C_ADDR, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    if ( ( rc == ERR_OK ) && wait )
        __delay_ms( 3 );    // Boot time to comms
    
    return rc;
}

extern err sensirion_read_part_name( char *part_name )
{
    err rc;
    uint8_t buf[SENSIRION_PART_NAME_LEN_WORDS*3];
    uint8_t i;
    
    rc = sensirion_read_eeprom( SENSIRION_EEPROM_ADDR_PART_NAME, SENSIRION_PART_NAME_LEN_BYTES, buf );
    
    if ( rc != ERR_OK )
    {
        *part_name = 0;
    }
    else
    {
        for ( i=0; i<SENSIRION_PART_NAME_LEN_WORDS; i++ )
        {
            char *buf_ptr = (char *)&buf[i*3];
            char *product_num_ptr = &part_name[i<<1];
            *product_num_ptr++ = *buf_ptr++;
            *product_num_ptr = *buf_ptr;
        }
        
        part_name[SENSIRION_PART_NAME_LEN_BYTES] = 0;
    }
    
    return rc;
}

extern err sensirion_read_scale( uint16_t addr, uint16_t *scale )
{
    err rc;
    uint16_t buf;
    
    rc = sensirion_read_eeprom( addr, 2, (void *)&buf );
    
    if ( rc == ERR_OK )
        COPY_16BIT_TO_PTR_REV( (uint8_t *)scale, buf );
    
    return rc;
}

extern err sensirion_measurement_start( void )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[2];
    uint8_t cmd = 0xF1;
    uint8_t dummy;
    
    I2C2_MasterWriteTRBBuild( &trBlocks[0], (void *)&cmd, 1, I2C_ADDR );
    I2C2_MasterReadTRBBuild( &trBlocks[1], &dummy, 1, I2C_ADDR );
    I2C2_MasterTRBInsert( 2, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    /* v3.2: a present sensor always ACKs the write header (I2C guide 4.5) and
     * NACKs the 0xF1 byte while measuring (DATA_NO_ACK = NOT_READY).  An
     * address NACK therefore means no sensor on this mux channel. */
    if ( status == I2C2_MESSAGE_ADDRESS_NO_ACK )
        rc = ERR_SENSIRION_COMMS_FAIL;
    
	return rc;
}

extern err sensirion_measurement_read( int16_t *flow )
{
    /* v3: read the 3-byte frame [MSB][LSB][CRC-8] and reject corrupted
     * readings.  The previous 2-byte read accepted any bytes that arrived
     * without an I2C error, so a corrupted transfer became a valid flow. */
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[1];
    uint8_t buf[3];

    I2C2_MasterReadTRBBuild( &trBlocks[0], (void *)buf, 3, I2C_ADDR );
    I2C2_MasterTRBInsert( 1, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    if ( ( rc == ERR_OK ) && ( sensirion_crc8( buf, 2 ) != buf[2] ) )
        rc = ERR_SENSIRION_CRC_FAIL;
    
    if ( rc != ERR_OK )
    {
        *flow = 0;
    }
    else
    {
        *flow = (int16_t)( ( (uint16_t)buf[0] << 8 ) | buf[1] );
    }
    
    return rc;
}

extern err sensirion_set_resolution( uint8_t bits )
{
    /* v3: Advanced User Register bits 11:9 select the measurement
     * resolution: 0b000 = 9 bit (1 ms) ... 0b111 = 16 bit (74 ms).
     * Volatile setting (register only, never EEPROM): lost on sensor reset.
     * Caller must have selected the sensor on the I2C mux and must restart
     * the measurement afterwards.
     * With hold-master disabled the sensor NACKs every command while a
     * measurement is pending, so the pending result is drained first
     * (worst case 16 bit = 73 ms max; v3.2 polls cheaply until done or
     * SENSIRION_DRAIN_TIMEOUT_MS). */
    err rc;
    uint16_t adv_user_reg;
    uint16_t readback;
    int16_t flow;
    uint16_t time;
    uint16_t last;
    
    if ( ( bits < SENSIRION_RESOLUTION_MIN_BITS ) || ( bits > SENSIRION_RESOLUTION_MAX_BITS ) )
        return ERR_SENSIRION_RESOLUTION_INVALID;
    
    /* Drain: one read attempt per millisecond until a valid frame arrives.
     * If the sensor was idle the first read header starts a measurement and
     * returns no valid frame (CRC_FAIL): keep polling in that case too. */
    time = timer_ms;
    last = timer_ms;
    do
    {
        while ( timer_ms == last );
        last = timer_ms;
        rc = sensirion_measurement_read( &flow );
    }
    while ( ( ( rc == ERR_SENSIRION_NOT_READY ) || ( rc == ERR_SENSIRION_CRC_FAIL ) )
            && ( ( timer_ms - time ) <= SENSIRION_DRAIN_TIMEOUT_MS ) );
    if ( rc != ERR_OK )
        return rc;
    
    rc = sensirion_read_reg( SENSIRION_REG_ADV_USER_READ, &adv_user_reg );
    if ( rc == ERR_OK )
    {
        adv_user_reg &= ~SENSIRION_ADV_USER_RESOLUTION_MASK;
        adv_user_reg |= (uint16_t)( bits - SENSIRION_RESOLUTION_MIN_BITS ) << SENSIRION_ADV_USER_RESOLUTION_SHIFT;
        rc = sensirion_write_reg( SENSIRION_REG_ADV_USER_WRITE, adv_user_reg );
    }
    if ( rc == ERR_OK )
    {
        /* No master-to-slave checksum: datasheet recommends reading back. */
        rc = sensirion_read_reg( SENSIRION_REG_ADV_USER_READ, &readback );
        if ( ( rc == ERR_OK ) && ( readback != adv_user_reg ) )
            rc = ERR_SENSIRION_COMMS_FAIL;
    }
    
    return rc;
}

extern uint8_t sensirion_crc8( const uint8_t *data, uint8_t len )
{
    /* Sensirion CRC-8: polynomial 0x31 (x^8 + x^5 + x^4 + 1), init 0x00,
     * no reflection, no final XOR. */
    uint8_t crc = 0x00;
    uint8_t i, bit;
    
    for ( i = 0; i < len; i++ )
    {
        crc ^= data[i];
        for ( bit = 0; bit < 8; bit++ )
        {
            if ( crc & 0x80 )
                crc = (uint8_t)( ( crc << 1 ) ^ 0x31 );
            else
                crc = (uint8_t)( crc << 1 );
        }
    }
    
    return crc;
}

extern uint8_t sensirion_processing_time_min_ms( uint8_t bits )
{
    /* v3.2: minimum processing time per resolution, Sensirion I2C guide 4.2
     * (9 bit 0.5 ms ... 16 bit 65.5 ms), floored to whole ms.  The host polls
     * from this moment on; an early poll only costs a cheap NACK. */
    static const uint8_t t_min_ms[] = { 0, 1, 2, 4, 8, 16, 32, 65 };   /* 9..16 bit */
    
    if ( ( bits < SENSIRION_RESOLUTION_MIN_BITS ) || ( bits > SENSIRION_RESOLUTION_MAX_BITS ) )
        return 0;
    return t_min_ms[bits - SENSIRION_RESOLUTION_MIN_BITS];
}

/* Static Functions */

static err i2c_wait_for_reply( volatile I2C2_MESSAGE_STATUS *status, uint16_t timeout_ms )
{
    /* v3.2: return as soon as the driver has finished the transaction, whatever
     * the outcome.  Before v3.2 this spun for the full timeout on a NACK and then
     * called I2C2_Abort(), which re-initialises the peripheral and resets the ADC
     * state machine; with hold-master disabled a NACK is the normal "still
     * measuring" answer (Sensirion I2C guide 4.5), so polling must be cheap.
     * The MCC driver already issues STOP on a NACK; I2C2_Abort() is only needed
     * when the transaction never completes (bus stuck). */
    err rc;
    uint16_t time;
    
    time = timer_ms;
    while ( ( *status == I2C2_MESSAGE_PENDING ) && ( ( timer_ms - time ) <= timeout_ms ) );
    
    switch ( *status )
    {
        case I2C2_MESSAGE_COMPLETE:
            rc = ERR_OK;
            break;
        case I2C2_MESSAGE_ADDRESS_NO_ACK:
        case I2C2_DATA_NO_ACK:
            /* Sensor busy: read header NACKed, or 0xF1 NACKed while measuring. */
            rc = ERR_SENSIRION_NOT_READY;
            break;
        case I2C2_MESSAGE_PENDING:
            /* Timeout: transaction never finished -> bus stuck, reset peripheral. */
            I2C2_Abort();
            rc = ERR_SENSIRION_COMMS_FAIL;
            break;
        default:
            rc = ERR_SENSIRION_COMMS_FAIL;
    }
    
    return rc;
}

