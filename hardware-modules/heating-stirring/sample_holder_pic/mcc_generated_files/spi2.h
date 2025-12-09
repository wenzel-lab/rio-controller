
/**
  SPI2 Generated Driver API Header File

  Company:
    Microchip Technology Inc.

  File Name:
    spi2.h

  @Summary
    This is the generated header file for the SPI2 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This header file provides APIs for driver for SPI2.
    Generation Information :
        Product Revision  :  PIC24 / dsPIC33 / PIC32MM MCUs - 1.145.0
        Device            :  dsPIC33CK256MP502
    The generated drivers are tested against the following:
        Compiler          :  XC16 v1.36b
        MPLAB             :  MPLAB X v5.25
*/

/*
    (c) 2019 Microchip Technology Inc. and its subsidiaries. You may use this
    software and any derivatives exclusively with Microchip products.

    THIS SOFTWARE IS SUPPLIED BY MICROCHIP "AS IS". NO WARRANTIES, WHETHER
    EXPRESS, IMPLIED OR STATUTORY, APPLY TO THIS SOFTWARE, INCLUDING ANY IMPLIED
    WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A
    PARTICULAR PURPOSE, OR ITS INTERACTION WITH MICROCHIP PRODUCTS, COMBINATION
    WITH ANY OTHER PRODUCTS, OR USE IN ANY APPLICATION.

    IN NO EVENT WILL MICROCHIP BE LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE,
    INCIDENTAL OR CONSEQUENTIAL LOSS, DAMAGE, COST OR EXPENSE OF ANY KIND
    WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER CAUSED, EVEN IF MICROCHIP HAS
    BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE FORESEEABLE. TO THE
    FULLEST EXTENT ALLOWED BY LAW, MICROCHIP'S TOTAL LIABILITY ON ALL CLAIMS IN
    ANY WAY RELATED TO THIS SOFTWARE WILL NOT EXCEED THE AMOUNT OF FEES, IF ANY,
    THAT YOU HAVE PAID DIRECTLY TO MICROCHIP FOR THIS SOFTWARE.

    MICROCHIP PROVIDES THIS SOFTWARE CONDITIONALLY UPON YOUR ACCEPTANCE OF THESE
    TERMS.
*/

#ifndef _SPI2_H
#define _SPI2_H

/**
 Section: Included Files
*/

#include <xc.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus  // Provide C++ Compatibility

    extern "C" {

#endif

/**
 Section: Data Type Definitions
*/
        
/**
  SPI2_DUMMY_DATA 

  @Summary
    Dummy data to be sent. 

  @Description
    Dummy data to be sent, when no input buffer is specified in the buffer APIs.
 */
#define SPI2_DUMMY_DATA 0xFF
        
/**
  SPI2_FIFO_FILL_LIMIT

  @Summary
    FIFO fill limit for data transmission. 

  @Description
    The amount of data to be filled in the FIFO during transmission. The maximum limit allowed is 8.
 */
#define SPI2_FIFO_FILL_LIMIT 0x8

//Check to make sure that the FIFO limit does not exceed the maximum allowed limit of 8
#if (SPI2_FIFO_FILL_LIMIT > 8)

    #define SPI2_FIFO_FILL_LIMIT 8

#endif

/**
  SPI2 Status Enumeration

  @Summary
    Defines the status enumeration for SPI2.

  @Description
    This defines the status enumeration for SPI2.
 */
typedef enum {
    SPI2_SHIFT_REGISTER_EMPTY  = 1 << 7,
    SPI2_RECEIVE_OVERFLOW = 1 << 6,
    SPI2_RECEIVE_FIFO_EMPTY = 1 << 5,
    SPI2_TRANSMIT_BUFFER_FULL = 1 << 1,
    SPI2_RECEIVE_BUFFER_FULL = 1 << 0
}SPI2_STATUS;

/**
 Section: Interface Routines
*/

/**
  @Summary
    Initializes the SPI instance : 2

  @Description
    This routine initializes the spi2 driver instance for : 2
    index, making it ready for clients to open and use it.

    This routine must be called before any other SPI2 routine is called.
    This routine should only be called once during system initialization.
 
  @Preconditions
    None.

  @Returns
    None.

  @Param
    None.

  @Example
    <code>
    uint16_t   myWriteBuffer[MY_BUFFER_SIZE];
    uint16_t   myReadBuffer[MY_BUFFER_SIZE];
    uint16_t writeData;
    uint16_t readData;
    SPI2_STATUS status;
    unsigned int    total;
    SPI2_Initialize;
 
    total = 0;
    numberOfBytesFactor = 2;
    do
    {
        total  = SPI2_Exchange16bitBuffer( &myWriteBuffer[total], (MY_BUFFER_SIZE - total)*numberOfBytesFactor, &myReadBuffer[total]);

        // Do something else...

    } while( total < MY_BUFFER_SIZE );

    readData = SPI2_Exchange16bit( writeData);

    status = SPI2_StatusGet();

    </code>

*/

void SPI2_Initialize (void);




/**
  @Summary
    Exchanges one byte of data from SPI2

  @Description
    This routine exchanges one byte of data from the SPI2.
    This is a blocking routine.

  @Preconditions
    The SPI2_Initialize routine must have been called for the specified
    SPI2 driver instance.

  @Returns
    Data read from SPI2

  @Param
    data         - Data to be written onto SPI2.

  @Example 
    Refer to SPI2_Initialize() for an example    
*/
        
uint8_t SPI2_Exchange8bit( uint8_t data );

/**
  @Summary
    Exchanges data from a buffer of size one byte from SPI2

  @Description
    This routine exchanges data from a buffer of size one byte from the SPI2.
    This is a blocking routine.

  @Preconditions
    The SPI2_Initialize routine must have been called for the specified
    SPI2 driver instance.

  @Returns
    Number of 8bit data written/read.

  @Param
    dataTransmitted         - Buffer of data to be written onto SPI2.
 
  @Param
    byteCount         - Number of bytes to be exchanged.
 
  @Param
    dataReceived         - Buffer of data to be read from SPI2.

  @Example 
    Refer to SPI2_Initialize() for an example    
 
*/

uint16_t SPI2_Exchange8bitBuffer(uint8_t *dataTransmitted, uint16_t byteCount, uint8_t *dataReceived);

/**
  @Summary
    Returns the value of the status register of SPI instance : 2

  @Description
    This routine returns the value of the status register of SPI2 driver instance : 2

  @Preconditions
    None.

  @Returns
    Returns the value of the status register.

  @Param
    None.

  @Example 
    Refer to SPI2_Initialize() for an example    
 
*/

SPI2_STATUS SPI2_StatusGet(void);


#ifdef __cplusplus  // Provide C++ Compatibility

    }

#endif

#endif //_SPI2_H
    
/*******************************************************************************
 End of File
*/
