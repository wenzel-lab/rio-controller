/**
  SPI1 Generated Driver File

  @Company
    Microchip Technology Inc.

  @File Name
    spi1.c

  @Summary
    This is the generated driver implementation file for the SPI1 driver using PIC10 / PIC12 / PIC16 / PIC18 MCUs

  @Description
    This source file provides APIs for SPI1.
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

/**
  Section: Included Files
*/

#include <xc.h>
#include "spi1.h"


uint8_t (*SPI1_xchgHandler)(uint8_t);
/**
  Section: Module APIs
*/

void SPI1_Initialize(void)
{
    // Set the SPI1 module to the options selected in the User Interface

    // SMP High Speed; CKE Active to Idle; 
    SSP1STAT = 0x40;

    // SSPEN enabled; CKP Idle:High, Active:Low; SSPM SCKx_nSSxenabled; 
    SSP1CON1 = 0x34;

    // SBCDE disabled; BOEN disabled; SCIE disabled; PCIE disabled; DHEN disabled; SDAHT 100ns; AHEN disabled; 
    SSP1CON3 = 0x00;
	
	SSP1BUF = SPI1_DUMMY_DATA;
	SPI1_setExchangeHandler(SPI1_DefaultExchangeHandler);
	
	PIE3bits.SSP1IE = 1;
}


void SPI1_ISR(void)
{
    SSP1BUF = SPI1_xchgHandler(SSP1BUF);
}


void SPI1_setExchangeHandler(uint8_t (* InterruptHandler)(uint8_t)){
    SPI1_xchgHandler = InterruptHandler;
}



uint8_t SPI1_DefaultExchangeHandler(uint8_t byte){
    // add your SPI1 interrupt custom code
    // or set custom function using SPI1_setExchangeHandler()
    return byte;
}

/**
 End of File
*/