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

/* Errors */
#define ERR_OK                      0
#define ERR_ERROR                   1

#define ERR_SPI_WRITE_OVERFLOW      20

#define ERR_PACKET_OVERFLOW         30
#define ERR_PACKET_INVALID          31

typedef uint8_t err;

#ifdef	__cplusplus
}
#endif

#endif	/* COMMON_H */

