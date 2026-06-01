#!/usr/bin/env python3
"""SPI wiring diagnostic — captures one raw transaction and shows
exactly what arrives on each GPIO pin, edge by edge.

Run on Pi while ESP32 sends ping3 repeatedly.
"""
import sys
import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("pip install RPi.GPIO"); sys.exit(1)

CS   = 22
MOSI = 10
MISO = 9
SCLK = 11

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(CS,   GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(MOSI, GPIO.IN)
GPIO.setup(SCLK, GPIO.IN)
GPIO.setup(MISO, GPIO.OUT, initial=GPIO.LOW)

print(f"Watching  CS=GPIO{CS}  SCLK=GPIO{SCLK}  MOSI=GPIO{MOSI}")
print("Idle levels (should be: CS=1 SCLK=0 MOSI=0 when ESP32 not sending):")
print(f"  CS={GPIO.input(CS)}  SCLK={GPIO.input(SCLK)}  MOSI={GPIO.input(MOSI)}")
print()
print("Waiting for CS LOW (ask ESP32 to 'ping3')...")

deadline = time.monotonic() + 30
while GPIO.input(CS) == GPIO.HIGH:
    if time.monotonic() > deadline:
        print("Timeout: CS never went LOW in 30s")
        print("  → IO15 (ESP32) is not reaching GPIO22 (Pi), or ESP32 not sending")
        GPIO.cleanup(); sys.exit(1)

print("CS LOW detected — capturing edges...")

edges = []          # (sclk_level, mosi_level) at each SCLK edge
prev_sclk = GPIO.input(SCLK)
prev_mosi = GPIO.input(MOSI)
t_start   = time.monotonic()

while not GPIO.input(CS):
    s = GPIO.input(SCLK)
    m = GPIO.input(MOSI)
    if s != prev_sclk:
        edges.append((s, m))
        prev_sclk = s

# Wait for CS to go HIGH
deadline2 = time.monotonic() + 0.01
while not GPIO.input(CS) and time.monotonic() < deadline2:
    pass

GPIO.cleanup()

rising  = [(s, m) for (s, m) in edges if s == 1]  # rising edges
falling = [(s, m) for (s, m) in edges if s == 0]  # falling edges

print(f"\nTotal SCLK edges captured: {len(edges)}")
print(f"  Rising  edges: {len(rising)}  (expected 32 for 4 bytes)")
print(f"  Falling edges: {len(falling)}")
print()

if len(rising) == 0:
    print("DIAGNOSIS: No rising edges on GPIO11.")
    print("  → GPIO11 is not seeing SCLK — either SCLK not wired to GPIO11,")
    print("    or MOSI/SCLK are swapped on the Pi end.")
    sys.exit(0)

print("MOSI sampled at each SCLK rising edge (MSB first):")
for i, (_, m) in enumerate(rising[:32]):
    if i % 8 == 0:
        print(f"  byte {i//8}: ", end="")
    print(m, end=" ")
    if i % 8 == 7:
        byte_val = 0
        for j, (_, bm) in enumerate(rising[i-7:i+1]):
            byte_val |= (bm << (7 - j))
        print(f"= 0x{byte_val:02X}", end="")
        if i // 8 == 0: print("  (should be 0x45 for PING)", end="")
        if i // 8 == 3: print("  (should be 0x6D for PING CRC)", end="")
        print()

print()
if len(rising) >= 32:
    bytes_rx = []
    for b in range(4):
        bval = 0
        for bit in range(8):
            idx = b*8 + bit
            if idx < len(rising):
                bval |= (rising[idx][1] << (7 - bit))
        bytes_rx.append(bval)
    print(f"Decoded frame: {[hex(b) for b in bytes_rx]}")
    if bytes_rx == [0x45, 0x00, 0x00, 0x6D]:
        print("WIRING OK — frame matches expected PING perfectly!")
    elif bytes_rx[0] == 0x45:
        print("PARTIAL: first byte matches PING (0x45) but CRC is wrong")
    else:
        print(f"MISMATCH — expected [0x45, 0x00, 0x00, 0x6D]")
        print("  Check: are MOSI and SCLK wires swapped?")
        print("  Check: is ESP32 firmware flashed (look for [PI-SPI] in boot log)?")
