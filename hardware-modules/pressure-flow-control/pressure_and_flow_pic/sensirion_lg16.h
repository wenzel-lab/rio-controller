#ifndef SENSIRION_H
#define	SENSIRION_H

#ifdef	__cplusplus
extern "C" {
#endif
    
#define SENSIRION_PART_NAME_LEN_WORDS   10
#define SENSIRION_PART_NAME_LEN_BYTES   20
#define SENSIRION_PART_NAME_STR_LEN     21
    
#define SENSIRION_REG_ADV_USER_WRITE    0xE4
#define SENSIRION_REG_ADV_USER_READ     0xE5

#define SENSIRION_EEPROM_ADDR_PART_NAME 0x2E80
#define SENSIRION_EEPROM_ADDR_SCALE0    0x2B60

#define SENSIRION_FLOW_SCALE_ML_MIN     500
#define SENSIRION_TEMP_SCALE_DEGC       200

typedef struct __attribute__((packed))
{
    uint8_t air_in_line : 1;
    uint8_t high_flow : 1;
    uint8_t : 3;
    uint8_t exp_smoothing_active : 1;
    uint16_t : 10;
} sensirion_flags_t;

extern err sensirion_read_eeprom( uint16_t addr, uint8_t bytes, uint8_t *reg_data );
extern err sensirion_read_reg( uint8_t reg, uint16_t *reg_data );
extern err sensirion_write_reg( uint8_t reg, uint16_t reg_data );

extern err sensirion_reset( bool wait );
extern err sensirion_read_part_name( char *part_name );
extern err sensirion_read_scale( uint16_t addr, uint16_t *scale );
extern err sensirion_measurement_start( void );
extern err sensirion_measurement_read( int16_t *flow );

#ifdef	__cplusplus
}
#endif

#endif	/* SENSIRION_H */

