#include "temperature.h"

double temperature_c(uint8_t msb, uint8_t lsb)
{
    int32_t counts = (int32_t)msb * 256 + lsb;
    if (counts >= 32768)
        counts -= 65536;
    return counts / 256.0;
}
