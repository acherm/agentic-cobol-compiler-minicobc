#include <stdint.h>

short sum_and_scale(short a, short b, short factor) {
    return (a + b) * factor;
}

void mutate_pair(short *a, short *b) {
    *a += 1;
    *b += 2;
}

int first_char_code(char *text) {
    return (unsigned char) text[0];
}
