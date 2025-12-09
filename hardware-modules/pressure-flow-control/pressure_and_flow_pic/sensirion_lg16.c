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
    
	return rc;
}

extern err sensirion_measurement_read( int16_t *flow )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[1];
    uint16_t buf;

    I2C2_MasterReadTRBBuild( &trBlocks[0], (void *)&buf, 2, I2C_ADDR );
    I2C2_MasterTRBInsert( 1, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    if ( rc != ERR_OK )
    {
        *flow = 0;
    }
    else
    {
        COPY_16BIT_TO_PTR_REV( (uint8_t *)flow, buf );
    }
    
    return rc;
}

/* Static Functions */

static err i2c_wait_for_reply( volatile I2C2_MESSAGE_STATUS *status, uint16_t timeout_ms )
{
    err rc = ERR_OK;
    uint16_t time;
    
    time = timer_ms;
    while ( ( *status != I2C2_MESSAGE_COMPLETE ) && ( ( timer_ms - time ) <= timeout_ms ) );
    if ( *status != I2C2_MESSAGE_COMPLETE )
    {
        rc = ERR_SENSIRION_COMMS_FAIL;
//        printf( "Status*: %hu\n", *status );
        I2C2_Abort();
    }
    
    return rc;
}

