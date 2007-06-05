/* -*- Mode: C; tab-width:2 -*- */
/* ex: set ts=2 shiftwidth=2 softtabstop=2 cindent: */

#include "saf.h"
#include <math.h>
#include "../accel_sampler.h"

//#if SOS_SIM
//#define TIME_CONV 1.0
//#else
#define TIME_CONV 115200.0
//#endif

enum {
  SAF_INIT=0,
  SAF_LEARN,
  SAF_COMPARE,
	SAF_MONITOR,
};

enum {
  X_DIM = 0,
  Y_DIM,
};

typedef struct{
  uint8_t pid;          //process ID
  uint8_t state;        //state of learning or comparing
  uint8_t num_allowed_errors;
  float epsilon[NUM_DIM];
	float low_epsilon[NUM_DIM];
  uint32_t seq_nr;
  float linear_coef[NUM_DIM][NUM_LINEAR_COEF];
  float static_coef[NUM_DIM][NUM_STATIC_COEF];
  float noise_coef[NUM_DIM];
  float last_readings[NUM_DIM][NUM_STATIC_COEF];
  uint8_t num_errors[NUM_DIM];
	uint8_t is_previous_wrong[NUM_DIM];
	uint8_t error_check_count;
} app_state_t;

typedef struct{
  uint8_t number_errors;
  float epsilon;
} constant_change_t;

typedef double Saf_Type;
typedef Saf_Type** Matrix;

static int8_t saf_msg_handler(void *state, Message *msg);

static int least_squares(uint16_t *readings, Matrix param, uint8_t num_readings, uint8_t num_coef,float *coef);

static mod_header_t mod_header SOS_MODULE_HEADER = {
  .mod_id         =SAF_PID,
  .state_size     =sizeof(app_state_t),
  .num_timers     =1,
  .num_sub_func   =0,
  .num_prov_func  =0,
  .platform_type  = HW_TYPE,
  .processor_type = MCU_TYPE,
  .code_id        = ehtons(SAF_PID),
  .module_handler = saf_msg_handler,
};

Matrix inline
NewMatrix(cols, rows)
uint8_t cols,rows;
{
    uint8_t i;
    Matrix newM; 
    newM = (Saf_Type **)sys_malloc(rows * sizeof(Saf_Type *));
		if (!newM){
			//LED_DBG(LED_GREEN_TOGGLE);
			return NULL;
		}
    for(i = 0; i < rows; i++){
        newM[i] = (Saf_Type *) sys_malloc(cols * sizeof(Saf_Type));
				if (!newM[i]){
					//LED_DBG(LED_GREEN_TOGGLE);
					return NULL;
				}
		}
    return newM;
}

void inline FreeMatrix(mat, rows) 
Matrix mat;
uint8_t rows;
{
    uint8_t i;
    for(i = 0; i < rows; i++)
        sys_free(mat[i]);
    sys_free(mat);
}

