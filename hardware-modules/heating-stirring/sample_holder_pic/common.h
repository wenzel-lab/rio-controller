#ifndef COMMON_H
#define	COMMON_H

#ifdef	__cplusplus
extern "C" {
#endif

/* Errors */
#define ERR_OK                      0
#define ERR_ERROR                   1

#define ERR_SPI_WRITE_OVERFLOW      20

#define ERR_PACKET_OVERFLOW         30
#define ERR_PACKET_INVALID          31
#define ERR_PACKET_TIMEOUT          32
#define ERR_PACKET_PID_INVALID      33
    
#define ERR_HEAT_TARGET_INVALID     40
#define ERR_HEAT_PID_NOT_READY      41
#define ERR_HEAT_AUTOTUNE_ACTIVE    42
#define ERR_HEAT_MAX_POWER_INVALID  43

#define ERR_STIR_PID_NOT_READY      51

#define ERR_EEPROM_VERIFY_FAIL      60

typedef uint8_t err;

extern volatile uint16_t timer_ms;

#ifdef	__cplusplus
}
#endif

#endif	/* COMMON_H */

