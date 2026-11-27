#ifndef OPTIC_REVIEW_TEMPERATURE_H
#define OPTIC_REVIEW_TEMPERATURE_H

#include <stdint.h>

/* Decode a supported, ready module's temperature sample in degrees Celsius. */
double temperature_c(uint8_t msb, uint8_t lsb);

#endif
