import socket


def has_internet(host: str = "8.8.8.8", port: int = 53, timeout_s: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False
