#include "capability.h"
#include <assert.h>

int main(void)
{
    assert(sample_state_for(false, false, true) == SAMPLE_UNAVAILABLE);
    assert(sample_state_for(true, true, true) == SAMPLE_READY);
    assert(sample_state_for(true, false, true) == SENSOR_UNSUPPORTED);
    assert(sample_state_for(true, true, false) == SAMPLE_UNAVAILABLE);
    return 0;
}
