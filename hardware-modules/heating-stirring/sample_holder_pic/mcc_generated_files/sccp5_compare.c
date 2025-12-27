/**
  SCCP5 Generated Driver File 

  @Company
    Microchip Technology Inc.

  @File Name
    sccp5.c

  @Summary
    This is the generated driver implementation file for the SCCP5 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This header file provides implementations for driver APIs for SCCP5. 
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

#include "sccp5_compare.h"

/** OC Mode.

  @Summary
    Defines the OC Mode.

  @Description
    This data type defines the OC Mode of operation.

*/

static uint16_t         gSCCP5Mode;

/**
  Section: Driver Interface
*/


void SCCP5_COMPARE_Initialize (void)
{
    // CCPON enabled; MOD Dual Edge Compare, Buffered(PWM); CCSEL disabled; CCPSIDL disabled; TMR32 16 Bit; CCPSLP disabled; TMRPS 1:1; CLKSEL FOSC/2; TMRSYNC disabled; 
    CCP5CON1L = (0x8005 & 0x7FFF); //Disabling CCPON bit
    //RTRGEN disabled; ALTSYNC disabled; ONESHOT disabled; TRIGEN disabled; IOPS Each Time Base Period Match; SYNC None; OPSRC Timer Interrupt Event; 
    CCP5CON1H = 0x00;
    //ASDGM disabled; SSDG disabled; ASDG 0; PWMRSEN disabled; 
    CCP5CON2L = 0x00;
    //ICGSM Level-Sensitive mode; ICSEL IC5; AUXOUT OC Signal; OCAEN disabled; OENSYNC disabled; 
    CCP5CON2H = 0x18;
    //OETRIG disabled; OSCNT None; POLACE disabled; PSSACE Tri-state; 
    CCP5CON3H = 0x00;
    //ICDIS disabled; SCEVT disabled; TRSET disabled; ICOV disabled; ASEVT disabled; TRIG disabled; ICGARM disabled; TRCLR disabled; 
    CCP5STATL = 0x00;
    //TMR 0; 
    CCP5TMRL = 0x00;
    //TMR 0; 
    CCP5TMRH = 0x00;
    //PR 9; 
    CCP5PRL = 0x09;
    //PR 0; 
    CCP5PRH = 0x00;
    //CMP 5; 
    CCP5RAL = 0x05;
    //CMP 0; 
    CCP5RBL = 0x00;
    //BUF 0; 
    CCP5BUFL = 0x00;
    //BUF 0; 
    CCP5BUFH = 0x00;

    CCP5CON1Lbits.CCPON = 0x1; //Enabling CCP

    gSCCP5Mode = CCP5CON1Lbits.MOD;

}

void __attribute__ ((weak)) SCCP5_COMPARE_CallBack(void)
{
    // Add your custom callback code here
}

void SCCP5_COMPARE_Tasks( void )
{
    if(IFS2bits.CCP5IF)
    {
		// SCCP5 COMPARE callback function 
		SCCP5_COMPARE_CallBack();
		
        IFS2bits.CCP5IF = 0;
    }
}

void __attribute__ ((weak)) SCCP5_COMPARE_TimerCallBack(void)
{
    // Add your custom callback code here
}


void SCCP5_COMPARE_TimerTasks( void )
{
    if(IFS2bits.CCT5IF)
    {
		// SCCP5 COMPARE Timer callback function 
		SCCP5_COMPARE_TimerCallBack();
	
        IFS2bits.CCT5IF = 0;
    }
}

void SCCP5_COMPARE_Start( void )
{
    /* Start the Timer */
    CCP5CON1Lbits.CCPON = true;
}

void SCCP5_COMPARE_Stop( void )
{
    /* Start the Timer */
    CCP5CON1Lbits.CCPON = false;
}

void SCCP5_COMPARE_SingleCompare16ValueSet( uint16_t value )
{   
    CCP5RAL = value;
}


void SCCP5_COMPARE_DualCompareValueSet( uint16_t priVal, uint16_t secVal )
{

    CCP5RAL = priVal;

    CCP5RBL = secVal;
}

void SCCP5_COMPARE_DualEdgeBufferedConfig( uint16_t priVal, uint16_t secVal )
{

    CCP5RAL = priVal;

    CCP5RBL = secVal;
}

void SCCP5_COMPARE_CenterAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP5RAL = priVal;

    CCP5RBL = secVal;
}

void SCCP5_COMPARE_EdgeAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP5RAL = priVal;

    CCP5RBL = secVal;
}

void SCCP5_COMPARE_VariableFrequencyPulseConfig( uint16_t priVal )
{
    CCP5RAL = priVal;
}

bool SCCP5_COMPARE_IsCompareCycleComplete( void )
{
    return(IFS2bits.CCP5IF);
}

bool SCCP5_COMPARE_TriggerStatusGet( void )
{
    return( CCP5STATLbits.TRIG );
    
}

void SCCP5_COMPARE_TriggerStatusSet( void )
{
    CCP5STATLbits.TRSET = 1;
}

void SCCP5_COMPARE_TriggerStatusClear( void )
{
    /* Clears the trigger status */
    CCP5STATLbits.TRCLR = 0;
}

bool SCCP5_COMPARE_SingleCompareStatusGet( void )
{
    return( CCP5STATLbits.SCEVT );
}

void SCCP5_COMPARE_SingleCompareStatusClear( void )
{
    /* Clears the trigger status */
    CCP5STATLbits.SCEVT = 0;
    
}
/**
 End of File
*/
