#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xc.h>
#include "common.h"
#include "spi.h"
//#include "mcc_generated_files/spi1.h"

#define SPI1_INT_ON()           { IEC0bits.SPI1RXIE = 1; }
#define SPI1_INT_OFF()          { IEC0bits.SPI1RXIE = 0; }

#define READ_BUF_SIZE           32
#define READ_BUF_SIZE_MASK      ( READ_BUF_SIZE - 1 )
#define WRITE_BUF_SIZE          32
#define WRITE_BUF_SIZE_MASK     ( WRITE_BUF_SIZE - 1 )

#define STX                     2

#ifdef SPI_READ_SUPPORTED
volatile uint8_t read_buf[READ_BUF_SIZE];
volatile uint8_t read_buf_head;
volatile uint8_t read_buf_tail;
volatile uint8_t read_buf_remaining;
#endif

#ifdef SPI_WRITE_SUPPORTED
volatile uint8_t write_buf[WRITE_BUF_SIZE];
volatile uint8_t write_buf_head;
volatile uint8_t write_buf_tail;
volatile uint8_t write_buf_remaining;
#endif

// Static Prototypes -------------------------------------------------------

static uint8_t spi_handler( uint8_t byte_in, uint8_t *byte_out );
//static void __attribute__( ( __interrupt__, auto_psv ) ) _SPI1RXInterrupt( void );

// Extern Functions --------------------------------------------------------

extern void spi_init( void )
{
#ifdef SPI_READ_SUPPORTED
    read_buf_head = 0;
    read_buf_tail = 0;
    read_buf_remaining = READ_BUF_SIZE;
#endif

#ifdef SPI_WRITE_SUPPORTED
    write_buf_head = 0;
    write_buf_tail = 0;
    write_buf_remaining = WRITE_BUF_SIZE;
#endif
    
//    SPI1_setExchangeHandler( spi_handler );
    SPI1STATL = 0;
    IFS0bits.SPI1RXIF = 0;
//    IEC0bits.SPI1RXIE = 1;
    SPI1_INT_ON();
}

#ifdef SPI_READ_SUPPORTED
extern uint8_t spi_read_bytes_available( void )
{
    return ( READ_BUF_SIZE - read_buf_remaining );
}
#endif

#ifdef SPI_WRITE_SUPPORTED
extern void spi_clear_write( void )
{
//    uint8_t int_enabled = SPI1IMSKLbits.SPIRBFEN;
    
    SPI1_INT_OFF();
    
//    SPI1IMSKLbits.SPIRBFEN = 0;
    write_buf_head = 0;
    write_buf_tail = 0;
    write_buf_remaining = WRITE_BUF_SIZE;
    
//    SPI1BUFL = 0xFF;
    
//    SPI1IMSKLbits.SPIRBFEN = int_enabled;
//    SPI1IMSKLbits.SPIRBFEN = 1;
    SPI1_INT_ON();
//    IEC0bits.SPI1RXIE = 1;
}
#endif

#ifdef SPI_WRITE_SUPPORTED
extern uint8_t spi_write_bytes_written( void )
{
    return ( WRITE_BUF_SIZE - write_buf_remaining );
}
#endif

#ifdef SPI_READ_SUPPORTED
extern uint8_t spi_read_byte( void )
{
    uint8_t byte = 0;
    
    if ( READ_BUF_SIZE != read_buf_remaining )
    {
        SPI1_INT_OFF();
        byte = read_buf[read_buf_tail];
        read_buf_tail = ( read_buf_tail + 1 ) & READ_BUF_SIZE_MASK;
        read_buf_remaining++;
        SPI1_INT_ON();
    }
    
    return byte;
}
#endif

