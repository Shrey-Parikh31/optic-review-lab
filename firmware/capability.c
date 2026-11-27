#include "capability.h"

enum sample_state sample_state_for(bool read_ok, bool supported, bool ready)
{
    if (!read_ok)
        return SAMPLE_UNAVAILABLE;
    if (!supported)
        return SENSOR_UNSUPPORTED;
    return ready ? SAMPLE_READY : SAMPLE_UNAVAILABLE;
}
