#!/usr/bin/env bash
set -euo pipefail
cd /home/pi/auszeit_display
source config/publish.env
export FTP_HOST FTP_USER FTP_PASS
exec ./venv/bin/python -m player.publish_feed
