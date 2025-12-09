/* 
 * File:   common.h
 * Author: Cyrus
 *
 * Created on October 4, 2019, 1:04 PM
 */

#ifndef COMMON_H
#define	COMMON_H

#ifdef	__cplusplus
extern "C" {
#endif

/* Macros */
#define COPY_16BIT_TO_PTR(ptr,val)      {*((uint8_t *)(ptr)+1)=*((uint8_t *)&(val)+1); *(uint8_t *)(ptr)=*(uint8_t *)&(val);}

/* For __delay_ms */
#define FCY 75000000UL

/* System Constants */
#define NUM_PRESSURE_CLTRLS                 4

/* Errors */
#define ERR_OK                      0
#define ERR_ERROR                   1

#define ERR_SPI_WRITE_OVERFLOW      20

#define ERR_PACKET_OVERFLOW         30
#define ERR_PACKET_INVALID          31
#define ERR_PACKET_TIMEOUT          32
    
#define ERR_HEAT_TARGET_INVALID     40
#define ERR_HEAT_PID_NOT_READY      41

#define ERR_STIR_PID_NOT_READY      51

#define ERR_EEPROM_VERIFY_FAIL      60

#define ERR_SENSIRION_COMMS_FAIL    70

#define ERR_PCA9544A_COMMS_FAIL     80

#define ERR_ADS1115_COMMS_FAIL      90

typedef uint8_t err;

extern volatile uint16_t timer_ms;

#ifdef	__cplusplus
}
#endif

#endif	/* COMMON_H */