#ifdef SPI_WRITE_SUPPORTED
extern err spi_write_byte( uint8_t byte )
{
    err rc = ERR_OK;
//    uint8_t add_to_buf = 1;
    
    if ( write_buf_remaining )
    {
        SPI1_INT_OFF();
//        SPI1IMSKLbits.SPIRBFEN = 0;
        SPI1STATLbits.SPITUR = 0;
        
        if ( WRITE_BUF_SIZE == write_buf_remaining )
        {
            /* Empty transmit buffer -> write byte directly */
            SPI1BUFL = byte;
            
            /* If collision -> just add to buffer instead */
//            add_to_buf = SSP1CON1bits.WCOL;
        }
        else
//        if ( add_to_buf )
        {
            write_buf[write_buf_head] = byte;
            write_buf_head = ( write_buf_head + 1 ) & WRITE_BUF_SIZE_MASK;
//            SSP1CON1bits.WCOL = 0;
        }
        
        write_buf_remaining--;
//        PIE3bits.SSP1IE = 1;
//        SPI1IMSKLbits.SPIRBFEN = 1;
        SPI1_INT_ON();
    }
    else
        rc = ERR_SPI_WRITE_OVERFLOW;
    
    return rc;
}
#endif

extern void spi_packet_clear( spi_packet_buf_t *packet )
{
    packet->buf_bytes = 0;
}

extern void spi_packet_init( spi_packet_buf_t *packet, uint16_t *timer_ptr, uint16_t timeout )
{
    spi_packet_clear( packet );
    
    packet->timer_ptr = timer_ptr;
    packet->timeout = timeout;
}

#ifdef SPI_READ_SUPPORTED
extern err spi_packet_read( spi_packet_buf_t *packet, uint8_t *packet_type, uint8_t *data, uint8_t *data_size, uint8_t data_buf_size )
{
    /* Returns ERR_OK(0) if good packet, non-zero error otherwise */
    
    /* Packet format:
     * [STX U8=2][size U8][packet type U8][data...][checksum U8]
     */
    
    err rc = ERR_OK;
    uint8_t invalidate = 0;
    uint8_t packet_size;
    uint8_t type;
    uint8_t checksum;
    uint8_t *data_ptr;
    uint8_t *buf_ptr;
    uint8_t i;
    
    *packet_type = 0;
    
    /* Read until we find STX. */
    while ( ( packet->buf_bytes == 0 ) && spi_read_bytes_available() )
    {
//        printf( "Bytes: %hu\n", spi_read_bytes_available() );

        if ( spi_read_byte() == STX )
        {
            packet->buf[0] = STX;
            packet->buf_bytes = 1;
            packet->start_time = *packet->timer_ptr;
        }
    }
    
    if ( packet->buf_bytes > 0 )
    {
        /* We have an STX already. Keep reading. */
        while ( spi_read_bytes_available() && ( packet->buf_bytes < SPI_PACKET_BUF_SIZE ) )
            packet->buf[packet->buf_bytes++] = spi_read_byte();

        if ( ( *packet->timer_ptr - packet->start_time ) > packet->timeout )
        {
            rc = ERR_PACKET_TIMEOUT;
            invalidate = 1;
        }
        else if ( packet->buf_bytes >= 3 )
        {
            /* We have at minimum: STX, size and packet type */

            packet_size = packet->buf[1];
            
            if ( ( packet_size > SPI_PACKET_BUF_SIZE ) || ( packet_size > data_buf_size ) )
            {
                rc = ERR_PACKET_OVERFLOW;
                invalidate = 1;
            }
            else if ( packet_size < 4 )
            {
                /* Packet size is too small to be valid. */
                rc = ERR_PACKET_INVALID;
                invalidate = 1;
            }
            else if ( packet->buf_bytes >= packet_size )
            {
                type = packet->buf[2];
                *data_size = packet_size - 4;
                checksum = STX + packet_size + type + packet->buf[packet_size-1];
                data_ptr = data;
                buf_ptr = &packet->buf[3];

                /* Calculate checksum and copy over data. */
                for ( i=0; i<*data_size; i++ )
                {
                    checksum += *buf_ptr;
                    *data_ptr++ = *buf_ptr++;
                }

                if ( checksum != 0 )
                {
                    /* Bad checksum. Search until we find next STX. */
                    rc = ERR_PACKET_INVALID;
                    invalidate = 1;
                }
                else
                {
                    /* Checksum is good. */

//                    printf( "Packet %hu\n", type );
//                    printf( "Packet Size %hu\n", packet_size );
//                    printf( "Data Size %hu\n", *data_size );
//                    printf( "Available %hu\n", spi_read_bytes_available() );
                    
                    if ( packet->buf_bytes == packet_size )
                        packet->buf_bytes = 0;
                    else
                    {
                        /* Shift up remaining data */

                        uint8_t buf_bytes = packet->buf_bytes;
                        packet->buf_bytes -= packet_size;
                        memcpy( packet->buf, &packet->buf[buf_bytes], packet->buf_bytes );
                    }

                    if ( type == 0 )
                        rc = ERR_PACKET_INVALID;
                    else
                        *packet_type = type;
                }
            }
        }
        
        if ( invalidate )
        {
            /* Data in buffer is invalid -> look for next STX. */

            buf_ptr = &packet->buf[1];
            for ( i=1; i<packet->buf_bytes; i++ )
                if ( packet->buf[i] == STX )
                    break;

            packet->buf_bytes -= i;
            memcpy( packet->buf, &packet->buf[i], packet->buf_bytes );
        }
    }
    
    return rc;
}
#endif

