import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _default_uart_port() -> str:
    return "COM3" if os.name == "nt" else "/dev/ttyUSB0"


@dataclass(frozen=True)
class Settings:
    uart_port: str = field(default_factory=lambda: os.getenv("ROBOT_UART_PORT", _default_uart_port()))
    uart_baudrate: int = field(default_factory=lambda: _int_env("ROBOT_UART_BAUDRATE", 115200))
    uart_timeout_s: float = 1.0
    language: str = "en"
    default_speed: int = field(default_factory=lambda: _int_env("ROBOT_DEFAULT_SPEED", 120))
    default_move_time_ms: int = field(default_factory=lambda: _int_env("ROBOT_DEFAULT_MOVE_TIME_MS", 1000))
    dry_run: bool = field(default_factory=lambda: os.getenv("ROBOT_DRY_RUN", "1") != "0")
    audio_cdc_port: str = field(default_factory=lambda: os.getenv("ROBOT_AUDIO_CDC_PORT", "/dev/ttyACM0"))
    audio_cdc_baudrate: int = field(default_factory=lambda: _int_env("ROBOT_AUDIO_CDC_BAUDRATE", 921600))
    audio_cdc_timeout_s: float = field(default_factory=lambda: _float_env("ROBOT_AUDIO_CDC_TIMEOUT_S", 1.0))
    audio_sample_rate: int = 16000
    audio_bits: int = 16
    audio_channels: int = 1
    audio_input_device: str = field(default_factory=lambda: os.getenv("ROBOT_AUDIO_INPUT_DEVICE", "default"))
    audio_output_device: str = field(default_factory=lambda: os.getenv("ROBOT_AUDIO_OUTPUT_DEVICE", "default"))
    audio_hardware_profile: str = field(default_factory=lambda: os.getenv("ROBOT_AUDIO_HARDWARE_PROFILE", "i2s_inmp441_max98357"))
    audio_frame_min_bytes: int = 64
    audio_frame_max_bytes: int = 1024
    deepgram_api_key: str = field(default_factory=lambda: os.getenv("DEEPGRAM_API_KEY", ""))
    deepgram_language: str = field(default_factory=lambda: os.getenv("DEEPGRAM_LANGUAGE", "en-US"))
