#ifndef ACCEL_SAMP_HEADER
#define ACCEL_SAMP_HEADER
  
#include <module.h>
#include <sys_module.h>
#include <string.h>
#include <rats/rats.h>

#define LED_DEBUG
#include <led_dbg.h>
  
#include <mts310sb.h>

#define ACCEL_TEST_APP_TID 0
#ifdef SOS_SIM
#define ACCEL_TEST_APP_INTERVAL 20
#else
#define ACCEL_TEST_APP_INTERVAL 20
#endif

#define ACCEL_TEST_PID DFLT_APP_ID0

#define SAMPLES_PER_MSG 30 

#define MSG_ACCEL_DATA (MOD_MSG_START + 1)
#define ROOT_ID 0
//the following message is used for the RATS reply
#define MSG_REPLY (MOD_MSG_START + 0)

// the following messages are used for sending only one set of acceleration values
#define MSG_CHANGE_TO_SINGLE (MOD_MSG_START +5)
#define MSG_CHANGE_TO_MULT (MOD_MSG_START +6)

typedef struct {
  uint32_t seq_nr;
  uint16_t accel0[SAMPLES_PER_MSG];
  uint16_t accel1[SAMPLES_PER_MSG];
} accel_msg_t;

typedef struct {
  uint32_t seq_nr;
  uint16_t accel[2];
} single_accel_msg_t;

#endif

//
