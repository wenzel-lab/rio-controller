/**
  SCCP2 Generated Driver File 

  @Company
    Microchip Technology Inc.

  @File Name
    sccp2.c

  @Summary
    This is the generated driver implementation file for the SCCP2 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This header file provides implementations for driver APIs for SCCP2. 
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

#include "sccp2_compare.h"

/** OC Mode.

  @Summary
    Defines the OC Mode.

  @Description
    This data type defines the OC Mode of operation.

*/

static uint16_t         gSCCP2Mode;

/**
  Section: Driver Interface
*/


void SCCP2_COMPARE_Initialize (void)
{
    // CCPON enabled; MOD Dual Edge Compare, Buffered(PWM); CCSEL disabled; CCPSIDL disabled; TMR32 16 Bit; CCPSLP disabled; TMRPS 1:1; CLKSEL FOSC/2; TMRSYNC disabled; 
    CCP2CON1L = (0x8005 & 0x7FFF); //Disabling CCPON bit
    //RTRGEN disabled; ALTSYNC disabled; ONESHOT disabled; TRIGEN disabled; IOPS Each Time Base Period Match; SYNC None; OPSRC Timer Interrupt Event; 
    CCP2CON1H = 0x00;
    //ASDGM disabled; SSDG disabled; ASDG 0; PWMRSEN disabled; 
    CCP2CON2L = 0x00;
    //ICGSM Level-Sensitive mode; ICSEL IC2; AUXOUT Disabled; OCAEN enabled; OENSYNC disabled; 
    CCP2CON2H = 0x100;
    //OETRIG disabled; OSCNT None; POLACE disabled; PSSACE Tri-state; 
    CCP2CON3H = 0x00;
    //ICDIS disabled; SCEVT disabled; TRSET disabled; ICOV disabled; ASEVT disabled; TRIG disabled; ICGARM disabled; TRCLR disabled; 
    CCP2STATL = 0x00;
    //TMR 0; 
    CCP2TMRL = 0x00;
    //TMR 0; 
    CCP2TMRH = 0x00;
    //PR 255; 
    CCP2PRL = 0xFF;
    //PR 0; 
    CCP2PRH = 0x00;
    //CMP 0; 
    CCP2RAL = 0x00;
    //CMP 0; 
    CCP2RBL = 0x00;
    //BUF 0; 
    CCP2BUFL = 0x00;
    //BUF 0; 
    CCP2BUFH = 0x00;

    CCP2CON1Lbits.CCPON = 0x1; //Enabling CCP

    gSCCP2Mode = CCP2CON1Lbits.MOD;

}

void __attribute__ ((weak)) SCCP2_COMPARE_CallBack(void)
{
    // Add your custom callback code here
}

void SCCP2_COMPARE_Tasks( void )
{
    if(IFS1bits.CCP2IF)
    {
		// SCCP2 COMPARE callback function 
		SCCP2_COMPARE_CallBack();
		
        IFS1bits.CCP2IF = 0;
    }
}

void __attribute__ ((weak)) SCCP2_COMPARE_TimerCallBack(void)
{
    // Add your custom callback code here
}


void SCCP2_COMPARE_TimerTasks( void )
{
    if(IFS1bits.CCT2IF)
    {
		// SCCP2 COMPARE Timer callback function 
		SCCP2_COMPARE_TimerCallBack();
	
        IFS1bits.CCT2IF = 0;
    }
}

void SCCP2_COMPARE_Start( void )
{
    /* Start the Timer */
    CCP2CON1Lbits.CCPON = true;
}

void SCCP2_COMPARE_Stop( void )
{
    /* Start the Timer */
    CCP2CON1Lbits.CCPON = false;
}

void SCCP2_COMPARE_SingleCompare16ValueSet( uint16_t value )
{   
    CCP2RAL = value;
}


void SCCP2_COMPARE_DualCompareValueSet( uint16_t priVal, uint16_t secVal )
{

    CCP2RAL = priVal;

    CCP2RBL = secVal;
}

void SCCP2_COMPARE_DualEdgeBufferedConfig( uint16_t priVal, uint16_t secVal )
{

    CCP2RAL = priVal;

    CCP2RBL = secVal;
}

void SCCP2_COMPARE_CenterAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP2RAL = priVal;

    CCP2RBL = secVal;
}

void SCCP2_COMPARE_EdgeAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP2RAL = priVal;

    CCP2RBL = secVal;
}

void SCCP2_COMPARE_VariableFrequencyPulseConfig( uint16_t priVal )
{
    CCP2RAL = priVal;
}

bool SCCP2_COMPARE_IsCompareCycleComplete( void )
{
    return(IFS1bits.CCP2IF);
}

bool SCCP2_COMPARE_TriggerStatusGet( void )
{
    return( CCP2STATLbits.TRIG );
    
}

void SCCP2_COMPARE_TriggerStatusSet( void )
{
    CCP2STATLbits.TRSET = 1;
}

void SCCP2_COMPARE_TriggerStatusClear( void )
{
    /* Clears the trigger status */
    CCP2STATLbits.TRCLR = 0;
}

bool SCCP2_COMPARE_SingleCompareStatusGet( void )
{
    return( CCP2STATLbits.SCEVT );
}

void SCCP2_COMPARE_SingleCompareStatusClear( void )
{
    /* Clears the trigger status */
    CCP2STATLbits.SCEVT = 0;
    
}
/**
 End of File
*/
