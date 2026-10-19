/** main_host.c — Roda o firmware no PC por N segundos (padrão 30 s). */
#include "app.h"
#include "hal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void hal_host_set_hex_only(bool v);

int main(int argc, char **argv)
{
    unsigned seconds = 30;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--hex")) hal_host_set_hex_only(true);
        else seconds = (unsigned)atoi(argv[i]);
    }
    srand(42);
    app_init();
    while (hal_millis() < seconds * 1000u) app_tick();
    return 0;
}