#ifdef SPI_WRITE_SUPPORTED
extern err spi_packet_write( uint8_t packet_type, uint8_t *data, uint8_t data_size )
{
    /* Returns ERR_OK(0) if write successful, non-zero error otherwise */
    
    /* Packet format:
     * [STX U8=2][size U8][packet type U8][data...][checksum U8]
     */
    
    uint8_t rc = ERR_OK;
    uint8_t packet_size;
    uint8_t checksum;
    uint8_t byte;
    
    packet_size = data_size + 4;
    
    if ( write_buf_remaining < packet_size )
        rc = ERR_SPI_WRITE_OVERFLOW;
    else
    {
        spi_write_byte( STX );          checksum = STX;
        spi_write_byte( packet_size );  checksum += packet_size;
        spi_write_byte( packet_type );  checksum += packet_type;
        while ( data_size-- )
        {
            byte = *data++;
            spi_write_byte( byte );
            checksum += byte;
        }
        spi_write_byte( -checksum );
    }
    
    return rc;
}
#endif

uint8_t spi_packet_timeout( spi_packet_buf_t *packet )
{
    return ( ( *packet->timer_ptr - packet->start_time ) > packet->timeout );
}

// Static Functions --------------------------------------------------------

static uint8_t spi_handler( uint8_t byte_in, uint8_t *byte_out )
{
#ifdef SPI_READ_SUPPORTED
    if ( read_buf_remaining )
    {
        read_buf[read_buf_head] = byte_in;
        read_buf_head = ( read_buf_head + 1 ) & READ_BUF_SIZE_MASK;
        read_buf_remaining--;
    }
#endif

#ifdef SPI_WRITE_SUPPORTED
    /* Decrease buffer count since previous byte just sent */
    if ( WRITE_BUF_SIZE != write_buf_remaining )
    {
        write_buf_remaining++;

        if ( WRITE_BUF_SIZE != write_buf_remaining )
        {
            *byte_out = write_buf[write_buf_tail];
            byte_in = 1;
            write_buf_tail = ( write_buf_tail + 1 ) & WRITE_BUF_SIZE_MASK;
        }
        else
            byte_in = 0;
    }
    else
        byte_in = 0;
#endif
    
    return byte_in;
}

static void __attribute__( ( __interrupt__, auto_psv ) ) _SPI1RXInterrupt( void )
{
    uint8_t byte_out;
    
    IFS0bits.SPI1RXIF = 0;
//    SPI1STATL = 0;
//    uint8_t dummy;
    
//    dummy = SPI1BUFL;
//    SPI1BUFL = 11;
//    PORTAbits.RA0 = 1;
    
    SPI1STATLbits.SPIROV = 0;
    SPI1STATLbits.SPITUR = 0;
    
    if ( SPI1IMSKLbits.SPIRBFEN && SPI1STATLbits.SPIRBF )
    {
//        SPI1STATLbits.SPIRBF = 0;
//        SPI1STATL = 0;
        if ( spi_handler( SPI1BUFL, &byte_out ) )
            SPI1BUFL = byte_out;
    }
}