static int compute_coef_for_one_dim(void *data,  void *state, uint8_t dimension){

  uint16_t *s_values;
  float *s_linear_coef;
  float *s_static_coef;
  float *s_noise_coef;
  uint8_t i,j;
  float a, b;
  float start_time;
  float time;
  float mean, variance; 
	float pred;
  Matrix parameters;
  float error;

  app_state_t *s = (app_state_t *) state;
  accel_msg_t *d = (accel_msg_t *) data;

  switch(dimension){
    case X_DIM:
      s_values = d->accel0;
      s_linear_coef = s->linear_coef[X_DIM];
      s_static_coef = s->static_coef[X_DIM];
      s_noise_coef = &s->noise_coef[X_DIM];
      break;
    case Y_DIM:
      s_values = d->accel1;
      s_linear_coef = s->linear_coef[Y_DIM];
      s_static_coef = s->static_coef[Y_DIM];
      s_noise_coef = &s->noise_coef[Y_DIM];
      break;
    default:
      return 0;
    }

	/* FIXME i think we need to round the start time value to 4 digits past the decimal */
  start_time = d->seq_nr/TIME_CONV - (SAMPLES_PER_MSG - 1) * TIMING_INTERVAL;
	//start_time *= 10000;
	//DEBUG("starttime, before conv: %f\n", start_time);
	//start_time = ceil(start_time);
	//DEBUG("start time before divid: %f\n", start_time);
	//start_time /= 10000;
	//DEBUG("start timme: %f\n", start_time);
  
  // compute linear  trend coeficients
  parameters = NewMatrix(SAMPLES_PER_MSG, 1);
   
	if (!parameters){
		LED_DBG(LED_RED_TOGGLE);
		return 0;
	}

  time = start_time;
  for (i = 0; i<SAMPLES_PER_MSG;i++){
		//DEBUG("time: %f\n", time);

    parameters[0][i] = time;
    time += TIMING_INTERVAL;
    }

  if (!least_squares(s_values, parameters, SAMPLES_PER_MSG, NUM_LINEAR_COEF, s_linear_coef)){
    LED_DBG(LED_RED_TOGGLE);
    return 0;
  }

	DEBUG("a: %f\tb: %f\n", s_linear_coef[0], s_linear_coef[1]);
  FreeMatrix(parameters, 1);
  
  // compute static coeficients
  parameters = NewMatrix(SAMPLES_PER_MSG, 1);
 
	if (!parameters){
		LED_DBG(LED_RED_TOGGLE);
		return 0;
	}

  a = s_linear_coef[0];
  b = s_linear_coef[1];
  time = start_time;
  for (i = 0; i < SAMPLES_PER_MSG;i++){
    error =  (a * time + b) - s_values[i];
    if (error < 0.0)
      error *= -1;
		if (error < 1.0)
			error = 0;
    parameters[0][i] = error;
    time += TIMING_INTERVAL;
    }
  if (!least_squares(NULL, parameters, SAMPLES_PER_MSG, NUM_STATIC_COEF, s_static_coef)) {
		LED_DBG(LED_RED_TOGGLE);
    return 0;
	}

  // compute noise coefficient
	mean = 0;
	time = start_time;
  for (i = NUM_STATIC_COEF; i< SAMPLES_PER_MSG; i++){
		pred = a*(time + NUM_STATIC_COEF*TIMING_INTERVAL) + b;
		error = 0;
    for (j = 0; j < NUM_STATIC_COEF; j++)
			error += s_static_coef[j] *( s_values[i - NUM_STATIC_COEF+j] - (a*(time+j*TIMING_INTERVAL) + b));
    pred += error;
		error = pred - s_values[i];
		//if (error < 0.0)
		//	error *= -1;
		parameters[0][i] = error;
		mean += error;
		time += TIMING_INTERVAL;
	}

  mean /= (float) (SAMPLES_PER_MSG-NUM_STATIC_COEF);

	//DEBUG("mean: %f\n", mean);
  variance =0;
	time = start_time;
  for(i = NUM_STATIC_COEF; i< SAMPLES_PER_MSG;i++){
    variance +=  (parameters[0][i] - mean) * (parameters[0][i] - mean);
	}

  variance /= (float) (SAMPLES_PER_MSG-NUM_STATIC_COEF);

	//DEBUG("variance: %f\n", variance);

  FreeMatrix(parameters, 1);
//	DEBUG("standard deviation: %f\n", sqrt(variance));
  *s_noise_coef = sqrt(variance);

	if (*s_noise_coef < 1.0)
		*s_noise_coef = 1;

	//DEBUG("noise: %f\n",*s_noise_coef);
	return 1;
}

