
/**
  SPI3 Generated Driver API Source File

  Company:
    Microchip Technology Inc.

  File Name:
    spi3.c

  @Summary
    This is the generated source file for the SPI3 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This source file provides APIs for driver for SPI3.
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

/**
  Section: Included Files
*/

#include "spi3.h"

/**
 Section: File specific functions
*/

/**
  SPI3 Transfer Mode Enumeration

  @Summary
    Defines the Transfer Mode enumeration for SPI3.

  @Description
    This defines the Transfer Mode enumeration for SPI3.
 */
typedef enum {
    SPI3_TRANSFER_MODE_32BIT  = 2,
    SPI3_TRANSFER_MODE_16BIT = 1,
    SPI3_TRANSFER_MODE_8BIT = 0
}SPI3_TRANSFER_MODE;

inline __attribute__((__always_inline__)) SPI3_TRANSFER_MODE SPI3_TransferModeGet(void);
void SPI3_Exchange( uint8_t *pTransmitData, uint8_t *pReceiveData );
uint16_t SPI3_ExchangeBuffer(uint8_t *pTransmitData, uint16_t byteCount, uint8_t *pReceiveData);

/**
 Section: Driver Interface Function Definitions
*/


void SPI3_Initialize (void)
{
    // AUDEN disabled; FRMEN disabled; AUDMOD I2S; FRMSYPW One clock wide; AUDMONO stereo; FRMCNT 0; MSSEN disabled; FRMPOL disabled; IGNROV disabled; SPISGNEXT not sign-extended; FRMSYNC disabled; URDTEN disabled; IGNTUR disabled; 
    SPI3CON1H = 0x00;
    // WLENGTH 0; 
    SPI3CON2L = 0x00;
    // SPIROV disabled; FRMERR disabled; 
    SPI3STATL = 0x00;
    // SPI3BRGL 255; 
    SPI3BRGL = 0xFF;
    // SPITBFEN disabled; SPITUREN disabled; FRMERREN disabled; SRMTEN disabled; SPIRBEN disabled; BUSYEN disabled; SPITBEN disabled; SPIROVEN disabled; SPIRBFEN disabled; 
    SPI3IMSKL = 0x00;
    // RXMSK 0; TXWIEN disabled; TXMSK 0; RXWIEN disabled; 
    SPI3IMSKH = 0x00;
    // SPI3URDTL 0; 
    SPI3URDTL = 0x00;
    // SPI3URDTH 0; 
    SPI3URDTH = 0x00;
    // SPIEN enabled; DISSDO disabled; MCLKEN FOSC/2; CKP Idle:Low, Active:High; SSEN disabled; MSTEN Master; MODE16 disabled; SMP Middle; DISSCK disabled; SPIFE Frame Sync pulse precedes; CKE Active to Idle; MODE32 disabled; SPISIDL disabled; ENHBUF enabled; DISSDI disabled; 
    SPI3CON1L = 0x8121;

}

void SPI3_Exchange( uint8_t *pTransmitData, uint8_t *pReceiveData )
{

    while( SPI3STATLbits.SPITBF == true )
    {

    }
        
    SPI3BUFL = *((uint8_t*)pTransmitData);

    while ( SPI3STATLbits.SPIRBE == true)
    {
    
    }

    *((uint8_t*)pReceiveData) = SPI3BUFL;
}

uint16_t SPI3_ExchangeBuffer(uint8_t *pTransmitData, uint16_t byteCount, uint8_t *pReceiveData)
{

    uint16_t dataSentCount = 0;
    uint16_t dataReceivedCount = 0;
    uint16_t dummyDataReceived = 0;
    uint16_t dummyDataTransmit = SPI3_DUMMY_DATA;

    uint8_t  *pSend, *pReceived;
    uint16_t addressIncrement;
    uint16_t receiveAddressIncrement, sendAddressIncrement;

    addressIncrement = 1;

    // set the pointers and increment delta 
    // for transmit and receive operations
    if (pTransmitData == NULL)
    {
        sendAddressIncrement = 0;
        pSend = (uint8_t*)&dummyDataTransmit;
    }
    else
    {
        sendAddressIncrement = addressIncrement;
        pSend = (uint8_t*)pTransmitData;
    }
        
    if (pReceiveData == NULL)
    {
       receiveAddressIncrement = 0;
       pReceived = (uint8_t*)&dummyDataReceived;
    }
    else
    {
       receiveAddressIncrement = addressIncrement;        
       pReceived = (uint8_t*)pReceiveData;
    }


    while( SPI3STATLbits.SPITBF == true )
    {

    }

    while (dataSentCount < byteCount)
    {
        if ( SPI3STATLbits.SPITBF != true )
        {

            SPI3BUFL = *pSend;

            pSend += sendAddressIncrement;
            dataSentCount++;

        }

        if (SPI3STATLbits.SPIRBE == false)
        {

            *pReceived = SPI3BUFL;

            pReceived += receiveAddressIncrement;
            dataReceivedCount++;
        }

    }
    while (dataReceivedCount < byteCount)
    {
        if (SPI3STATLbits.SPIRBE == false)
        {

            *pReceived = SPI3BUFL;

            pReceived += receiveAddressIncrement;
            dataReceivedCount++;
        }
    }

    return dataSentCount;
}

uint8_t SPI3_Exchange8bit( uint8_t data )
{
    uint8_t receiveData;
    
    SPI3_Exchange(&data, &receiveData);

    return (receiveData);
}


uint16_t SPI3_Exchange8bitBuffer(uint8_t *dataTransmitted, uint16_t byteCount, uint8_t *dataReceived)
{
    return (SPI3_ExchangeBuffer(dataTransmitted, byteCount, dataReceived));
}

inline __attribute__((__always_inline__)) SPI3_TRANSFER_MODE SPI3_TransferModeGet(void)
{
    if (SPI3CON1Lbits.MODE32 == 1)
        return SPI3_TRANSFER_MODE_32BIT;
    else if (SPI3CON1Lbits.MODE16 == 1)
        return SPI3_TRANSFER_MODE_16BIT;
    else
        return SPI3_TRANSFER_MODE_8BIT;
}

SPI3_STATUS SPI3_StatusGet()
{
    return(SPI3STATL);
}

/**
 End of File
*/
