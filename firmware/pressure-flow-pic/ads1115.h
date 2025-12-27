#ifndef ADS1115_H_
#define ADS1115_H_

/************************************************************************/
/* ADS1115 ADDR															*/
/************************************************************************/

#define ADS1115_ADDR_GND (0b1001000)
#define ADS1115_ADDR_VDD (0b1001001)
#define ADS1115_ADDR_SDA (0b1001010)
#define ADS1115_ADDR_SCL (0b1001011)

/************************************************************************/
/* ADS1115 REGISTER														*/
/************************************************************************/

#define ADS1115_REG_CONVERSION	0x00
#define ADS1115_REG_CONFIG		0x01
#define ADS1115_REG_LO_THRESH	0x02
#define ADS1115_REG_HI_THRESH	0x03

/************************************************************************/
/* ADS1115 CONFIG REGISTER BIT NR										*/
/************************************************************************/

#define ADS1115_OS 			15
#define ADS1115_IMUX2 		14
#define ADS1115_IMUX1 		13
#define ADS1115_IMUX0 		12
#define ADS1115_PGA2 		11
#define ADS1115_PGA1 		10
#define ADS1115_PGA0 		9
#define ADS1115_MODE 		8
#define ADS1115_DR2 		7
#define ADS1115_DR1 		6
#define ADS1115_DR0 		5
#define ADS1115_COMP_MODE 	4
#define ADS1115_COMP_POL 	3
#define ADS1115_COMP_LAT 	2
#define ADS1115_COMP_QUE1 	1
#define ADS1115_COMP_QUE0	0

/************************************************************************/
/* ADS1115 CONFIG REGISTER BITS											*/
/************************************************************************/

// Bit 0,1
#define ADS1115_COMP_QUE_CON1			(0x0000)
#define ADS1115_COMP_QUE_CON2			(0x0001)
#define ADS1115_COMP_QUE_CON4			(0x0002)
#define ADS1115_COMP_QUE_DIS			(0x0003)

// Bit 2
#define ADS1115_COMP_LAT_NonLatching	(0x0000)
#define ADS1115_COMP_LAT_Latching		(0x0004)

// Bit 3
#define ADS1115_COMP_POL_3_ACTIVELOW	(0x0000)
#define ADS1115_COMP_POL_3_ACTIVEHIGH	(0x0008)

// Bit 4
#define ADS1115_COMP_MODE_TRADITIONAL	(0x0000)
#define ADS1115_COMP_MODE_WINDOWCOMP	(0x0010)

// Bit 5,6,7
#define ADS1115_DR_8SPS					(0x0000)
#define ADS1115_DR_16SPS				(0x0020)
#define ADS1115_DR_32SPS				(0x0040)
#define ADS1115_DR_64SPS				(0x0060)
#define ADS1115_DR_128SPS				(0x0080)
#define ADS1115_DR_250SPS				(0x00A0)
#define ADS1115_DR_475SPS				(0x00C0)
#define ADS1115_DR_860SPS				(0x00E0)

// Bit 8
#define ADS1115_MODE_CONTINUOUS			(0x0000)
#define ADS1115_MODE_SINGLE				(0x0100) 

// Bit 9,10,11
#define ADS1115_PGA_6_144				(0x0000)
#define ADS1115_PGA_4_096				(0x0200)
#define ADS1115_PGA_2_048				(0x0400)
#define ADS1115_PGA_1_024				(0x0600)
#define ADS1115_PGA_0_512				(0x0800)
#define ADS1115_PGA_0_256				(0x0A00)
#define ADS1115_PGA_0_256_2				(0x0C00)
#define ADS1115_PGA_0_256_3				(0x0E00)

// Bit 12,13,14
#define ADS1115_MUX_AIN0_AIN1			(0x0000)
#define ADS1115_MUX_AIN0_AIN3			(0x1000)
#define ADS1115_MUX_AIN1_AIN3			(0x2000)
#define ADS1115_MUX_AIN2_AIN3			(0x3000)
#define ADS1115_MUX_AIN0_GND			(0x4000)
#define ADS1115_MUX_AIN1_GND			(0x5000)
#define ADS1115_MUX_AIN2_GND			(0x6000)
#define ADS1115_MUX_AIN3_GND			(0x7000)

// Bit 15
#define ADS1115_OS_OFF					(0x0000)
#define ADS1115_OS_SINGLE				(0x8000)

/************************************************************************/
/* ADS1115 ENUMS				                                        */
/************************************************************************/

typedef enum
{
	FSR_6_144		= ADS1115_PGA_6_144,
	FSR_4_096       = ADS1115_PGA_4_096,
	FSR_2_048       = ADS1115_PGA_2_048,
	FSR_1_024       = ADS1115_PGA_1_024,
	FSR_0_512       = ADS1115_PGA_0_512,
	FSR_0_256		= ADS1115_PGA_0_256,
	FSR_0_256_1     = ADS1115_PGA_0_256_2,
	FSR_0_256_2     = ADS1115_PGA_0_256_3
} ads1115_fsr_gain;

typedef enum
{
	DATARATE_8SPS		= ADS1115_DR_8SPS,
	DATARATE_16SPS		= ADS1115_DR_16SPS,
	DATARATE_32SPS		= ADS1115_DR_32SPS,
	DATARATE_64SPS		= ADS1115_DR_64SPS,
	DATARATE_128SPS		= ADS1115_DR_128SPS,
	DATARATE_250SPS		= ADS1115_DR_250SPS,
	DATARATE_475SPS		= ADS1115_DR_475SPS,
	DATARATE_860SPS		= ADS1115_DR_860SPS
} ads1115_datarate;

typedef struct
{
    uint8_t write_data[3];
    volatile uint8_t read_data[2];
    I2C2_TRANSACTION_REQUEST_BLOCK trBlocks[3];
    uint16_t start_time;
    int8_t channel;
//    bool reading;
    volatile I2C2_MESSAGE_STATUS status;
} ads1115_task_t;

/************************************************************************/
/* ADS1115 FUNCTIONS			                                        */
/************************************************************************/

err ads1115_set_ready_pin( uint8_t addr );
void ads1115_read_adc_start( uint8_t addr, int8_t read_channel, int8_t start_channel, ads1115_datarate dr, ads1115_fsr_gain gain, ads1115_task_t *task );
int8_t ads1115_read_adc_return( uint16_t *value, int8_t *channel, ads1115_task_t *task );
err ads1115_start_single( uint8_t addr, uint8_t channel, ads1115_datarate dr, ads1115_fsr_gain gain );
err ads1115_get_result( uint8_t addr, uint16_t *value  );

#endif /* ADS1115_H_ */