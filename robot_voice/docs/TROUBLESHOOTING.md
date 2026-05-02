# Troubleshooting

## No ALSA capture devices

Run:

```bash
bash scripts/pi_process.sh check
```

Verify INMP441 wiring and I2S microphone overlay configuration.

## No ESP32 serial device

Run:

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

Use a USB data cable and common ground for UART hardware.
