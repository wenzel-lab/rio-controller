/**
  SCCP6 Generated Driver File 

  @Company
    Microchip Technology Inc.

  @File Name
    sccp6.c

  @Summary
    This is the generated driver implementation file for the SCCP6 driver using PIC24 / dsPIC33 / PIC32MM MCUs

  @Description
    This header file provides implementations for driver APIs for SCCP6. 
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

#include "sccp6_compare.h"

/** OC Mode.

  @Summary
    Defines the OC Mode.

  @Description
    This data type defines the OC Mode of operation.

*/

static uint16_t         gSCCP6Mode;

/**
  Section: Driver Interface
*/


void SCCP6_COMPARE_Initialize (void)
{
    // CCPON enabled; MOD Dual Edge Compare, Buffered(PWM); CCSEL disabled; CCPSIDL disabled; TMR32 16 Bit; CCPSLP disabled; TMRPS 1:64; CLKSEL FOSC/2; TMRSYNC disabled; 
    CCP6CON1L = (0x80C5 & 0x7FFF); //Disabling CCPON bit
    //RTRGEN disabled; ALTSYNC disabled; ONESHOT disabled; TRIGEN disabled; IOPS Each Time Base Period Match; SYNC None; OPSRC Timer Interrupt Event; 
    CCP6CON1H = 0x00;
    //ASDGM disabled; SSDG disabled; ASDG 0; PWMRSEN disabled; 
    CCP6CON2L = 0x00;
    //ICGSM Level-Sensitive mode; ICSEL IC6; AUXOUT Disabled; OCAEN enabled; OENSYNC disabled; 
    CCP6CON2H = 0x100;
    //OETRIG disabled; OSCNT None; POLACE disabled; PSSACE Tri-state; 
    CCP6CON3H = 0x00;
    //ICDIS disabled; SCEVT disabled; TRSET disabled; ICOV disabled; ASEVT disabled; TRIG disabled; ICGARM disabled; TRCLR disabled; 
    CCP6STATL = 0x00;
    //TMR 0; 
    CCP6TMRL = 0x00;
    //TMR 0; 
    CCP6TMRH = 0x00;
    //PR 32767; 
    CCP6PRL = 0x7FFF;
    //PR 0; 
    CCP6PRH = 0x00;
    //CMP 0; 
    CCP6RAL = 0x00;
    //CMP 0; 
    CCP6RBL = 0x00;
    //BUF 0; 
    CCP6BUFL = 0x00;
    //BUF 0; 
    CCP6BUFH = 0x00;

    CCP6CON1Lbits.CCPON = 0x1; //Enabling CCP

    gSCCP6Mode = CCP6CON1Lbits.MOD;

}

void __attribute__ ((weak)) SCCP6_COMPARE_CallBack(void)
{
    // Add your custom callback code here
}

void SCCP6_COMPARE_Tasks( void )
{
    if(IFS2bits.CCP6IF)
    {
		// SCCP6 COMPARE callback function 
		SCCP6_COMPARE_CallBack();
		
        IFS2bits.CCP6IF = 0;
    }
}

void __attribute__ ((weak)) SCCP6_COMPARE_TimerCallBack(void)
{
    // Add your custom callback code here
}


void SCCP6_COMPARE_TimerTasks( void )
{
    if(IFS2bits.CCT6IF)
    {
		// SCCP6 COMPARE Timer callback function 
		SCCP6_COMPARE_TimerCallBack();
	
        IFS2bits.CCT6IF = 0;
    }
}

void SCCP6_COMPARE_Start( void )
{
    /* Start the Timer */
    CCP6CON1Lbits.CCPON = true;
}

void SCCP6_COMPARE_Stop( void )
{
    /* Start the Timer */
    CCP6CON1Lbits.CCPON = false;
}

void SCCP6_COMPARE_SingleCompare16ValueSet( uint16_t value )
{   
    CCP6RAL = value;
}


void SCCP6_COMPARE_DualCompareValueSet( uint16_t priVal, uint16_t secVal )
{

    CCP6RAL = priVal;

    CCP6RBL = secVal;
}

void SCCP6_COMPARE_DualEdgeBufferedConfig( uint16_t priVal, uint16_t secVal )
{

    CCP6RAL = priVal;

    CCP6RBL = secVal;
}

void SCCP6_COMPARE_CenterAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP6RAL = priVal;

    CCP6RBL = secVal;
}

void SCCP6_COMPARE_EdgeAlignedPWMConfig( uint16_t priVal, uint16_t secVal )
{

    CCP6RAL = priVal;

    CCP6RBL = secVal;
}

void SCCP6_COMPARE_VariableFrequencyPulseConfig( uint16_t priVal )
{
    CCP6RAL = priVal;
}

bool SCCP6_COMPARE_IsCompareCycleComplete( void )
{
    return(IFS2bits.CCP6IF);
}

bool SCCP6_COMPARE_TriggerStatusGet( void )
{
    return( CCP6STATLbits.TRIG );
    
}

void SCCP6_COMPARE_TriggerStatusSet( void )
{
    CCP6STATLbits.TRSET = 1;
}

void SCCP6_COMPARE_TriggerStatusClear( void )
{
    /* Clears the trigger status */
    CCP6STATLbits.TRCLR = 0;
}

bool SCCP6_COMPARE_SingleCompareStatusGet( void )
{
    return( CCP6STATLbits.SCEVT );
}

void SCCP6_COMPARE_SingleCompareStatusClear( void )
{
    /* Clears the trigger status */
    CCP6STATLbits.SCEVT = 0;
    
}
/**
 End of File
*/
