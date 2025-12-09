#ifndef SPI_H
#define	SPI_H

#ifdef	__cplusplus
extern "C" {
#endif

#define SPI_READ_SUPPORTED
#define SPI_WRITE_SUPPORTED

/* Comms Constants */
#define SPI_PACKET_BUF_SIZE             32

typedef struct
{
    uint8_t buf[SPI_PACKET_BUF_SIZE];
    uint8_t buf_bytes;
} spi_packet_buf_t;

/* SPI Core Functions */
extern void spi_init( void );

#ifdef SPI_READ_SUPPORTED
extern uint8_t spi_read_bytes_available( void );
extern uint8_t spi_read_byte( void );
#endif

#ifdef SPI_WRITE_SUPPORTED
extern uint8_t spi_write_bytes_available( void );
extern err spi_write_byte( uint8_t byte );
#endif

/* SPI Packet Functions */
extern void spi_packet_clear( spi_packet_buf_t *packet );

#ifdef SPI_READ_SUPPORTED
extern err spi_packet_read( spi_packet_buf_t *packet, uint8_t *packet_type, uint8_t *data, uint8_t *data_size, uint8_t data_buf_size );
#endif

#ifdef SPI_WRITE_SUPPORTED
extern err spi_packet_write( uint8_t packet_type, uint8_t *data, uint8_t data_size );
#endif

#ifdef	__cplusplus
}
#endif

#endif	/* SPI_H */

