# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray
from cocotb.triggers import FallingEdge, ReadOnly
from cocotb.utils import get_sim_time

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Start the 10MHz system clock
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)  # Set initial state with CS high
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 100, units="ns")  # 10 MHz clock
    cocotb.start_soon(clock.start())

    # Reset, then release reset on a falling edge of system clk
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Configure output 0 for PWM at 50% duty cycle
    await send_spi_transaction(dut, 1, 0x04, 0x80) 
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    # Sample output 0 after the design has settled
    await FallingEdge(dut.clk)
    await ReadOnly()
    previous = int(dut.uo_out.value) & 1
    rising_times = []

    # Observe for at most 1 ms, so a stuck output cannot hang the test
    for _ in range(10000):
        await FallingEdge(dut.clk)
        await ReadOnly()
        current = int(dut.uo_out.value) & 1
        if current == 1 and previous == 0:
            rising_times.append(get_sim_time(units="ns"))
            if len(rising_times) == 3:
                break
        previous = current

    assert len(rising_times) == 3, "PWM did not produce 3 rising edges within 1 ms"

    # Three rising edges gives us 2 complete PWM periods
    for index in range(2):
        period_ns = rising_times[index + 1] - rising_times[index]
        frequency_hz = 1_000_000_000 / period_ns    

        dut._log.info(f"Measured PWM frequency: {frequency_hz:.2f} Hz")
        assert 2970 <= frequency_hz <= 3030, (
            f"PWM frequency out of range: {frequency_hz:.2f} Hz"
        )


@cocotb.test()
async def test_pwm_duty(dut):
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Configure output 0 for PWM at 50% duty cycle.
    await send_spi_transaction(dut, 1, 0x04, 0x80)
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    await FallingEdge(dut.clk)
    await ReadOnly()
    previous = int(dut.uo_out.value) & 1

    first_rise = None
    first_fall = None
    next_rise = None

    # Find a complete PWM cycle within 1 ms.
    for _ in range(10000):
        await FallingEdge(dut.clk)
        await ReadOnly()
        current = int(dut.uo_out.value) & 1
        time_ns = get_sim_time(units="ns")

        if previous == 0 and current == 1:
            if first_rise is None:
                first_rise = time_ns
            else:
                next_rise = time_ns
                break

        elif previous == 1 and current == 0:
            if first_rise is not None and first_fall is None:
                first_fall = time_ns

        previous = current

    assert first_rise is not None, "No PWM rising edge detected"
    assert first_fall is not None, "No PWM falling edge after the rising edge"
    assert next_rise is not None, "No second PWM rising edge detected"

    high_time = first_fall - first_rise
    period = next_rise - first_rise
    duty_percent = 100 * high_time / period

    dut._log.info(f"Measured PWM duty cycle: {duty_percent:.2f}%")
    assert abs(duty_percent - 50.0) <= 1.0, (
        f"Expected 50% duty cycle, got {duty_percent:.2f}%"
    )

@cocotb.test()
async def test_pwm_extremes(dut):
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable PWM and output 0.
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    await send_spi_transaction(dut, 1, 0x00, 0x01)

    # Check 0%, then 100%, then return to 0%.
    for duty_value, expected in [(0x00, 0), (0xFF, 1), (0x00, 0)]:
        # Leave any previous ReadOnly phase before driving inputs.
        await FallingEdge(dut.clk)
        await send_spi_transaction(dut, 1, 0x04, duty_value)

        # Observe for 1 ms—about three normal PWM periods.
        for _ in range(10000):
            await FallingEdge(dut.clk)
            await ReadOnly()
            actual = int(dut.uo_out.value) & 1

            assert actual == expected, (
                f"Duty register 0x{duty_value:02X}: "
                f"expected output {expected}, got {actual}"
            )

        dut._log.info(
            f"Duty register 0x{duty_value:02X}: "
            f"output stayed at {expected} for 1 ms"
        )

