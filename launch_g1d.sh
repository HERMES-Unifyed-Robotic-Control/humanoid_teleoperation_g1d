#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XR_TELEOP_ROOT="${XR_TELEOP_ROOT:-${PROJECT_ROOT}}"
TELEOP_ENTRY="${XR_TELEOP_ROOT}/teleop/teleop_hand_and_arm.py"
EE_MODE="${EE_MODE:-dex1_internal}"
DISPLAY_MODE="${DISPLAY_MODE:-immersive}"
VOICE_LANGUAGE="${VOICE_LANGUAGE:-zh}"

if [[ ! -f "${TELEOP_ENTRY}" ]]; then
  echo "XR teleop entry not found: ${TELEOP_ENTRY}" >&2
  exit 1
fi

# The XR process needs the camera service only for its initial camera-config
# request.  Fail before creating any motor controller if that service is not
# available, instead of leaving a half-initialized Vuer page behind.
if ! systemctl is-active --quiet teleimager.service 2>/dev/null; then
  if ! ss -ltnH 2>/dev/null | awk '$4 ~ /:60000$/ { found=1 } END { exit !found }'; then
    echo "teleimager.service is not active and port 60000 is not listening." >&2
    echo "  sudo systemctl restart teleimager.service" >&2
    exit 1
  fi
fi

# A previous teleop process keeps the Vuer WebSocket port and makes a new
# PICO tab appear to load forever.  Refuse to start a second server and show
# the operator what must be stopped first.
if ss -ltnH 2>/dev/null | awk '$4 ~ /:8012$/ { found=1 } END { exit !found }'; then
  echo "XR WebSocket port 8012 is already in use." >&2
  ss -ltnp 2>/dev/null | grep -E ':(8012)[[:space:]]' >&2 || true
  echo "Close the previous teleop process (Q/Ctrl-C), then run this command again." >&2
  exit 1
fi

if [[ "${EE_MODE}" == "dex1" ]]; then
  DEX1_ROOT="${DEX1_ROOT:-/home/unitree/unitree_eai_environment/service/dex1_1_service}"
  if systemctl list-unit-files dex1_gripper.service --no-legend 2>/dev/null | grep -q dex1_gripper; then
    if ! systemctl is-active --quiet dex1_gripper.service; then
      echo "dex1_gripper.service exists but is not active." >&2
      echo "  sudo systemctl restart dex1_gripper.service" >&2
      echo "  sudo journalctl -u dex1_gripper.service -f" >&2
      exit 1
    fi
  elif ! pgrep -f '[d]ex1_1_gripper_server' >/dev/null; then
    echo "Dex1 server is not running and dex1_gripper.service is not installed." >&2
    echo "Install autostart once:" >&2
    echo "  cd ${DEX1_ROOT} && bash setup_autostart.sh" >&2
    echo "Or run it manually in another terminal:" >&2
    echo "  cd ${DEX1_ROOT}/bin && sudo ./dex1_1_gripper_server --network eth0" >&2
    exit 1
  fi
elif [[ "${EE_MODE}" != "dex1_internal" ]]; then
  echo "Unsupported EE_MODE=${EE_MODE}; use dex1_internal or dex1." >&2
  exit 1
fi

if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /home/unitree/miniconda3/envs/tv/bin/python ]]; then
    PYTHON_BIN=/home/unitree/miniconda3/envs/tv/bin/python
  else
    PYTHON_BIN="$(command -v python)"
  fi
fi

# CycloneDDS is started through sudo below.  On systems with
# fs.protected_regular enabled, root cannot reopen an existing file in /tmp
# owned by the non-root login user.  Normalize the trace log ownership once
# before creating the DDS domain so a previous non-sudo run cannot block it.
if [[ -e /tmp/cdds.LOG ]]; then
  sudo chown root:root /tmp/cdds.LOG
  sudo chmod 664 /tmp/cdds.LOG
fi
cd "${XR_TELEOP_ROOT}/teleop"
echo "PICO URL: https://vuer.ai?ws=wss://192.168.10.104:8012"
echo "PICO local fallback: https://192.168.10.104:8012/?ws=wss://192.168.10.104:8012"
exec sudo "${PYTHON_BIN}" teleop_hand_and_arm.py \
  --input-mode=controller \
  --display-mode="${DISPLAY_MODE}" \
  --arm=G1 \
  --ee="${EE_MODE}" \
  --base-type=mobile_lift \
  --use-waist \
  --xr-webrtc-host=192.168.10.104 \
  --voice-language="${VOICE_LANGUAGE}" \
  --headless \
  "$@"
