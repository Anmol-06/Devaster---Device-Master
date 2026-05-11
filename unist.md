# Devaster Uninstall Guide (Clean Removal)

Use the steps for your operating system to remove Devaster agent, startup hooks, and local config files.

---

## Linux (systemd user service)

```bash
# 1) Stop and disable the agent service
systemctl --user disable --now devaster-agent.service || true

# 2) Remove service definition
rm -f ~/.config/systemd/user/devaster-agent.service
systemctl --user daemon-reload

# 3) Remove Devaster files/config
rm -rf ~/.devaster
rm -f ~/.devaster_client.json

# 4) Optional: disable lingering if you enabled it only for Devaster
sudo loginctl disable-linger "$USER" || true
```

Verify removal:
```bash
systemctl --user status devaster-agent.service --no-pager || true
ls -la ~/.devaster ~/.devaster_client.json 2>/dev/null || echo "Devaster files removed."
```

---

## macOS (launchd agent)

```bash
# 1) Unload launch agent
launchctl unload ~/Library/LaunchAgents/com.devaster.agent.plist 2>/dev/null || true

# 2) Remove launch agent plist
rm -f ~/Library/LaunchAgents/com.devaster.agent.plist

# 3) Remove Devaster files/config
rm -rf ~/.devaster
rm -f ~/.devaster_client.json
```

Verify removal:
```bash
launchctl list | grep -i devaster || echo "No Devaster launch agent loaded."
ls -la ~/.devaster ~/.devaster_client.json 2>/dev/null || echo "Devaster files removed."
```

---

## Windows (PowerShell)

Open PowerShell as the same user that installed Devaster and run:

```powershell
# 1) Remove startup shortcut (if created)
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Devaster Agent.lnk" -ErrorAction SilentlyContinue

# 2) Remove local Devaster files/config
Remove-Item "$env:USERPROFILE\.devaster" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$env:USERPROFILE\.devaster_client.json" -Force -ErrorAction SilentlyContinue
```

If you used a standalone `.exe`, also delete the downloaded executable manually from its folder.

---

## Server-side unpair (recommended before reinstall)

If you plan to reinstall Devaster on the same machine, unpair the old device first in Telegram:

```text
/devices
/unpair <device_id>
```

Then run `/add_device` to get a fresh pairing code and install again.
