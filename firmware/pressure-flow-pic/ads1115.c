#include "mcc_generated_files/mcc.h"
#include "common.h"
#include "ads1115.h"

#define I2C_TIMEOUT_MS      2

uint8_t conversion_reg = ADS1115_REG_CONVERSION;

/* Static Prototypes */
static err i2c_wait_for_reply( volatile I2C2_MESSAGE_STATUS *status, uint16_t timeout_ms );

/* Extern Functions */

err ads1115_write_register( uint8_t addr, uint8_t reg, uint16_t data )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    uint8_t writeBuffer[3];
    
    writeBuffer[0] = reg;
    writeBuffer[1] = data >> 8;
    writeBuffer[2] = data & 0xFF;
    
    I2C2_MasterWrite( writeBuffer, 3, addr, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
	return rc;
}

err ads1115_read_register( uint8_t addr, uint8_t reg, uint16_t *value )
{
    err rc = ERR_OK;
    uint8_t buf[2];
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[2];

    I2C2_MasterWriteTRBBuild( &trBlocks[0], &reg, 1, addr );
    I2C2_MasterReadTRBBuild( &trBlocks[1], (void *)buf, 2, addr );
    I2C2_MasterTRBInsert( 2, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    rc = i2c_wait_for_reply( &status, I2C_TIMEOUT_MS );
    
    *value = ( ( (uint16_t)(buf[0]) ) << 8 ) | buf[1];
    
    return rc;
}

err ads1115_set_ready_pin( uint8_t addr )
{
    err rc;
    
    rc = ads1115_write_register( addr, ADS1115_REG_HI_THRESH, 0b1000000000000000 );
    if ( rc == ERR_OK )
        rc = ads1115_write_register( addr, ADS1115_REG_LO_THRESH, 0b0000000000000000 );
    
    return rc;
}

void ads1115_read_adc_start( uint8_t addr, int8_t read_channel, int8_t start_channel, ads1115_datarate dr, ads1115_fsr_gain gain, ads1115_task_t *task )
{
    uint16_t adc_config;
    uint8_t trb_count;
    
    /** Clear I2C buffer */
    
    trb_count = 0;
    task->channel = read_channel;
    
    if ( read_channel >= 0 )
    {
        /* Read conversion */
        
        I2C2_MasterWriteTRBBuild( &task->trBlocks[trb_count++], &conversion_reg, 1, addr );
        I2C2_MasterReadTRBBuild( &task->trBlocks[trb_count++], (uint8_t *)task->read_data, 2, addr );
    }
    
    if ( start_channel >= 0 )
    {
        /* Start new conversion */
        
        adc_config =    ADS1115_COMP_QUE_CON1 |
                        ADS1115_COMP_LAT_Latching |
                        ADS1115_COMP_POL_3_ACTIVELOW |
                        ADS1115_COMP_MODE_TRADITIONAL |
                        dr |
                        ADS1115_MODE_SINGLE |
                        gain |
                        ADS1115_OS_SINGLE;

        switch ( start_channel )
        {
            case 0:
                adc_config |= ADS1115_MUX_AIN0_GND;
                break;
            case 1:
                adc_config |= ADS1115_MUX_AIN1_GND;
                break;
            case 2:
                adc_config |= ADS1115_MUX_AIN2_GND;
                break;
            case 3:
                adc_config |= ADS1115_MUX_AIN3_GND;
                break;
            default:
                ;
        }

        if ( start_channel <= 3 )
        {
            task->write_data[0] = ADS1115_REG_CONFIG;
            task->write_data[1] = adc_config >> 8;
            task->write_data[2] = adc_config & 0xFF;

            I2C2_MasterWriteTRBBuild( &task->trBlocks[trb_count++], task->write_data, 3, addr );
        }
    }
    
    I2C2_MasterTRBInsert( trb_count, (I2C2_TRANSACTION_REQUEST_BLOCK *)&task->trBlocks, (I2C2_MESSAGE_STATUS *)&task->status );
    
    /* Record start time */
    task->start_time = timer_ms;
}

int8_t ads1115_read_adc_return( uint16_t *value, int8_t *channel, ads1115_task_t *task )
{
    /* Returns: 0 if still waiting
     *          1 if result available / success
     *          -1 if timeout
     * Channel: <ADC channel number> or -1 if no read was requested
     */
    
    int8_t rc;
    
    if ( task->status == I2C2_MESSAGE_COMPLETE )
    {
        /* Return conversion */
        *value = ( ( (uint16_t)(task->read_data[0]) ) << 8 ) | task->read_data[1];
        *channel = task->channel;
        rc = 1;
    }
    else if ( ( timer_ms - task->start_time ) > I2C_TIMEOUT_MS )
    {
        /* Timeout */
        I2C2_Abort();
        rc = -1;
    }
    else
    {
        /* Still waiting */
        rc = 0;
    }
    
    return rc;
}

err ads1115_start_single( uint8_t addr, uint8_t channel, ads1115_datarate dr, ads1115_fsr_gain gain )
{
    err rc = ERR_OK;
    
	uint16_t adc_config =   ADS1115_COMP_QUE_CON1 |
                            ADS1115_COMP_LAT_Latching |
                            ADS1115_COMP_POL_3_ACTIVELOW |
                            ADS1115_COMP_MODE_TRADITIONAL |
                            dr |
                            ADS1115_MODE_SINGLE |
                            gain |
                            ADS1115_OS_SINGLE;
	
    switch ( channel )
    {
        case 0:
            adc_config |= ADS1115_MUX_AIN0_GND;
            break;
        case 1:
            adc_config |= ADS1115_MUX_AIN1_GND;
            break;
        case 2:
            adc_config |= ADS1115_MUX_AIN2_GND;
            break;
        case 3:
            adc_config |= ADS1115_MUX_AIN3_GND;
            break;
        default:
            rc = ERR_ERROR;
	}
    
    if ( rc == ERR_OK )
        rc = ads1115_write_register( addr, ADS1115_REG_CONFIG, adc_config );
    
    return rc;
}

err ads1115_get_result( uint8_t addr, uint16_t *value )
{
    return ads1115_read_register( addr, ADS1115_REG_CONVERSION, value );
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
        rc = ERR_ADS1115_COMMS_FAIL;
        I2C2_Abort();
    }
    
    return rc;
}

