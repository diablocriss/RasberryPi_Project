def device_index(audio, device_name: str | None, *, input_device: bool) -> int | None:
    if not device_name or device_name == "default":
        return None

    for index in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(index)
        name = info.get("name", "")
        if device_name == name or device_name in name:
            if input_device and info.get("maxInputChannels", 0) > 0:
                return index
            if not input_device and info.get("maxOutputChannels", 0) > 0:
                return index

    kind = "input" if input_device else "output"
    raise RuntimeError(f"PyAudio {kind} device not found: {device_name}")
