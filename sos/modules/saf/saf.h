#ifndef SAF_HEADER
#define SAF_HEADER

#include <module.h>
#include <sys_module.h>
#include <string.h>
#include <math.h>
#include "../accel_sampler.h"

#define SAF_PID DFLT_APP_ID1

#if SOS_SIM
#define TIMING_INTERVAL .0195 
#else
#define TIMING_INTERVAL .0195 
#endif
  
#define NUM_LINEAR_COEF 2
#define NUM_STATIC_COEF 6 
#define NUM_NOISE_COEF 1

#define MSG_ERROR_DATA (MOD_MSG_START +2)
#define MSG_LINE_DATA (MOD_MSG_START +3)
#define MSG_NEW_CONSTANT (MOD_MSG_START +4) 
#define HIGH_EPSILON 25 
#define LOW_EPSILON 12 
#define PERCENT_VALID 80
#define PROB_ERROR .025
#define NUM_DIM 2

typedef struct {
   uint32_t seq_nr;
   uint16_t accel0[SAMPLES_PER_MSG];
   uint16_t accel1[SAMPLES_PER_MSG];
   float    linear_coef[NUM_DIM][NUM_LINEAR_COEF];
   float    static_coef[NUM_DIM][NUM_STATIC_COEF];
   float    noise_coef[NUM_DIM];
} line_fit_msg_t;

typedef struct {
  uint32_t seq_nr;
  float    prediction_error[NUM_DIM][SAMPLES_PER_MSG];
} line_error_msg_t;

typedef struct {
  uint32_t seq_nr;
  uint16_t accel[NUM_DIM];
  float    prediction_error[NUM_DIM];
  uint16_t      is_real_msg;
} single_error_msg_t;

#endif