static float compute_prediction_for_one_dim(void *state, uint8_t dim, uint32_t seq_nr){
	app_state_t *s = (app_state_t *) state;
	int j;
	float a, b;
	float *alpha;
	float *last_readings;
	float auto_regression;
  float prediction;
  float time;
  float noise;

  switch(dim){
		case X_DIM:
		  a = s->linear_coef[X_DIM][0];
			b = s->linear_coef[X_DIM][1];
			alpha = s->static_coef[X_DIM];
			noise = s->noise_coef[X_DIM];
			last_readings = s->last_readings[X_DIM];
			break;
		case Y_DIM:
			a = s->linear_coef[Y_DIM][0];
			b = s->linear_coef[Y_DIM][1];
			alpha = s->static_coef[Y_DIM];
			noise = s->noise_coef[Y_DIM];
			last_readings = s->last_readings[Y_DIM];
			break;
		default:
			return 0;
	}

  time = seq_nr/TIME_CONV;
  //time *= 10000;
  //time = ceil(time);
  //time /= 10000;

	DEBUG("a: %f\n", a);
  prediction = a*time + b;

 	time = time - NUM_STATIC_COEF*TIMING_INTERVAL;
  auto_regression = 0;
  for (j = 0; j < NUM_STATIC_COEF; j++)
    auto_regression += alpha[j] *  (last_readings[j] - (a *(time + j*TIMING_INTERVAL) + b));
  prediction += auto_regression;
						
	/* add the white noise, i'm totaly guessing on this part */
	//prediction +=  0*noise * normal_random();	

//	DEBUG("prediction : %f\n", prediction);
//	DEBUG("noise: %f\n", noise*normal_random());
	DEBUG("prediction: %f\n", prediction);
  return prediction;
}
			
	
static int8_t saf_msg_handler(void *state, Message *msg){
  uint8_t i, j;
  app_state_t *s = (app_state_t *) state;
  accel_msg_t *data;
  line_fit_msg_t *data_msg;
  constant_change_t *change_msg;

  switch (msg->type){
    case MSG_INIT:
      s->state = SAF_LEARN;
      s->seq_nr = 0;
      s->pid = msg->did;
      //s->epsilon = HIGH_EPSILON;
			//s->low_epsilon = LOW_EPSILON;
      s->num_allowed_errors = SAMPLES_PER_MSG * (100 - PERCENT_VALID) / 100; 
      break;

    case MSG_FINAL:
      //so far do nothing
      break;
    
    case MSG_NEW_CONSTANT:
      change_msg = (constant_change_t *) msg->data;
      //s->epsilon = change_msg->epsilon;
      s->num_allowed_errors = change_msg->number_errors;
      break;

    case MSG_DATA_READY: 
      
      switch (s->state){
        case SAF_INIT:
          s->state = SAF_LEARN;
          break;

        case SAF_COMPARE:
			  {
					uint8_t i,j;
					uint8_t is_real_msg;
          float prediction[NUM_DIM];
					float error[NUM_DIM];
          single_accel_msg_t *single_data_msg = (single_accel_msg_t *) msg->data;
          single_error_msg_t *single_error_msg;

				  prediction[X_DIM] = compute_prediction_for_one_dim(s, X_DIM, single_data_msg->seq_nr);
					prediction[Y_DIM] = compute_prediction_for_one_dim(s, Y_DIM, single_data_msg->seq_nr);

					/* check for errors */
					is_real_msg = 0;
					s->error_check_count++;
					for(i =0; i<NUM_DIM;i++){
						error[i] = single_data_msg->accel[i] - prediction[i];
						if (error[i] < 0.0)
							error[i] *= -1;
						if (error[i] < 1.0)
							error[i] = 0;
						if (s->low_epsilon[i] < error[i] && error[i] < s->epsilon[i]){
							is_real_msg = 2;
							s->num_errors[i]++;
						} else if (error[i] > s->epsilon[i] && error[i] < 1000){
							if (s->is_previous_wrong[i])
								s->num_errors[i]++;
							else
								s->is_previous_wrong[i] = 1;
							is_real_msg = 1;
							//s->num_errors[i]++;
						}
					}

					/* reset the monitor window, change modes if too many errors exist */
					if (s->error_check_count == SAMPLES_PER_MSG){
						if (s->num_allowed_errors < s->num_errors[X_DIM] || s->num_allowed_errors < s->num_errors[Y_DIM]){
              sys_post_value(ACCEL_TEST_PID ,MSG_CHANGE_TO_MULT, 0, 0);
							s->state = SAF_LEARN;
						}
						else{
							s->error_check_count = 0;
							for (i = 0; i < NUM_DIM; i++)
								s->num_errors[i] = 0;
						}
					}

					/* record the last reading in the queue */
					for(i = 0; i< NUM_DIM;i++){
						for (j = 0; j < NUM_STATIC_COEF-1; j++)
								s->last_readings[i][j] = s->last_readings[i][j+1];
						if (is_real_msg)
							s->last_readings[i][NUM_STATIC_COEF-1] = single_data_msg->accel[i];
						else
							s->last_readings[i][NUM_STATIC_COEF-1] = prediction[i];
					}

				  single_error_msg 	= (single_error_msg_t *) sys_malloc(sizeof(single_error_msg_t));

					if ( single_error_msg){
						single_error_msg->seq_nr = single_data_msg->seq_nr;
						for (i = 0; i < NUM_DIM; i++)
							single_error_msg->prediction_error[i] = error[i];
						single_error_msg->is_real_msg = is_real_msg;

						memcpy((void*)single_error_msg->accel, (void*)single_data_msg->accel, NUM_DIM*sizeof(uint16_t));

						DEBUG("Sending single error mesage at time %d\n", single_error_msg->seq_nr);

						if(ker_id() == 0){
									LED_DBG(LED_YELLOW_TOGGLE);
									sys_post_uart ( s->pid,
											MSG_ERROR_DATA,
											sizeof(single_error_msg_t),
											single_error_msg,
								      SOS_MSG_RELEASE,
								      BCAST_ADDRESS);
						} else {
									//LED_DBG(LED_GREEN_TOGGLE);
									sys_post_net ( s->pid,
											MSG_ERROR_DATA,
											sizeof(single_error_msg_t),
											single_error_msg,
											SOS_MSG_RELEASE,
                      BCAST_ADDRESS);
						}
				  } else
            LED_DBG(LED_RED_TOGGLE);
        break;
				}
				
        case SAF_LEARN:   
          data = (accel_msg_t *) msg->data;

					DEBUG("computing coeficients\n");
			
					if (!compute_coef_for_one_dim(data, s, X_DIM))
						break;
          if (!compute_coef_for_one_dim(data, s, Y_DIM))
						break;
     
          // send the data 
					DEBUG("creating line msg\n");
          data_msg = (line_fit_msg_t*) sys_malloc(sizeof(line_fit_msg_t));

					DEBUG("SENDING LINE packet with time %d\n", data->seq_nr);
          if ( data_msg ) {
            data_msg->seq_nr = data->seq_nr;

            memcpy((void*)data_msg->accel0, (void*)data->accel0, SAMPLES_PER_MSG*sizeof(uint16_t));
            memcpy((void*)data_msg->accel1, (void*)data->accel1, SAMPLES_PER_MSG*sizeof(uint16_t));
            for (i = 0; i < NUM_DIM; i++){
              memcpy((void*)data_msg->linear_coef[i], (void*)s->linear_coef[i],NUM_LINEAR_COEF*sizeof(float));
              memcpy((void*)data_msg->static_coef[i], (void*)s->static_coef[i],NUM_STATIC_COEF*sizeof(float));
							data_msg->noise_coef[i] = s->noise_coef[i];
            }
            if(ker_id() == 0){
                 LED_DBG(LED_GREEN_TOGGLE);
                 sys_post_uart ( s->pid,
                          MSG_LINE_DATA,
                          sizeof(line_fit_msg_t),
                          data_msg,
                          SOS_MSG_RELEASE,
                          BCAST_ADDRESS);
            } else {
                 /* there seems to be an error here when transfering from a second node FIXME */
                 //LED_DBG(LED_GREEN_TOGGLE);
                 sys_post_net ( s->pid,
                         MSG_LINE_DATA,
                         sizeof(line_fit_msg_t),
                         data_msg,
                         SOS_MSG_RELEASE,
                         BCAST_ADDRESS);
            }
          } else
            LED_DBG(LED_RED_TOGGLE);

          s->state = SAF_COMPARE;

          // record the last 3 accel readings for each dimension
          for (i = SAMPLES_PER_MSG-NUM_STATIC_COEF, j = 0; i < SAMPLES_PER_MSG;i++, j++){
            s->last_readings[0][j] = data->accel0[i];
            s->last_readings[1][j] = data->accel1[i];
          }
					for(i = 0; i<NUM_DIM;i++){
						s->num_errors[i] = 0;
						s->is_previous_wrong[i] = 0;
						s->low_epsilon[i] = 1.2*s->noise_coef[i];
						s->epsilon[i] =  1 /sqrt(PROB_ERROR) * s->noise_coef[i];
					}
          s->error_check_count = 0;
					
          sys_post_value(ACCEL_TEST_PID ,MSG_CHANGE_TO_SINGLE, 0, 0); 
				  //DEBUG("changing read mode to single\n");
          break;
      }	
      break;
    default:
      break;
  }
  return SOS_OK;
}

