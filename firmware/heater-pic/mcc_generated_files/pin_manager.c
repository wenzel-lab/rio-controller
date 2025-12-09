/**
  PIN MANAGER Generated Driver File

  @Company:
    Microchip Technology Inc.

  @File Name:
    pin_manager.c

  @Summary:
    This is the generated manager file for the PIC24 / dsPIC33 / PIC32MM MCUs device.  This manager
    configures the pins direction, initial state, analog setting.
    The peripheral pin select, PPS, configuration is also handled by this manager.

  @Description:
    This source file provides implementations for PIN MANAGER.
    Generation Information :
        Product Revision  :  PIC24 / dsPIC33 / PIC32MM MCUs - 1.145.0
        Device            :  dsPIC33CK256MP502
    The generated drivers are tested against the following:
        Compiler          :  XC16 v1.36b
        MPLAB 	          :  MPLAB X v5.25
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
    Section: Includes
*/

#include <xc.h>
#include <stdio.h>
#include "pin_manager.h"

/**
 Section: File specific functions
*/

/**
 Section: Driver Interface Function Definitions
*/
void PIN_MANAGER_Initialize (void)
{
    /****************************************************************************
     * Setting the Output Latch SFR(s)
     ***************************************************************************/
    LATA = 0x0000;
    LATB = 0x8080;

    /****************************************************************************
     * Setting the GPIO Direction SFR(s)
     ***************************************************************************/
    TRISA = 0x001F;
    TRISB = 0x2771;

    /****************************************************************************
     * Setting the Weak Pull Up and Weak Pull Down SFR(s)
     ***************************************************************************/
    CNPDA = 0x0000;
    CNPDB = 0x0000;
    CNPUA = 0x0000;
    CNPUB = 0x07C7;

    /****************************************************************************
     * Setting the Open Drain SFR(s)
     ***************************************************************************/
    ODCA = 0x0000;
    ODCB = 0x0000;

    /****************************************************************************
     * Setting the Analog/Digital Configuration SFR(s)
     ***************************************************************************/
    ANSELA = 0x001F;
    ANSELB = 0x0000;


    /****************************************************************************
     * Set the PPS
     ***************************************************************************/
    __builtin_write_RPCON(0x0000); // unlock PPS

    RPINR22bits.SCK2R = 0x0021;    //RB1->SPI2:SCK2OUT
    RPINR6bits.TCKI4R = 0x002A;    //RB10->SCCP4:TCKI4
    RPINR5bits.ICM3R = 0x002A;    //RB10->SCCP3:ICM3
    RPOR6bits.RP44R = 0x0010;    //RB12->SCCP2:OCM2
    RPOR3bits.RP39R = 0x000A;    //RB7->SPI2:SS2OUT
    RPOR1bits.RP35R = 0x0005;    //RB3->SPI1:SDO1
    RPINR20bits.SCK1R = 0x0025;    //RB5->SPI1:SCK1IN
    RPOR7bits.RP47R = 0x0001;    //RB15->UART1:U1TX
    RPINR21bits.SS1R = 0x0020;    //RB0->SPI1:SS1
    RPINR22bits.SDI2R = 0x0026;    //RB6->SPI2:SDI2
    RPOR5bits.RP43R = 0x000F;    //RB11->SCCP1:OCM1
    RPOR0bits.RP33R = 0x0009;    //RB1->SPI2:SCK2OUT
    RPOR7bits.RP46R = 0x0014;    //RB14->SCCP6:OCM6
    RPOR1bits.RP34R = 0x0008;    //RB2->SPI2:SDO2
    RPINR20bits.SDI1R = 0x0024;    //RB4->SPI1:SDI1

    __builtin_write_RPCON(0x0800); // lock PPS

}


