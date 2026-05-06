#!/usr/bin/env python3
"""WiFi captive portal for Raspberry Pi.

Creates a hotspot and serves a web page to configure WiFi credentials.
Must run as root: sudo python3 scripts/wifi_portal.py
Connect to 'RobotAP' then open http://10.42.0.1
"""

import subprocess
from flask import Flask, request, render_template_string

app = Flask(__name__)

_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Robot WiFi Setup</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: Arial, sans-serif; max-width: 420px; margin: 40px auto; padding: 20px; background: #f5f5f5; }
    h1 { color: #4caf50; margin-bottom: 4px; }
    p  { color: #666; margin-top: 0; }
    label { display: block; margin-top: 14px; font-weight: bold; }
    select, input[type=text], input[type=password] {
      width: 100%; padding: 10px; margin-top: 4px; border: 1px solid #ccc;
      border-radius: 6px; font-size: 15px;
    }
    button {
      margin-top: 18px; width: 100%; padding: 13px;
      background: #4caf50; color: #fff; border: none;
      border-radius: 6px; font-size: 16px; cursor: pointer;
    }
    button:hover { background: #388e3c; }
    .msg { padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 14px; }
    .ok  { background: #c8e6c9; color: #1b5e20; }
    .err { background: #ffcdd2; color: #b71c1c; }
    .status { margin-top: 20px; font-size: 13px; color: #888; text-align: center; }
  </style>
</head>
<body>
  <h1>Robot WiFi Setup</h1>
  <p>Select a network and enter the password.</p>

  {% if message %}
  <div class="msg {{ 'ok' if success else 'err' }}">{{ message }}</div>
  {% endif %}

  <form method="POST" action="/connect">
    <label>Available networks</label>
    <select name="ssid">
      {% for net in networks %}
      <option value="{{ net.ssid }}">{{ net.ssid }} &nbsp;({{ net.signal }}%{{ ' 🔒' if net.secure else '' }})</option>
      {% endfor %}
      <option value="">-- Enter manually below --</option>
    </select>

    <label>Or type SSID manually</label>
    <input type="text" name="custom_ssid" placeholder="Leave blank to use selection above">

    <label>Password</label>
    <input type="password" name="password" placeholder="WiFi password">

    <button type="submit">Connect</button>
  </form>

  <div class="status">Current connection: <strong>{{ status }}</strong></div>
</body>
</html>"""


def _run(cmd, timeout=20):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def scan_networks():
    r = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"], timeout=15)
    seen, nets = set(), []
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        ssid = parts[0].strip()
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        nets.append({
            "ssid": ssid,
            "signal": parts[1] if len(parts) > 1 else "?",
            "secure": parts[2] != "--" if len(parts) > 2 else True,
        })
    return sorted(nets, key=lambda x: int(x["signal"]) if x["signal"].isdigit() else 0, reverse=True)


def current_connection():
    r = _run(["nmcli", "-t", "-f", "NAME,TYPE,STATE", "con", "show", "--active"])
    for line in r.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "802-11-wireless" and parts[2] == "activated":
            return parts[0]
    return "Not connected"


@app.route("/")
def index():
    return render_template_string(_HTML,
        networks=scan_networks(),
        status=current_connection(),
        message=None, success=False)


@app.route("/connect", methods=["POST"])
def connect():
    ssid = (request.form.get("custom_ssid") or request.form.get("ssid", "")).strip()
    password = request.form.get("password", "").strip()

    if not ssid:
        return render_template_string(_HTML,
            networks=scan_networks(), status=current_connection(),
            message="Please select or enter a network name.", success=False)

    # Remove hotspot so wlan0 is free to connect
    _run(["nmcli", "connection", "delete", "Hotspot"], timeout=10)

    cmd = ["nmcli", "dev", "wifi", "connect", ssid, "ifname", "wlan0"]
    if password:
        cmd += ["password", password]

    r = _run(cmd, timeout=30)

    if r.returncode == 0:
        return render_template_string(_HTML,
            networks=[], status=ssid,
            message=f"Connected to '{ssid}'! You can close this page.", success=True)

    error = r.stderr.strip() or r.stdout.strip()
    return render_template_string(_HTML,
        networks=scan_networks(), status=current_connection(),
        message=f"Failed: {error}", success=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
