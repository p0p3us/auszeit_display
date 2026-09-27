#!/usr/bin/env bash
set -euo pipefail
if [ "$(hostname)" != "auszeit-player-01" ]; then
  echo "Nur auf auszeit-player-01 ausfuehren." >&2
  exit 1
fi
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEST=/opt/auszeit-player-package-test
test -f "$SOURCE/prepared/latest.json"
test -f "$SOURCE/activate_real.py"
sudo -v
sudo test -f "$DEST/player/package_test/server.py"
sudo install -m 0644 "$SOURCE/activate_real.py" "$DEST/player/package_test/activate_real.py"
sudo cp -R "$SOURCE/prepared" "$DEST/player/package_test/"
cd "$DEST"
sudo -u player /usr/bin/python3 -m player.package_test.activate_real
