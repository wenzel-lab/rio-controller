#ifndef EEPROM_H
#define	EEPROM_H

#ifdef	__cplusplus
extern "C" {
#endif

#define EEPROM_BLANK_U8     0xFF
#define EEPROM_BLANK_U16    0xFFFF

typedef enum __attribute__((packed))
{
    EE_PROTECT_NONE          = 0,
    EE_PROTECT_UPPER_QUARTER = 1,
    EE_PROTECT_UPPER_HALF    = 2,
    EE_PROTECT_ALL           = 3,
} E_EE_PROTECT;

typedef union
{
    struct
    {
        uint8_t WIP : 1;            // Write in progress
        uint8_t WEL : 1;            // Write enable latched
        E_EE_PROTECT protect : 2;   // Block Protect
    };
    uint8_t value;
} ee_status_t;

extern bool eeprom_comms_check( void );
extern ee_status_t eeprom_read_status( void );
extern uint8_t eeprom_read_byte( uint16_t addr );
extern void eeprom_read_bytes( uint16_t addr, uint8_t num, uint8_t *data );
extern uint8_t eeprom_verify_bytes( uint16_t addr, uint8_t num, uint8_t *data );
extern void eeprom_set_wren( bool wren );
extern void eeprom_write_byte( uint16_t addr, uint8_t byte );
extern void eeprom_write_bytes( uint16_t addr, uint8_t num, uint8_t *data );
extern void eeprom_read_write_bytes( uint16_t addr, uint8_t num, uint8_t *data );

#ifdef	__cplusplus
}
#endif

#endif	/* EEPROM_H */

