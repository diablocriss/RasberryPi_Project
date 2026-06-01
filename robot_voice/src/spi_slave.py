#!/usr/bin/env python3
"""SPI Slave for Raspberry Pi 4 — receives 4-byte frames from ESP32 master.

Protocol (identical to ESP32 Slave1/Slave2):
  RX frame: [CMD][PARAM1][PARAM2][CRC8(cmd,p1,p2)]
  TX frame: [0xDE][0xAD][data1][CRC8(DE,AD,data1)]  ← OK
            [0xEE][err ][0x00 ][CRC8(EE,err,00 )]   ← ERROR
  Mode 0 (CPOL=0 CPHA=0), MSB first, CS active LOW
  CRC-8: poly=0x07, init=0xFF, over bytes[0..2]

Wiring (BCM numbering — matches ESP32 MasterPiSpi.h):
  GPIO22 ← CS   (active LOW)   ← ESP32 IO15
  GPIO10 ← MOSI                ← ESP32 IO17
  GPIO9  → MISO                → ESP32 IO16
  GPIO11 ← SCLK (idles LOW)    ← ESP32 IO18

WARNING: GPIO9/10/11 are the Pi hardware SPI0 pins. If spidev is loaded
via raspi-config, the kernel driver owns these pins and GPIO access will
fail. Either keep SPI disabled in raspi-config, or rewire to other GPIOs.

Response pipeline: the slave pre-loads the response for command N before
transaction N+1 starts (one-transaction lag, matching ESP32 slave1 behaviour).
The first transaction always returns the default OK [0xDE 0xAD 0x00 CRC].

Run:  python3 src/spi_slave.py
Stop: Ctrl+C
"""

import sys
import time
import signal

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not installed. Run: pip install RPi.GPIO")
    sys.exit(1)

# ── Pin definitions (BCM) ─────────────────────────────────────
CS   = 22
MOSI = 10
MISO = 9
SCLK = 11

# ── Protocol constants ────────────────────────────────────────
RESP_OK    = 0xDE
RESP_ACK   = 0xAD
RESP_ERROR = 0xEE

# ── Text command accumulator ──────────────────────────────────
_text_buf      = ""
_text_expected = 0
_text_start_t  = 0.0

# ── Pending TX buffer (response loaded before each transaction) ──
# Initialised to default OK; updated after every command is processed.
_pending_tx = [RESP_OK, RESP_ACK, 0x00, 0x00]  # CRC filled in main()

# ── Boot time reference ───────────────────────────────────────
_start_time = time.monotonic()


# ─────────────────────────────────────────────────────────────
# CRC-8  poly=0x07  init=0xFF  (matches ESP32 crc8_calc)
# ─────────────────────────────────────────────────────────────
def _crc8(data: list) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte & 0xFF
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
    return crc


def _make_ok(data1: int = 0x00) -> list:
    frame = [RESP_OK, RESP_ACK, data1 & 0xFF]
    frame.append(_crc8(frame))
    return frame


def _make_error(code: int) -> list:
    frame = [RESP_ERROR, code & 0xFF, 0x00]
    frame.append(_crc8(frame))
    return frame


# Module-level constant — used by _run() and main() to reset the pipeline.
_DEFAULT_OK = _make_ok()