Saf_Type
InvertMatrix(mat,actual_size)
Matrix mat;                     /* Holds the original and inverse */
int actual_size;        /* Actual size of matrix in use, (high_subscript+1)*/
{
    int i,j,k;
                                        /* Locations of pivot elements */
    int *pvt_i, *pvt_j;
    Saf_Type pvt_val;                     /* Value of current pivot element */
    Saf_Type hold;                        /* Temporary storage */
    Saf_Type determ;                      /* Determinant */

    determ = 1.0;

    pvt_i = (int *) sys_malloc(actual_size * sizeof(int));
    pvt_j = (int *) sys_malloc(actual_size * sizeof(int));

    for (k = 0; k < actual_size; k++)
    {
        /* Locate k'th pivot element */
        pvt_val = mat[k][k];            /* Initialize for search */
        pvt_i[k] = k;
        pvt_j[k] = k;
        for (i = k; i < actual_size; i++)
          for (j = k; j < actual_size; j++)

            if (fabs(mat[i][j]) > fabs(pvt_val))
            {
                pvt_i[k] = i;
                pvt_j[k] = j;
                pvt_val = mat[i][j];
            }
        /* Product of pivots, gives determinant when finished */
        determ *= pvt_val;
        if (determ == 0.0) {
         /* Matrix is singular (zero determinant). */
            sys_free(pvt_i);
            sys_free(pvt_j);
            return (0.0);
        }

        /* "Interchange" rows (with sign change stuff) */
        i = pvt_i[k];
        if (i != k)                     /* If rows are different */
          for (j = 0; j < actual_size; j++)
          {
            hold = -mat[k][j];
            mat[k][j] = mat[i][j];
            mat[i][j] = hold;
          }

        /* "Interchange" columns */
        j = pvt_j[k];
        if (j != k)                     /* If columns are different */
          for (i = 0; i < actual_size; i++)
          {
            hold = -mat[i][k];
            mat[i][k] = mat[i][j];
            mat[i][j] = hold;
          }
        /* Divide column by minus pivot value */
        for (i = 0; i < actual_size; i++)
          if (i != k)                   /* Don't touch the pivot entry */
            mat[i][k] /= ( -pvt_val) ;  /* (Tricky C syntax for division) */

        /* Reduce the matrix */
        for (i = 0; i < actual_size; i++)
        {
            hold = mat[i][k];
            for (j = 0; j < actual_size; j++)
              if ( i != k && j != k )   /* Don't touch pivot. */
                mat[i][j] += hold * mat[k][j];
        }

        /* Divide row by pivot */
        for (j = 0; j < actual_size; j++)
          if (j != k)                   /* Don't touch the pivot! */
            mat[k][j] /= pvt_val;

        /* Replace pivot by reciprocal (at last we can touch it). */
        mat[k][k] = 1.0/pvt_val;
    }

    /* That was most of the work, one final pass of row/column interchange */
    /* to finish */
    for (k = actual_size-2; k >= 0; k--)  /* Don't need to work with 1 by 1 */
                                        /* corner */
    {
        i = pvt_j[k];            /* Rows to swap correspond to pivot COLUMN */
        if (i != k)                     /* If rows are different */
          for(j = 0; j < actual_size; j++)
          {
            hold = mat[k][j];
            mat[k][j] = -mat[i][j];
            mat[i][j] = hold;
          }

        j = pvt_i[k];           /* Columns to swap correspond to pivot ROW */
        if (j != k)                     /* If columns are different */
          for (i = 0; i < actual_size; i++)
          {
            hold = mat[i][k];
            mat[i][k] = -mat[i][j];
            mat[i][j] = hold;
          }
    }

    sys_free(pvt_i);
    sys_free(pvt_j);
    return(determ);
}

