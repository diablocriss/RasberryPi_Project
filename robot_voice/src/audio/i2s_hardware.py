from dataclasses import dataclass


@dataclass(frozen=True)
class I2sPin:
    physical_pin: int
    bcm_gpio: int | None
    signal: str
    connects_to: tuple[str, ...]


I2S_AUDIO_PROFILE = "i2s_inmp441_max98357"

I2S_PIN_MAP = (
    I2sPin(physical_pin=1, bcm_gpio=None, signal="3.3V", connects_to=("INMP441 VDD",)),
    I2sPin(physical_pin=4, bcm_gpio=None, signal="5V", connects_to=("MAX98357 VIN",)),
    I2sPin(physical_pin=6, bcm_gpio=None, signal="GND", connects_to=("INMP441 GND",)),
    I2sPin(physical_pin=9, bcm_gpio=None, signal="GND", connects_to=("MAX98357 GND",)),
    I2sPin(
        physical_pin=12,
        bcm_gpio=18,
        signal="I2S BCLK",
        connects_to=("INMP441 SCK", "MAX98357 BCLK"),
    ),
    I2sPin(
        physical_pin=35,
        bcm_gpio=19,
        signal="I2S LRCLK",
        connects_to=("INMP441 WS", "MAX98357 LRC"),
    ),
    I2sPin(physical_pin=38, bcm_gpio=20, signal="I2S DOUT", connects_to=("MAX98357 DIN",)),
    I2sPin(physical_pin=40, bcm_gpio=21, signal="I2S DIN", connects_to=("INMP441 SD",)),
    I2sPin(physical_pin=14, bcm_gpio=None, signal="GAIN GND", connects_to=("MAX98357 GAIN",)),
)


def describe_i2s_pin_map() -> list[str]:
    lines = []
    for pin in I2S_PIN_MAP:
        gpio = f"GPIO{pin.bcm_gpio}" if pin.bcm_gpio is not None else "POWER"
        targets = " + ".join(pin.connects_to)
        lines.append(f"Pin {pin.physical_pin}: {gpio} {pin.signal} -> {targets}")
    return lines