# ─────────────────────────────────────────────────────────────
# Full-duplex 4-byte bit-bang transfer (slave role)
#
# Tight GPIO polling loop — requires Pi 4 for 200 kHz timing.
# At 200 kHz each bit period = 5 µs; RPi.GPIO GPIO.input() ≈ 0.5 µs,
# giving ~10 iterations per half-period — sufficient to catch edges.
#
# CS abort: if CS goes HIGH mid-frame the loop exits early and returns
# however many bytes were received (padded with 0x00). The caller's CRC
# check will reject the partial frame and return an error response.
# ─────────────────────────────────────────────────────────────
def _transfer_frame(tx: list) -> list:
    rx = []
    for byte_idx in range(4):
        tx_byte = tx[byte_idx] if byte_idx < len(tx) else 0x00
        rx_byte = 0
        for bit in range(7, -1, -1):
            # Drive MISO before rising edge (CPHA=0: data setup before sample)
            GPIO.output(MISO, (tx_byte >> bit) & 1)

            # Wait for SCLK rising edge; bail if CS deasserted (abort)
            while not GPIO.input(SCLK):
                if GPIO.input(CS):
                    rx.append(rx_byte)
                    return rx + [0x00] * (4 - len(rx))

            # Sample MOSI on rising edge
            if GPIO.input(MOSI):
                rx_byte |= (1 << bit)

            # Wait for SCLK falling edge; bail if CS deasserted
            while GPIO.input(SCLK):
                if GPIO.input(CS):
                    rx.append(rx_byte)
                    return rx + [0x00] * (4 - len(rx))

        rx.append(rx_byte)

    return rx


# ─────────────────────────────────────────────────────────────
# Command processor — returns the response frame for the NEXT
# transaction (one-frame pipeline lag, matches hardware slaves).
# ─────────────────────────────────────────────────────────────
def _process_command(rx: list) -> list:
    global _text_buf, _text_expected, _text_start_t

    if len(rx) < 4:
        return _make_error(0x02)

    cmd, p1, p2, rx_crc = rx[0], rx[1], rx[2], rx[3]
    print(f"[RX] {[hex(b) for b in rx]}  crc_ok={_crc8([cmd,p1,p2])==rx_crc or cmd==0x08}")

    # ── CRC check (skip for CMD_LED_CUSTOM 0x08 — byte3 = Blue) ──
    if cmd != 0x08:
        if _crc8([cmd, p1, p2]) != rx_crc:
            print(f"[SPI] CRC ERROR  cmd=0x{cmd:02X}  "
                  f"expected=0x{_crc8([cmd,p1,p2]):02X}  got=0x{rx_crc:02X}")
            return _make_error(0x03)  # ERR_CRC_MISMATCH

    uptime_lsb = int(time.monotonic() - _start_time) & 0xFF

    # ── PING (0x45) ───────────────────────────────────────────
    if cmd == 0x45:
        print(f"[SPI] PING received  uptime={uptime_lsb}s")
        frame = [RESP_OK, RESP_ACK, uptime_lsb]
        frame.append(_crc8(frame))
        return frame

    # ── LED OFF (0x00) ────────────────────────────────────────
    if cmd == 0x00:
        print("[LED] OFF")
        return _make_ok(cmd)

    # ── LED presets (0x01–0x07) ───────────────────────────────
    _led_names = {
        0x01: "RED", 0x02: "GREEN", 0x03: "BLUE",
        0x04: "YELLOW", 0x05: "CYAN", 0x06: "MAGENTA", 0x07: "WHITE",
    }
    if cmd in _led_names:
        print(f"[LED] {_led_names[cmd]}")
        return _make_ok(cmd)

    # ── LED CUSTOM (0x08) — [R][G][B], byte3 is Blue not CRC ─
    if cmd == 0x08:
        r, g, b = p1, p2, rx_crc
        print(f"[LED] CUSTOM  R={r}  G={g}  B={b}")
        return _make_ok()

    # ── LED BRIGHTNESS (0x09) ─────────────────────────────────
    if cmd == 0x09:
        print(f"[LED] BRIGHTNESS={p1}")
        return _make_ok(p1)

    # ── SERVO SET ANGLE (0x10) ────────────────────────────────
    if cmd == 0x10:
        print(f"[SERVO] servo={p1}  →  {p2}°")
        return _make_ok(p1)

    # ── TEXT_START (0x30) — begin multi-frame text command ────
    if cmd == 0x30:
        _text_buf      = ""
        _text_expected = p1
        _text_start_t  = time.monotonic()
        return _make_ok()

    # ── TEXT_DATA (0x31) — 2 chars per frame ──────────────────
    if cmd == 0x31:
        if _text_expected == 0 or (time.monotonic() - _text_start_t) > 0.5:
            _text_expected = 0
            return _make_error(0x01)  # ERR_INVALID_CMD (no START or timeout)
        _text_buf += chr(p1)
        if p2 != 0x00:
            _text_buf += chr(p2)
        return _make_ok()

    # ── TEXT_EXEC (0x32) — execute assembled string ───────────
    if cmd == 0x32:
        if _text_expected == 0 or len(_text_buf) == 0:
            return _make_error(0x01)
        text = _text_buf[:_text_expected]
        print(f"[TEXT] {text}")
        _text_expected = 0
        _text_buf      = ""
        return _make_ok()

    # ── EMERGENCY STOP (0xFF) ─────────────────────────────────
    if cmd == 0xFF:
        print("[ESTOP] Emergency stop received")
        return _make_ok(0xFF)

    # ── Unknown command ───────────────────────────────────────
    print(f"[SPI] Unknown command: 0x{cmd:02X}  p1=0x{p1:02X}  p2=0x{p2:02X}")
    return _make_error(0x02)  # ERR_INVALID_CMD