static int least_squares(uint16_t *readings, Matrix param, uint8_t num_readings, uint8_t num_coef,float *coef){
  uint8_t i = 0;
  uint8_t j = 0;
  uint8_t k = 0;
  Saf_Type determ;
  Matrix param_t_param;
  Saf_Type *param_t_readings;
  Saf_Type  sum = 0;
  param_t_param = NewMatrix(num_coef, num_coef);

  param_t_readings = (Saf_Type *) sys_malloc(num_coef * sizeof(Saf_Type));

	if (!param_t_readings || !param_t_param){
		//LED_DBG(LED_GREEN_TOGGLE);
		return 0;
	}
 
  if (num_coef == NUM_LINEAR_COEF){
    // specific for linear coefficients to produce a 2 X 2 matrix
    float sum2 = 0;  
    sum = 0; 
    for (k = 0; k < num_readings;k++){
      sum += param[0][k] * param[0][k];
      sum2 += param[0][k];
      }

    param_t_param[0][0] = sum;
    param_t_param[0][1] = sum2;
    param_t_param[1][0] = sum2;
    param_t_param[1][1] = num_readings;
    
		DEBUG("param_t_param\nsum: %f\tsum2: %f\n", sum, sum2);

    sum = 0;
    sum2 = 0;
    for (k = 0; k< num_readings;k++){
      sum += param[0][k] * readings[k];
      sum2 += readings[k];
      }
    param_t_readings[0] = sum;
    param_t_readings[1] = sum2;

		DEBUG("param_t_readings\nsum: %f\tsum2%f\n", sum, sum2);
    }
  else if (num_coef == NUM_STATIC_COEF){
    // special case for static coef, with 3 coeficients
    for (i = 0; i < num_coef; i++){
      for (j = 0; j < num_coef; j++){
        sum = 0;
        for (k = num_coef; k< num_readings; k++)
          sum += param[0][k-NUM_STATIC_COEF+i] * param[0][k-NUM_STATIC_COEF+j];
        param_t_param[i][j] = sum;
        }
      }

    for (i = 0; i < num_coef; i++){
      sum = 0;
      for (k = num_coef; k < num_readings;k++)
        sum += param[0][k] * param[0][k-NUM_STATIC_COEF+i];
      param_t_readings[i] = sum;
      }
    }
  else {
    // general purpose for any number of coeficcients
    for (i = 0; i < num_coef; i++)
      for (j = 0; j < num_coef; j++){
        sum = 0;	
        for (k = 0; k < num_readings; k++)
          sum += param[i][k] * param[j][k];
        param_t_param[i][j] = sum;
       }
    
    for (i = 0; i < num_coef; i++){
      sum = 0;
      for (k = 0; k < num_readings; k++)
        sum += param[i][k] * ((float) readings[k]);
      param_t_readings[i] = sum;
      } 	
    }

  determ = InvertMatrix(param_t_param, num_coef);
  if (determ == 0){
		DEBUG("DETERM=0\n");
    for (i = 0; i< num_coef;i++)
      coef[i] = 0;
    sys_free(param_t_readings);
    FreeMatrix(param_t_param, num_coef);
    return 1;
  }

  for (i = 0; i< num_coef; i++)
  {
   sum =0;
   for (k = 0; k < num_coef;k++)
    sum += param_t_param[i][k] * param_t_readings[k];
   coef[i] = sum;
  }

  sys_free(param_t_readings);
  FreeMatrix(param_t_param, num_coef);

	return 1;
}

mod_header_ptr saf_get_header(){
  return sos_get_header_address(mod_header);
}
