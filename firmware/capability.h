#ifndef OPTIC_REVIEW_CAPABILITY_H
#define OPTIC_REVIEW_CAPABILITY_H

#include <stdbool.h>

enum sample_state { SAMPLE_UNAVAILABLE, SENSOR_UNSUPPORTED, SAMPLE_READY };

/* Inputs describe one observation. A retry supplies a fresh observation. */
enum sample_state sample_state_for(bool read_ok, bool supported, bool ready);

#endif
