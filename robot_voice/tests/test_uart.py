from config.settings import Settings
from comm.uart import UartClient


def test_uart_dry_run_prints_packet(capsys):
    uart = UartClient(Settings(uart_port="TEST", dry_run=True))

    uart.send_json({"cmd": "STOP"})

    captured = capsys.readouterr()
    assert 'UART dry-run -> TEST: {"cmd":"STOP"}' in captured.out
