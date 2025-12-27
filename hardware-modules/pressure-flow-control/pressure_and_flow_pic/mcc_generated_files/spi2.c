
/**
  SPI2 Generated Driver API Source File

  Company:
    Microchip Technology Inc.

  File Name:
    spi2.c

  @Summary
    This is the generated source file for the SPI2 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This source file provides APIs for driver for SPI2.
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

#include "spi2.h"

/**
 Section: File specific functions
*/

/**
  SPI2 Transfer Mode Enumeration

  @Summary
    Defines the Transfer Mode enumeration for SPI2.

  @Description
    This defines the Transfer Mode enumeration for SPI2.
 */
typedef enum {
    SPI2_TRANSFER_MODE_32BIT  = 2,
    SPI2_TRANSFER_MODE_16BIT = 1,
    SPI2_TRANSFER_MODE_8BIT = 0
}SPI2_TRANSFER_MODE;

inline __attribute__((__always_inline__)) SPI2_TRANSFER_MODE SPI2_TransferModeGet(void);
void SPI2_Exchange( uint8_t *pTransmitData, uint8_t *pReceiveData );
uint16_t SPI2_ExchangeBuffer(uint8_t *pTransmitData, uint16_t byteCount, uint8_t *pReceiveData);

/**
 Section: Driver Interface Function Definitions
*/


void SPI2_Initialize (void)
{
    // AUDEN disabled; FRMEN enabled; AUDMOD I2S; FRMSYPW One serial word length; AUDMONO stereo; FRMCNT 0; MSSEN enabled; FRMPOL disabled; IGNROV disabled; SPISGNEXT not sign-extended; FRMSYNC disabled; URDTEN disabled; IGNTUR disabled; 
    SPI2CON1H = 0x98;
    // WLENGTH 23; 
    SPI2CON2L = 0x17;
    // SPIROV disabled; FRMERR disabled; 
    SPI2STATL = 0x00;
    // SPI2BRGL 64; 
    SPI2BRGL = 0x40;
    // SPITBFEN disabled; SPITUREN disabled; FRMERREN disabled; SRMTEN disabled; SPIRBEN disabled; BUSYEN disabled; SPITBEN disabled; SPIROVEN disabled; SPIRBFEN disabled; 
    SPI2IMSKL = 0x00;
    // RXMSK 0; TXWIEN disabled; TXMSK 0; RXWIEN disabled; 
    SPI2IMSKH = 0x00;
    // SPI2URDTL 0; 
    SPI2URDTL = 0x00;
    // SPI2URDTH 0; 
    SPI2URDTH = 0x00;
    // SPIEN enabled; DISSDO disabled; MCLKEN FOSC/2; CKP Idle:High, Active:Low; SSEN disabled; MSTEN Master; MODE16 disabled; SMP Middle; DISSCK disabled; SPIFE Frame Sync pulse coincides; CKE Active to Idle; MODE32 enabled; SPISIDL disabled; ENHBUF enabled; DISSDI disabled; 
    SPI2CON1L = 0x8963;

}

void SPI2_Exchange( uint8_t *pTransmitData, uint8_t *pReceiveData )
{

    while( SPI2STATLbits.SPITBF == true )
    {

    }

    SPI2BUFL = *((uint16_t*)pTransmitData);
    SPI2BUFH = *((uint16_t*)(pTransmitData+2));

    while ( SPI2STATLbits.SPIRBE == true)
    {
    
    }

    *((uint16_t*)pReceiveData) = SPI2BUFL;
    *((uint16_t*)(pReceiveData+2)) = SPI2BUFH;

}

uint16_t SPI2_ExchangeBuffer(uint8_t *pTransmitData, uint16_t byteCount, uint8_t *pReceiveData)
{

    uint16_t dataSentCount = 0;
    uint16_t dataReceivedCount = 0;
    uint16_t dummyDataReceived = 0;
    uint32_t dummyDataTransmit = SPI2_DUMMY_DATA;

    uint8_t  *pSend, *pReceived;
    uint16_t addressIncrement;
    uint16_t receiveAddressIncrement, sendAddressIncrement;

    addressIncrement = 4;
    byteCount >>= 2;


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


    while( SPI2STATLbits.SPITBF == true )
    {

    }

    while (dataSentCount < byteCount)
    {
        if ( SPI2STATLbits.SPITBF != true )
        {

            SPI2BUFL = *((uint16_t*)pSend);
            SPI2BUFH = *((uint16_t*)(pSend+2));

            pSend += sendAddressIncrement;
            dataSentCount++;
        }

        if (SPI2STATLbits.SPIRBE == false)
        {

            *((uint16_t*)pReceived) = SPI2BUFL;
            *((uint16_t*)(pReceived+2)) = SPI2BUFH;

            pReceived += receiveAddressIncrement;
            dataReceivedCount++;
        }

    }
    while (dataReceivedCount < byteCount)
    {
        if (SPI2STATLbits.SPIRBE == false)
        {

            *((uint16_t*)pReceived) = SPI2BUFL;
            *((uint16_t*)(pReceived+2)) = SPI2BUFH;

            pReceived += receiveAddressIncrement;
            dataReceivedCount++;
        }
    }

    return dataSentCount;
}

uint32_t SPI2_Exchange32bit( uint32_t data )
{
    uint32_t receiveData;

    SPI2_Exchange((uint8_t*)&data, (uint8_t*)&receiveData);

    return (receiveData);
}


uint16_t SPI2_Exchange32bitBuffer(uint32_t *dataTransmitted, uint16_t byteCount, uint32_t *dataReceived)
{
    return (SPI2_ExchangeBuffer((uint8_t*)dataTransmitted, byteCount, (uint8_t*)dataReceived));
}



inline __attribute__((__always_inline__)) SPI2_TRANSFER_MODE SPI2_TransferModeGet(void)
{
    if (SPI2CON1Lbits.MODE32 == 1)
        return SPI2_TRANSFER_MODE_32BIT;
    else if (SPI2CON1Lbits.MODE16 == 1)
        return SPI2_TRANSFER_MODE_16BIT;
    else
        return SPI2_TRANSFER_MODE_8BIT;
}

SPI2_STATUS SPI2_StatusGet()
{
    return(SPI2STATL);
}

/**
 End of File
*/
