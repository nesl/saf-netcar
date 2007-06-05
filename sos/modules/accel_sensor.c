/* -*- Mode: C; tab-width:2 -*- */
/* ex: set ts=2 shiftwidth=2 softtabstop=2 cindent: */

#include <module.h>
#include <sys_module.h>
#include <stdio.h>
#include <sensor.h>

#include <mts310sb.h> 

/**
 * private conguration options for this driver. This is used to differenciate
 * the calls to the ADC and sensor registration system.
 */
#define ACCEL_0_SENSOR_ID (0)
#define ACCEL_1_SENSOR_ID (1<<6)

typedef struct accel_sensor_state {
	uint8_t accel_0_state;
	uint8_t accel_1_state;
  uint16_t accel_0_value;
  uint16_t accel_1_value;
	uint8_t options;
	uint8_t state;
  FILE* fp;
} accel_sensor_state_t;


// function registered with kernel sensor component
static int8_t accel_control(func_cb_ptr cb, uint8_t cmd, void *data);
// data ready callback registered with adc driver
int8_t accel_data_ready_cb(func_cb_ptr cb, uint8_t port, uint16_t value, uint8_t flags);

static int8_t accel_msg_handler(void *state, Message *msg);

static const mod_header_t mod_header SOS_MODULE_HEADER = {
  mod_id : ACCEL_SENSOR_PID,
  state_size : sizeof(accel_sensor_state_t),
  num_timers : 0,
  num_sub_func : 0,
  num_prov_func : 2,
	platform_type : HW_TYPE,
	processor_type : MCU_TYPE,
	code_id : ehtons(ACCEL_SENSOR_PID),
  module_handler : accel_msg_handler,
	funct : {
		{accel_control, "cCw2", ACCEL_SENSOR_PID, SENSOR_CONTROL_FID},
		{accel_data_ready_cb, "cCS3", ACCEL_SENSOR_PID, SENSOR_DATA_READY_FID},
	},
};


/**
 * adc call back
 * not a one to one mapping so not SOS_CALL
 */
int8_t accel_data_ready_cb(func_cb_ptr cb, uint8_t port, uint16_t value, uint8_t flags) {

	// post data ready message here
	switch(port) {
		case MTS310_ACCEL_0_SID:
			ker_sensor_data_ready(MTS310_ACCEL_0_SID, value, flags);
			break;
		case MTS310_ACCEL_1_SID:
			ker_sensor_data_ready(MTS310_ACCEL_1_SID, value, flags);
			break;
		default:
			return -EINVAL;
	}
	return SOS_OK;
}


static int8_t accel_control(func_cb_ptr cb, uint8_t cmd, void* data) {\

  int n, a0, a1;
	//int tmp;
	//int tmp2;
  float t;
	uint8_t ctx = *(uint8_t*)data;
  accel_sensor_state_t* s = (accel_sensor_state_t*)ker_get_module_state(ACCEL_SENSOR_PID);
	
	switch (cmd) {
		case SENSOR_GET_DATA_CMD:
      // get ready to read accel sensor
			switch(ctx & 0xC0) {
				case ACCEL_0_SENSOR_ID:
          // read a new line from the file
					n = fscanf(s->fp, "%f\t%d\t%d\t\n", &t, &a0, &a1);
          //n = fscanf(s->fp, "%f\t%d\t%d\t%d\t%d\n", &t, &a0, &a1, &tmp, &tmp2);
					//n = fscanf(s->fp, "%f\t%d\t%d\t%d\n", &t, &a0, &a1, &tmp);
					if (n == EOF)
						exit(1);
					s->accel_0_value = (uint16_t)a0;
          s->accel_1_value = (uint16_t)a1;
          DEBUG("read %f %d %d\n", t, s->accel_0_value, s->accel_1_value);
          return ker_sensor_data_ready(MTS310_ACCEL_0_SID, s->accel_0_value, 0);
				case ACCEL_1_SENSOR_ID:
          return ker_sensor_data_ready(MTS310_ACCEL_1_SID, s->accel_1_value, 0);
				default:
					return -EINVAL;
			}
			break;

		case SENSOR_ENABLE_CMD:
			break;

		case SENSOR_DISABLE_CMD:
			break;

		case SENSOR_CONFIG_CMD:
			// no configuation
			if (data != NULL) {
				sys_free(data);
			}
			break;

		default:
			return -EINVAL;
	}
	return SOS_OK;
}

char *sineLogStr = "../logs/sinlogs/1-1.log";
char *logStr = "../logs/1.log";
char *sampleStr = "../sampledata.log";
int8_t accel_msg_handler(void *state, Message *msg)
{
	
	accel_sensor_state_t *s = (accel_sensor_state_t*)state;
  
	switch (msg->type) {

		case MSG_INIT:
      DEBUG("ACCEL_SENSOR: init\n");
      // register with kernel sensor interface
			s->accel_0_state = ACCEL_0_SENSOR_ID;
			ker_sensor_register(ACCEL_SENSOR_PID, MTS310_ACCEL_0_SID, SENSOR_CONTROL_FID, (void*)(&s->accel_0_state));
			s->accel_1_state = ACCEL_1_SENSOR_ID;
			ker_sensor_register(ACCEL_SENSOR_PID, MTS310_ACCEL_1_SID, SENSOR_CONTROL_FID, (void*)(&s->accel_1_state));
      s->fp = fopen(sineLogStr, "r");
      if(s->fp == NULL){
        DEBUG("couldn't open file ../sampledata.log!!!");
        exit(0);
      }
			break;

		case MSG_FINAL:
			// shutdown sensor
			// unregister sensor
			ker_sensor_deregister(ACCEL_SENSOR_PID, MTS310_ACCEL_0_SID);
			ker_sensor_deregister(ACCEL_SENSOR_PID, MTS310_ACCEL_1_SID);
      fclose(s->fp);
			break;

		default:
			return -EINVAL;
			break;
	}
	return SOS_OK;
}


#ifndef _MODULE_
mod_header_ptr accel_sensor_get_header() {
	return sos_get_header_address(mod_header);
}
#endif

