#include "temperature.h"
#include <stddef.h>
#include <stdio.h>

struct sample {
    uint8_t msb;
    uint8_t lsb;
    double expected_c;
};

int main(void)
{
    const struct sample cases[] = {
        {0x00, 0x00, 0.0},
        {0x19, 0x80, 25.5},
        {0xff, 0x80, -0.5},
        {0x80, 0x00, -128.0},
        {0x7f, 0xff, 127.99609375},
    };
    size_t failed = 0;
    const size_t count = sizeof cases / sizeof cases[0];
    for (size_t i = 0; i < count; ++i) {
        const double actual = temperature_c(cases[i].msb, cases[i].lsb);
        /* Every expected value is a small integer divided by a power of two. */
        if (actual != cases[i].expected_c) {
            fprintf(stderr, "%02X %02X: expected %.8f C, got %.8f C\n",
                    (unsigned)cases[i].msb, (unsigned)cases[i].lsb,
                    cases[i].expected_c, actual);
            ++failed;
        }
    }
    printf("%zu/%zu temperature cases passed\n", count - failed, count);
    return failed == 0 ? 0 : 1;
}
