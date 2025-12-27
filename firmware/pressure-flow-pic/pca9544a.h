#ifndef PCA9544A_H
#define	PCA9544A_H

#ifdef	__cplusplus
extern "C" {
#endif

extern err pca9544a_write( uint8_t addr, uint8_t enabled, uint8_t channel );
extern err pca9544a_read( uint8_t addr, uint8_t *ints, uint8_t *enabled, uint8_t *channel );

#ifdef	__cplusplus
}
#endif

#endif	/* PCA9544A_H */

