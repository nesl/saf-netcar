#include <sos.h>

mod_header_ptr rats_get_header();
mod_header_ptr loader_get_header();
mod_header_ptr accel_sensor_get_header();
mod_header_ptr accel_test_app_get_header();
mod_header_ptr saf_get_header();
mod_header_ptr nic_get_header();

void sos_start(void) {
  ker_register_module(loader_get_header());
  ker_register_module(nic_get_header());
  ker_register_module(rats_get_header());
  ker_register_module(accel_sensor_get_header());
  ker_register_module(accel_test_app_get_header());
  ker_register_module(saf_get_header());
}
