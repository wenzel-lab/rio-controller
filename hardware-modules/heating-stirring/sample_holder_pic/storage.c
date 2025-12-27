#include <stdio.h>
#include "mcc_generated_files/mcc.h"
#include "common.h"
#include "storage.h"
#include "eeprom.h"

#define GET_STORE_OFFSET( member )  offsetof( store_t, member )

typedef struct __attribute__((packed))
{
    uint16_t pid_p;
    uint16_t pid_i;
    uint16_t pid_d;
} store_pid_t;

typedef struct __attribute__((packed))
{
    uint8_t eeprom_ver;
    store_pid_t pid;
    int16_t hpid_temp_c_scaled;
    int16_t htune_temp_c_scaled;
    uint8_t run_on_start;
    uint8_t heat_power_limit_pc;
} store_t;

/* Static Function Prototypes */

static err store_save_data( uint16_t offset, uint8_t data_len, uint8_t *data );

/* Extern Functions */

extern err store_save_eeprom_ver( uint8_t eeprom_ver )
{
    err rc = ERR_OK;
    uint8_t verify_rc;
    
    eeprom_read_write_bytes( GET_STORE_OFFSET(eeprom_ver), sizeof(eeprom_ver), &eeprom_ver );
    verify_rc = eeprom_verify_bytes( GET_STORE_OFFSET(eeprom_ver), sizeof(eeprom_ver), &eeprom_ver );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}

extern err store_save_pid( uint16_t pid_p, uint16_t pid_i, uint16_t pid_d )
{
    err rc;
    store_pid_t pid;
    uint8_t verify_rc;
    
//    printf( "store size %i, offset %i\n", sizeof(store_t), GET_STORE_OFFSET(pid) );
    
    pid.pid_p = pid_p;
    pid.pid_i = pid_i;
    pid.pid_d = pid_d;
    
    eeprom_read_write_bytes( GET_STORE_OFFSET(pid), sizeof(pid), (uint8_t *)&pid );
    verify_rc = eeprom_verify_bytes( GET_STORE_OFFSET(pid), sizeof(pid), (uint8_t *)&pid );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}

extern err store_save_hpid_temp( int16_t hpid_temp_c_scaled )
{
    err rc = ERR_OK;
    uint8_t verify_rc;
    
    eeprom_read_write_bytes( GET_STORE_OFFSET(hpid_temp_c_scaled), sizeof(hpid_temp_c_scaled), (uint8_t *)&hpid_temp_c_scaled );
    verify_rc = eeprom_verify_bytes( GET_STORE_OFFSET(hpid_temp_c_scaled), sizeof(hpid_temp_c_scaled), (uint8_t *)&hpid_temp_c_scaled );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}

extern err store_save_htune_temp( int16_t htune_temp_c_scaled )
{
    err rc = ERR_OK;
    uint8_t verify_rc;
    
    eeprom_read_write_bytes( GET_STORE_OFFSET(htune_temp_c_scaled), sizeof(htune_temp_c_scaled), (uint8_t *)&htune_temp_c_scaled );
    verify_rc = eeprom_verify_bytes( GET_STORE_OFFSET(htune_temp_c_scaled), sizeof(htune_temp_c_scaled), (uint8_t *)&htune_temp_c_scaled );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}

extern err store_save_run_on_start( uint8_t run_on_start )
{
    err rc = ERR_OK;
    uint8_t verify_rc;
    
    eeprom_read_write_bytes( GET_STORE_OFFSET(run_on_start), sizeof(run_on_start), &run_on_start );
    verify_rc = eeprom_verify_bytes( GET_STORE_OFFSET(run_on_start), sizeof(run_on_start), &run_on_start );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}

extern err store_save_heat_power_limit_pc( uint8_t heat_power_limit_pc )
{
    return store_save_data( GET_STORE_OFFSET(heat_power_limit_pc), sizeof(heat_power_limit_pc), &heat_power_limit_pc );
}

extern err store_load_eeprom_ver( uint8_t *eeprom_ver_p )
{
    err rc = ERR_OK;
    uint8_t eeprom_ver;
    
    eeprom_read_bytes( GET_STORE_OFFSET(eeprom_ver), sizeof(eeprom_ver), (uint8_t *)&eeprom_ver );
    
    *eeprom_ver_p = eeprom_ver;
    
    return rc;
}

extern err store_load_pid( uint16_t *pid_p, uint16_t *pid_i, uint16_t *pid_d )
{
    err rc = ERR_OK;
    store_pid_t pid;
    
    eeprom_read_bytes( GET_STORE_OFFSET(pid), sizeof(pid), (uint8_t *)&pid );
    
    *pid_p = pid.pid_p;
    *pid_i = pid.pid_i;
    *pid_d = pid.pid_d;
    
    return rc;
}

extern err store_load_hpid_temp( int16_t *hpid_temp_c_scaled_p )
{
    err rc = ERR_OK;
    int16_t hpid_temp_c_scaled;
    
    eeprom_read_bytes( GET_STORE_OFFSET(hpid_temp_c_scaled), sizeof(hpid_temp_c_scaled), (uint8_t *)&hpid_temp_c_scaled );
    
    *hpid_temp_c_scaled_p = hpid_temp_c_scaled;
    
    return rc;
}

extern err store_load_htune_temp( int16_t *htune_temp_c_scaled_p )
{
    err rc = ERR_OK;
    int16_t htune_temp_c_scaled;
    
    eeprom_read_bytes( GET_STORE_OFFSET(htune_temp_c_scaled), sizeof(htune_temp_c_scaled), (uint8_t *)&htune_temp_c_scaled );
    
    *htune_temp_c_scaled_p = htune_temp_c_scaled;
    
    return rc;
}

extern err store_load_run_on_start( uint8_t *run_on_start_p )
{
    err rc = ERR_OK;
    uint8_t run_on_start;
    
    eeprom_read_bytes( GET_STORE_OFFSET(run_on_start), sizeof(run_on_start), (uint8_t *)&run_on_start );
    
    *run_on_start_p = run_on_start;
    
    return rc;
}

extern void store_load_heat_power_limit_pc( uint8_t *heat_power_limit_pc )
{
    eeprom_read_bytes( GET_STORE_OFFSET(heat_power_limit_pc), sizeof(heat_power_limit_pc), (uint8_t *)heat_power_limit_pc );
}

/* Static Functions */

static err store_save_data( uint16_t offset, uint8_t data_len, uint8_t *data )
{
    err rc = ERR_OK;
    uint8_t verify_rc;
    
    eeprom_read_write_bytes( offset, data_len, data );
    verify_rc = eeprom_verify_bytes( offset, data_len, data );
    
    rc = ( verify_rc == 0 ) ? ERR_OK : ERR_EEPROM_VERIFY_FAIL;
    
    return rc;
}
