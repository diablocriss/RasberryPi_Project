#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y alsa-utils portaudio19-dev python3-pyaudio ffmpeg git
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python -m pip install -r requirements-pi.txt
