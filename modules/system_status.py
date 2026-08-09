from datetime import datetime
import platform
import shutil
import subprocess


FINDMNT = "/usr/bin/findmnt"
LSUSB = "/usr/bin/lsusb"
VCGENCMD = "/usr/bin/vcgencmd"


def run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=3,
            check=False
        )

        if result.returncode != 0:
            return ""

        return result.stdout.strip()
    except Exception:
        return ""


def get_root_source() -> str:
    output = run_command([FINDMNT, "-n", "-o", "SOURCE", "/"])
    return output if output else "unbekannt"


def get_usb_speed() -> str:
    output = run_command([LSUSB, "-t"])

    if not output:
        return "unbekannt"

    lines = output.splitlines()

    mass_storage_lines = [
        line.strip()
        for line in lines
        if "Mass Storage" in line
    ]

    if not mass_storage_lines:
        return "keine USB-SSD erkannt"

    for line in mass_storage_lines:
        if "5000M" in line:
            return "USB3 / 5000M"

    for line in mass_storage_lines:
        if "480M" in line:
            return "USB2 / 480M"

    return "USB-SSD erkannt, Geschwindigkeit unklar"


def get_throttled_status() -> str:
    output = run_command([VCGENCMD, "get_throttled"])

    if output == "throttled=0x0":
        return "OK, keine Unterspannung"

    return output if output else "unbekannt"


def get_system_status() -> dict:
    total, used, free = shutil.disk_usage("/")

    return {
        "time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "hostname": platform.node(),
        "root_source": get_root_source(),
        "usb_speed": get_usb_speed(),
        "power_status": get_throttled_status(),
        "disk_total_gb": round(total / (1024 ** 3), 2),
        "disk_used_gb": round(used / (1024 ** 3), 2),
        "disk_free_gb": round(free / (1024 ** 3), 2),
    }