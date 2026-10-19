# Firmware Pulso — build para o PC (testes e simulação).
# O build para a placa real é feito no STM32CubeIDE (ver README.md).

CC      ?= gcc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2 -Iinclude -Idrivers
LDLIBS  = -lm

CORE    = src/packet.c src/sos.c src/ppg.c src/uwb_pos.c src/fall.c
APP     = src/app.c drivers/max30102.c drivers/lis2dh12.c drivers/max17048.c
HOST    = platform/host/hal_host.c platform/host/main_host.c

all: build/pulso_tests build/pulso_sim

build:
	mkdir -p build

build/pulso_tests: $(CORE) tests/test_main.c | build
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

build/pulso_sim: $(CORE) $(APP) $(HOST) | build
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

test: build/pulso_tests
	./build/pulso_tests

sim: build/pulso_sim
	./build/pulso_sim 30

clean:
	rm -rf build

.PHONY: all test sim clean
