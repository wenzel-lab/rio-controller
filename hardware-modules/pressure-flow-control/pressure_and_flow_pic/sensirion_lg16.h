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

/* v3: measurement resolution (Advanced User Register bits 11:9) */
#define SENSIRION_ADV_USER_RESOLUTION_MASK   0x0E00
#define SENSIRION_ADV_USER_RESOLUTION_SHIFT  9
#define SENSIRION_RESOLUTION_MIN_BITS        9
#define SENSIRION_RESOLUTION_MAX_BITS        16
#define SENSIRION_RESOLUTION_DEFAULT_BITS    13     /* v3.2: 8.9 ms/measurement, 1 uL/h step; factory default is 16 (74 ms) */
#define SENSIRION_DRAIN_TIMEOUT_MS           80     /* v3.2: > 16 bit max processing time (73.2 ms) */

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
extern err sensirion_set_resolution( uint8_t bits );
extern uint8_t sensirion_crc8( const uint8_t *data, uint8_t len );
extern uint8_t sensirion_processing_time_min_ms( uint8_t bits );

#ifdef	__cplusplus
}
#endif

#endif	/* SENSIRION_H */