# ─────────────────────────────────────────────────────────────
# GPIO setup
# ─────────────────────────────────────────────────────────────
def _gpio_setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(CS,   GPIO.IN,  pull_up_down=GPIO.PUD_UP)
    GPIO.setup(MOSI, GPIO.IN)
    GPIO.setup(SCLK, GPIO.IN)
    GPIO.setup(MISO, GPIO.OUT, initial=GPIO.LOW)


# ─────────────────────────────────────────────────────────────
# Main receive loop
# ─────────────────────────────────────────────────────────────
def _run(pending_tx: list):
    # Tight polling — no sleep() to avoid missing a CS edge at 200 kHz.
    # Heartbeat counter: prints "." every ~5 s of idle (calibrated for Pi 4).
    _HEARTBEAT_TICKS = 4_000_000  # ~5 s of idle GPIO.input() calls on Pi 4
    idle_ticks = 0

    while True:
        if GPIO.input(CS) == GPIO.HIGH:
            idle_ticks += 1
            if idle_ticks >= _HEARTBEAT_TICKS:
                print(".", end="", flush=True)
                idle_ticks = 0
            continue

        # CS asserted — transaction in progress
        idle_ticks = 0

        # Full-duplex: output pending_tx while clocking in the command
        rx = _transfer_frame(pending_tx)

        # Wait for CS HIGH (end of transaction)
        while not GPIO.input(CS):
            pass

        # Process received command; result becomes response for next frame.
        # After a CRC error (often from ESP32 IO15 floating during boot),
        # reset pending_tx to default OK so the next real command gets a
        # proper response instead of a stale error frame.
        response = _process_command(rx)
        if response[0] == RESP_ERROR:
            pending_tx = list(_DEFAULT_OK)
        else:
            pending_tx = response


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
def main():
    try:
        _gpio_setup()
    except RuntimeError as exc:
        print(f"ERROR: GPIO setup failed — {exc}")
        print("Hint: run as root (sudo) or add user to 'gpio' group.")
        sys.exit(1)

    def _shutdown(sig, frame):
        GPIO.cleanup()
        print("\nSlave stopped")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("SPI Slave ready")
    print(f"  CS=GPIO{CS}  SCLK=GPIO{SCLK}  MOSI=GPIO{MOSI}  MISO=GPIO{MISO}")
    print(f"  Protocol: Mode 0, MSB first, CRC-8 (poly=0x07 init=0xFF)")
    print(f"  Waiting for ESP32 master...")

    try:
        _run(list(_DEFAULT_OK))
    except Exception as exc:
        print(f"\n[ERROR] Unhandled exception: {exc}")
        GPIO.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()
