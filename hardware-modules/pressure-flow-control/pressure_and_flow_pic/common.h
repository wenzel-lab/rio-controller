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
/* v3: little-endian 32-bit copy, byte-wise like COPY_16BIT_TO_PTR */
#define COPY_32BIT_TO_PTR(ptr,val)      {uint8_t _i; for(_i=0;_i<4;_i++) *((uint8_t *)(ptr)+_i)=*((uint8_t *)&(val)+_i);}

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
#define ERR_SENSIRION_CRC_FAIL      71      /* v3: reading rejected by CRC-8 */
#define ERR_SENSIRION_RESOLUTION_INVALID 72 /* v3: resolution outside 9..16 bit */
#define ERR_SENSIRION_NOT_READY     73      /* v3: read header NACKed = measurement still running (hold-master off) */
#define ERR_FLOW_BATCH_GAP          74      /* v3.2: requested sequence no longer in the ring; batch restarts from oldest kept */

#define ERR_PCA9544A_COMMS_FAIL     80

#define ERR_ADS1115_COMMS_FAIL      90

typedef uint8_t err;

extern volatile uint16_t timer_ms;

#ifdef	__cplusplus
}
#endif

#endif	/* COMMON_H */

