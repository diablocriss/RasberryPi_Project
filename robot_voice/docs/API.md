# API

UART command packets are compact JSON followed by a newline.

Examples:

```json
{"cmd":"MOVE","dir":"FORWARD","speed":120,"time_ms":1000}
{"cmd":"STOP","reason":"EMERGENCY"}
```
