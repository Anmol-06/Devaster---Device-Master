#!/usr/bin/env bash
DEVASTER_INSTALL_BASE="https://raw.githubusercontent.com/Anmol-06/Devaster---Device-Master/main"
set -euo pipefail

# Single-line installer for Devaster agent with optional persistence
# Usage (GitHub/Render/static host):
# curl -fsSL <INSTALL_SCRIPT_URL> | DEVASTER_INSTALL_BASE="<BASE_URL_WITH_app.py>" bash
# or:
# curl -fsSL <INSTALL_SCRIPT_URL> | DEVASTER_AGENT_URL="<DIRECT_app.py_URL>" bash

if [[ "$(uname -s)" != "Linux" && "$(uname -s)" != "Darwin" ]]; then
  echo "This installer is for Linux/macOS only."
  exit 1
fi

APP_DIR="${HOME}/.devaster"
PY_BIN="${PY_BIN:-python3}"
BROKER="${DEVASTER_MQTT_BROKER:-broker.hivemq.com}"
PORT="${DEVASTER_MQTT_PORT:-1883}"
NAMESPACE="${DEVASTER_MQTT_NAMESPACE:-devaster}"

echo "Installing Devaster agent..."
mkdir -p "${APP_DIR}"

if command -v curl >/dev/null 2>&1; then
  FETCH_CMD="curl -fsSL"
elif command -v wget >/dev/null 2>&1; then
  FETCH_CMD="wget -qO-"
else
  echo "curl or wget required."
  exit 1
fi

if [[ -z "${DEVASTER_AGENT_URL:-}" ]]; then
  if [[ -n "${DEVASTER_INSTALL_BASE:-}" ]]; then
    DEVASTER_AGENT_URL="${DEVASTER_INSTALL_BASE%/}/app.py"
  else
    echo "Error: set DEVASTER_AGENT_URL or DEVASTER_INSTALL_BASE"
    echo "Example:"
    echo "  curl -fsSL <install_unix.sh URL> | DEVASTER_INSTALL_BASE=\"https://raw.githubusercontent.com/<user>/<repo>/<branch>\" bash"
    exit 1
  fi
fi

${FETCH_CMD} "${DEVASTER_AGENT_URL}" > "${APP_DIR}/app.py"

${PY_BIN} -m pip install --user --upgrade pip >/dev/null 2>&1
${PY_BIN} -m pip install --user paho-mqtt psutil requests gputil python-dotenv >/dev/null 2>&1

cat > "${APP_DIR}/.env" <<EOF
DEVASTER_MQTT_BROKER=${BROKER}
DEVASTER_MQTT_PORT=${PORT}
DEVASTER_MQTT_NAMESPACE=${NAMESPACE}
DEVASTER_ENV_FILE=${APP_DIR}/.env
EOF

echo "Starting first-run pairing..."
echo "Please run '/add_device' in your Telegram bot to get a 6-digit pairing code."
read -rp "Enter your 6-digit pairing code from Telegram: " PAIR_CODE

if [[ ! "${PAIR_CODE}" =~ ^[0-9]{6}$ ]]; then
  echo "Invalid pairing code format. Must be exactly 6 digits."
  exit 1
fi

echo "Pairing agent with your account..."
DEVASTER_PAIR_ONLY=1 printf "%s\n" "${PAIR_CODE}" | ${PY_BIN} "${APP_DIR}/app.py"

# Ask about persistence
echo ""
read -rp "Do you want Devaster to start automatically on boot/login? [y/N] " PERSISTENCE_CHOICE
PERSISTENCE_CHOICE="${PERSISTENCE_CHOICE:-N}"

if [[ "${PERSISTENCE_CHOICE}" =~ ^[Yy]$ ]]; then
  if [[ "$(uname -s)" == "Linux" ]]; then
    mkdir -p "${HOME}/.config/systemd/user"
    cat > "${HOME}/.config/systemd/user/devaster-agent.service" <<EOF
[Unit]
Description=Devaster Agent

[Service]
EnvironmentFile=${APP_DIR}/.env
ExecStart=${PY_BIN} ${APP_DIR}/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now devaster-agent.service
    echo "✓ Installed and started user systemd service: devaster-agent.service"
    
    # Enable lingering so service runs even when user is not logged in
    echo "Enabling user lingering for persistent background operation..."
    sudo loginctl enable-linger "$USER" 2>/dev/null || echo "Note: You may need to run 'sudo loginctl enable-linger $USER' manually for persistent background operation"
  else
    mkdir -p "${HOME}/Library/LaunchAgents"
    cat > "${HOME}/Library/LaunchAgents/com.devaster.agent.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.devaster.agent</string>
  <key>ProgramArguments</key>
  <array><string>${PY_BIN}</string><string>${APP_DIR}/app.py</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>DEVASTER_MQTT_BROKER</key><string>${BROKER}</string>
    <key>DEVASTER_MQTT_PORT</key><string>${PORT}</string>
    <key>DEVASTER_MQTT_NAMESPACE</key><string>${NAMESPACE}</string>
    <key>DEVASTER_ENV_FILE</key><string>${APP_DIR}/.env</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
EOF
    launchctl unload "${HOME}/Library/LaunchAgents/com.devaster.agent.plist" >/dev/null 2>&1 || true
    launchctl load "${HOME}/Library/LaunchAgents/com.devaster.agent.plist"
    echo "✓ Installed and loaded launchd agent: com.devaster.agent"
  fi
else
  echo "✓ Devaster installed but not set to start automatically."
  echo "  To run manually: ${PY_BIN} ${APP_DIR}/app.py"
  echo "  To enable auto-start later, run the installer again and choose 'yes' for persistence."
fi

echo ""
echo "Devaster installation complete!"
echo ""
echo "Next steps:"
echo "1. In Telegram, send /stats to see your device information"
echo "2. Use /help to see all available commands"
echo ""
if [[ "${PERSISTENCE_CHOICE}" =~ ^[Yy]$ ]]; then
  echo "Devaster will now start automatically on boot/login."
else
  echo "Remember to start Devaster manually after reboot if needed."
fi
