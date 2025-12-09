/**
  MSSP1 Generated Driver API Header File

  @Company
    Microchip Technology Inc.

  @File Name
    spi1.h

  @Summary
    This is the generated header file for the MSSP1 driver using PIC10 / PIC12 / PIC16 / PIC18 MCUs

  @Description
    This header file provides APIs for driver for MSSP1.
    Generation Information :
        Product Revision  :  PIC10 / PIC12 / PIC16 / PIC18 MCUs - 1.77
        Device            :  PIC16F18857
        Driver Version    :  1.02
    The generated drivers are tested against the following:
        Compiler          :  XC8 2.05 and above
        MPLAB 	          :  MPLAB X 5.20
*/

/*
    (c) 2018 Microchip Technology Inc. and its subsidiaries. 
    
    Subject to your compliance with these terms, you may use Microchip software and any 
    derivatives exclusively with Microchip products. It is your responsibility to comply with third party 
    license terms applicable to your use of third party software (including open source software) that 
    may accompany Microchip software.
    
    THIS SOFTWARE IS SUPPLIED BY MICROCHIP "AS IS". NO WARRANTIES, WHETHER 
    EXPRESS, IMPLIED OR STATUTORY, APPLY TO THIS SOFTWARE, INCLUDING ANY 
    IMPLIED WARRANTIES OF NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS 
    FOR A PARTICULAR PURPOSE.
    
    IN NO EVENT WILL MICROCHIP BE LIABLE FOR ANY INDIRECT, SPECIAL, PUNITIVE, 
    INCIDENTAL OR CONSEQUENTIAL LOSS, DAMAGE, COST OR EXPENSE OF ANY KIND 
    WHATSOEVER RELATED TO THE SOFTWARE, HOWEVER CAUSED, EVEN IF MICROCHIP 
    HAS BEEN ADVISED OF THE POSSIBILITY OR THE DAMAGES ARE FORESEEABLE. TO 
    THE FULLEST EXTENT ALLOWED BY LAW, MICROCHIP'S TOTAL LIABILITY ON ALL 
    CLAIMS IN ANY WAY RELATED TO THIS SOFTWARE WILL NOT EXCEED THE AMOUNT 
    OF FEES, IF ANY, THAT YOU HAVE PAID DIRECTLY TO MICROCHIP FOR THIS 
    SOFTWARE.
*/

#ifndef SPI1_H
#define SPI1_H

/**
  Section: Included Files
*/

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus  // Provide C++ Compatibility

    extern "C" {

#endif

/**
  Section: Macro Declarations
*/

#define SPI1_DUMMY_DATA 0xFF

/**
  Section: SPI1 Module APIs
*/

/**
  @Summary
    Initializes the SPI1

  @Description
    This routine initializes the SPI1.
    This routine must be called before any other SPI1 routine is called.
    This routine should only be called once during system initialization.

  @Preconditions
    None

  @Param
    None

  @Returns
    None

  @Comment
    

  @Example
    <code>
    uint8_t     myWriteBuffer[MY_BUFFER_SIZE];
    uint8_t     myReadBuffer[MY_BUFFER_SIZE];
    uint8_t     writeData;
    uint8_t     readData;
    uint8_t     total;

    SPI1_Initialize();

    total = 0;
    do
    {
        total = SPI1_Exchange8bitBuffer(&myWriteBuffer[total], MY_BUFFER_SIZE - total, &myWriteBuffer[total]);

        // Do something else...

    } while(total < MY_BUFFER_SIZE);

    readData = SPI1_Exchange8bit(writeData);
    </code>
 */
void SPI1_Initialize(void);

/**
  @Summary
    SPI1 Interrupt Service Routine

  @Description
    SPI1 Interrupt Service Routine is called by the Interrupt Manager.

  @Returns
    None

  @Param
    None
*/
void SPI1_ISR(void);

/**
  @Summary
    Set SPI1 Interrupt Handler

  @Description
    This sets the function to be called during the ISR

  @Preconditions
    Initialize  the SPI1 module with interrupt before calling this.

  @Param
    Address of function to be set

  @Returns
    None
*/
 void SPI1_setExchangeHandler(uint8_t (* InterruptHandler)(uint8_t));

/**
  @Summary
    Default SPI1 Interrupt Handler

  @Description
    This is the default Interrupt Handler function. The data to be transmitted must be loaded into SSPBUF register by the user.

  @Preconditions
    Initialize  the SPI1 module with interrupt before calling this isr.

  @Param
    None

  @Returns
    None
*/
uint8_t SPI1_DefaultExchangeHandler(uint8_t byte);

#ifdef __cplusplus  // Provide C++ Compatibility

    }

#endif

#endif // _SPI1_H
/**
 End of File
*/