@cocotb.test()
async def test_pwm_enables(dut):
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    await send_spi_transaction(dut, 1, 0x04, 0x80)

    # Each pair contains output-enable and PWM-enable masks.
    cases = [
        (0x0000, 0xFFFF),  # All disabled, even with PWM enabled.
        (0xFFFF, 0x0000),  # All enabled as constant-high outputs.
        (0xFFFF, 0xFFFF),  # All enabled as PWM outputs.
        (0xAAAA, 0xCCCC),  # Mix disabled, static, and PWM outputs.
        (0x5555, 0x3333),  # Complementary mix.
    ]

    for output_mask, pwm_mask in cases:
        await FallingEdge(dut.clk)

        # Configure the lower and upper banks through SPI.
        await send_spi_transaction(dut, 1, 0x00, output_mask & 0xFF)
        await send_spi_transaction(dut, 1, 0x01, (output_mask >> 8) & 0xFF)
        await send_spi_transaction(dut, 1, 0x02, pwm_mask & 0xFF)
        await send_spi_transaction(dut, 1, 0x03, (pwm_mask >> 8) & 0xFF)

        expected_low = output_mask & (~pwm_mask & 0xFFFF)
        expected_high = output_mask
        observed = set()

        # Observe for 400 us, longer than one PWM period.
        for _ in range(4000):
            await FallingEdge(dut.clk)
            await ReadOnly()

            actual = (
                (int(dut.uio_out.value) << 8)
                | int(dut.uo_out.value)
            )
            observed.add(actual)

            assert actual in (expected_low, expected_high), (
                f"Enable=0x{output_mask:04X}, PWM=0x{pwm_mask:04X}: "
                f"unexpected outputs 0x{actual:04X}"
            )

        assert observed == {expected_low, expected_high}, (
            f"Enable=0x{output_mask:04X}, PWM=0x{pwm_mask:04X}: "
            "did not observe all expected output states"
        )

        dut._log.info(
            f"Enable=0x{output_mask:04X}, PWM=0x{pwm_mask:04X}: passed"
        )

@cocotb.test()
async def test_pwm_sweep(dut):
    dut.ena.value = 1
    dut.ui_in.value = ui_in_logicarray(1, 0, 0)
    dut.uio_in.value = 0
    dut.rst_n.value = 0

    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Enable all outputs and PWM on both banks.
    for address in (0x00, 0x01, 0x02, 0x03):
        await send_spi_transaction(dut, 1, address, 0xFF)

    for duty_value in range(256):
        await FallingEdge(dut.clk)
        await send_spi_transaction(dut, 1, 0x04, duty_value)

        previous = None
        first_rise = None
        first_fall = None
        next_rise = None

        # Constant outputs need a fixed observation window.
        constant = duty_value in (0, 255)
        sample_count = 4000 if constant else 10000

        for _ in range(sample_count):
            await FallingEdge(dut.clk)
            await ReadOnly()

            outputs = (
                (int(dut.uio_out.value) << 8)
                | int(dut.uo_out.value)
            )

            # All 16 enabled PWM outputs should agree.
            assert outputs in (0x0000, 0xFFFF), (
                f"Duty {duty_value}: outputs disagree: 0x{outputs:04X}"
            )
            current = outputs & 1

            if constant:
                expected = 0 if duty_value == 0 else 1
                assert current == expected, (
                    f"Duty {duty_value}: expected constant {expected}"
                )
                continue

            time_ns = get_sim_time(units="ns")

            if previous == 0 and current == 1:
                if first_rise is None:
                    first_rise = time_ns
                else:
                    next_rise = time_ns
                    break
            elif previous == 1 and current == 0:
                if first_rise is not None and first_fall is None:
                    first_fall = time_ns

            previous = current

        if not constant:
            assert first_rise is not None, f"Duty {duty_value}: no rising edge"
            assert first_fall is not None, f"Duty {duty_value}: no falling edge"
            assert next_rise is not None, f"Duty {duty_value}: incomplete period"

            period_ns = next_rise - first_rise
            measured = 100 * (first_fall - first_rise) / period_ns
            expected = 100 * duty_value / 256
            frequency_hz = 1_000_000_000 / period_ns

            assert abs(measured - expected) <= 1.0, (
                f"Duty {duty_value}: expected {expected:.3f}%, "
                f"got {measured:.3f}%"
            )
            assert 2970 <= frequency_hz <= 3030, (
                f"Duty {duty_value}: frequency {frequency_hz:.2f} Hz"
            )

        if duty_value % 32 == 0 or duty_value == 255:
            dut._log.info(f"Duty sweep passed through value {duty_value}")                
