from audio.pcm import pcm_to_array
from comm.uart import UartClient
from comm.usb_cdc_audio import UsbCdcAudioReader
from config.settings import Settings
from core.fsd_tree import FsdTree
from stt.processor import stt_get_text, stt_init, stt_send


def audio_pipeline(settings: Settings | None = None) -> None:
    settings = settings or Settings()
    audio_reader = UsbCdcAudioReader(settings)
    command_tree = FsdTree(settings)
    uart = UartClient(settings)

    stt_init(settings.deepgram_api_key, settings.deepgram_language)

    print("[PIPELINE] Streaming started. Speak into the ESP32 microphone.")

    while True:
        try:
            frame = audio_reader.read_frame()
        except TimeoutError:
            continue
        except Exception as exc:
            print(f"[PIPELINE] Audio read error: {exc}")
            continue

        audio = pcm_to_array(frame)
        stt_send(audio)

        text = stt_get_text()
        if not text:
            continue

        command = command_tree.resolve_command(text)
        if command:
            print(f"[FSD] {command}")
            uart.send_json(command)
        else:
            rejected = command_tree.reject(text)
            print(f"[FSD] No match: {rejected}")
