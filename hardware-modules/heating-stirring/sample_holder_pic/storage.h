#ifndef STORAGE_H
#define	STORAGE_H

#ifdef	__cplusplus
extern "C" {
#endif

#define EEPROM_VER  1

extern err store_save_eeprom_ver( uint8_t eeprom_ver );
extern err store_save_pid( uint16_t pid_p, uint16_t pid_i, uint16_t pid_d );
extern err store_save_hpid_temp( int16_t hpid_temp_c_scaled );
extern err store_save_htune_temp( int16_t htune_temp_c_scaled );
extern err store_save_run_on_start( uint8_t run_on_start );
extern err store_save_heat_power_limit_pc( uint8_t heat_power_limit_pc );

extern err store_load_eeprom_ver( uint8_t *eeprom_ver_p );
extern err store_load_pid( uint16_t *pid_p, uint16_t *pid_i, uint16_t *pid_d );
extern err store_load_hpid_temp( int16_t *hpid_temp_c_scaled_p );
extern err store_load_htune_temp( int16_t *htune_temp_c_scaled_p );
extern err store_load_run_on_start( uint8_t *run_on_start_p );
extern void store_load_heat_power_limit_pc( uint8_t *heat_power_limit_pc );

#ifdef	__cplusplus
}
#endif

#endif	/* STORAGE_H */

