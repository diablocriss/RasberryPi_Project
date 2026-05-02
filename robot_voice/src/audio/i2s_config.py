from dataclasses import dataclass


@dataclass(frozen=True)
class I2SConfig:
    profile: str = "i2s_inmp441_max98357"
    mic_device: str = "default"
    amp_device: str = "default"
    mic_sample_rate: int = 16000
    amp_sample_rate: int = 22050
    channels: int = 1
    sample_format: str = "S16_LE"
    frames_per_buffer: int = 1024


def from_settings(settings) -> I2SConfig:
    return I2SConfig(
        profile=settings.audio_hardware_profile,
        mic_device=settings.audio_input_device,
        amp_device=settings.audio_output_device,
        mic_sample_rate=settings.audio_sample_rate,
        amp_sample_rate=getattr(settings, "audio_output_sample_rate", 22050),
        channels=settings.audio_channels,
    )
