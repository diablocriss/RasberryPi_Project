from audio.i2s_hardware import I2S_AUDIO_PROFILE, I2S_PIN_MAP, describe_i2s_pin_map


def test_i2s_profile_name_matches_settings_default():
    assert I2S_AUDIO_PROFILE == "i2s_inmp441_max98357"


def test_i2s_pin_map_contains_audio_bus_pins():
    by_gpio = {pin.bcm_gpio: pin for pin in I2S_PIN_MAP if pin.bcm_gpio is not None}

    assert by_gpio[18].connects_to == ("INMP441 SCK", "MAX98357 BCLK")
    assert by_gpio[19].connects_to == ("INMP441 WS", "MAX98357 LRC")
    assert by_gpio[20].connects_to == ("MAX98357 DIN",)
    assert by_gpio[21].connects_to == ("INMP441 SD",)


def test_describe_i2s_pin_map_is_human_readable():
    description = "\n".join(describe_i2s_pin_map())

    assert "Pin 12: GPIO18 I2S BCLK -> INMP441 SCK + MAX98357 BCLK" in description
    assert "Pin 40: GPIO21 I2S DIN -> INMP441 SD" in description
