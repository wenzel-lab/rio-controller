#include "mcc_generated_files/mcc.h"
#include "common.h"
#include "pca9544a.h"

#define I2C_TIMEOUT_MS      2

extern err pca9544a_write( uint8_t addr, uint8_t enabled, uint8_t channel )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    uint8_t writeBuffer[1];
    uint16_t time;
    
    writeBuffer[0] = ( enabled ? 0b100 : 0 ) | ( channel & 0b11 );
//    writeBuffer[0] = 0b100 | ( channel & 0b11 );
//    writeBuffer[0] = 0b100;
    
    I2C2_MasterWrite( writeBuffer, 1, addr, (I2C2_MESSAGE_STATUS *)&status );
    
    time = timer_ms;
    while ( ( status != I2C2_MESSAGE_COMPLETE ) && ( ( timer_ms - time ) <= I2C_TIMEOUT_MS ) );
    if ( status != I2C2_MESSAGE_COMPLETE )
    {
        rc = ERR_PCA9544A_COMMS_FAIL;
        I2C2_Abort();
    }
    
	return rc;
}

extern err pca9544a_read( uint8_t addr, uint8_t *ints, uint8_t *enabled, uint8_t *channel )
{
    err rc = ERR_OK;
    volatile I2C2_MESSAGE_STATUS status;
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[1];
    uint8_t buf[1];
    uint16_t time;

    I2C2_MasterReadTRBBuild( &trBlocks[0], (void *)buf, 1, addr );
    I2C2_MasterTRBInsert( 1, (I2C2_TRANSACTION_REQUEST_BLOCK *)&trBlocks, (I2C2_MESSAGE_STATUS *)&status );
    
    time = timer_ms;
    while ( ( status != I2C2_MESSAGE_COMPLETE ) && ( ( timer_ms - time ) <= I2C_TIMEOUT_MS ) );
    if ( status != I2C2_MESSAGE_COMPLETE )
    {
        rc = ERR_PCA9544A_COMMS_FAIL;
        *ints = 0;
        *enabled = 0;
        *channel = 0;
        I2C2_Abort();
    }
    else
    {
        *ints = *buf >> 4;
        *enabled = ( *buf & 0b00000100 ) >> 2;
        *channel = *buf & 0b00000011;
    }
    
    return rc;
}
