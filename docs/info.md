<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This project implements an SPI-controlled PWM peripheral
using a 10 MHz system clock.

The SPI interface uses mode 0 and accepts 16-bit transactions:
one read/write bit, seven address bits, and eight data bits.
Only writes are supported.

Five registers control the 16 outputs:
- 0x00: Enable outputs 0–7.
- 0x01: Enable outputs 8–15.
- 0x02: Enable PWM on outputs 0–7.
- 0x03: Enable PWM on outputs 8–15.
- 0x04: Set the shared PWM duty cycle.

The target PWM frequency is approximately 3 kHz.

## How to test

Run the Cocotb tests from the test directory using `make -B`.

The tests verify SPI writes and PWM output behavior.

## External hardware

An SPI controller is needed for physical testing.
Simulation does not require external hardware.
