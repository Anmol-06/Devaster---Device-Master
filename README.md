<div align="center">

# 📱 Devaster | Telegram-Based AI RMM
**Turn your Telegram chat into a remote console for Windows, macOS, and Linux devices.**

[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram&logoColor=white)](https://t.me/device_master_bot)
[![License: MIT](https://img.shields.io/badge/License-Free-green.svg)](#)

*Pair your machines securely with a 6-digit code, monitor granular hardware stats, run diagnostics, and get AI-driven optimization advice—all from your phone or desktop.*

[**🤖 Launch Devaster Bot on Telegram**](https://t.me/device_master_bot)

</div>

---

## ✨ What It Can Do

- 📊 **Deep Real-Time Telemetry:** Monitor CPU (temp, per-core load), RAM, Swap, **GPU**, battery health, disk usage, and network I/O.
- ⚡ **Remote Execution:** Kill processes, terminate entire apps, find specific paths, or safely scan and delete old/large items.
- 🧠 **AI Analysis (Zero-Cost):** Powered by free Gemini/Groq APIs. Turns raw data into plain-language insights (e.g., *"Chrome is using 4GB RAM – should I close it?"*).
- 🔄 **Seamless Multi-Device Support:** Pair multiple machines to one account. Effortlessly switch context using `/manage <id>` and `/stop_manage`.
- 🛡️ **Security & Auditing:** Track exposed ports, failed logins, and verify your firewall/Antivirus status in seconds.
- ⚙️ **Automatic Persistence:** Built-in support for `systemd` (Linux) and `launchd` (macOS) ensures the agent survives system reboots.

## 💡 Why Use Devaster?

*   **No Terminal Required:** Quickly spot performance hogs, memory leaks, or thermal throttling right from your chat app.
*   **Prevent Hardware Failure:** Keep an eye on battery wear, disk SMART health, and GPU/CPU temperatures.
*   **Clear Up Space:** Instantly locate and review large, unused files filling up your storage.
*   **Actionable AI Advice:** Stop guessing what to do. Get tailored, immediate optimizations based on your machine's live state.
*   **Global Access:** Control all your computers from a single chat interface, anywhere you have an internet connection.

---

## 🚀 Quick Start

1. Open **[Devaster Bot](https://t.me/device_master_bot)** on Telegram and click `Start`.
2. Send the `/add_device` command to generate your temporary 6-digit pairing code.
3. Install the agent on your computer and enter the code when prompted. 

For full installation commands for Linux, macOS, and Windows, check out our **[Installation Guide](installation.md)**.

---

## 🛠️ Command Reference

Once your device is paired, you can control it using direct slash commands or conversational natural language.

### 📌 Core & Device Management
| Command | Description |
| :--- | :--- |
| `/start` / `/help` | Shows the welcome message and usage guide. |
| `/about` | Summary of Devaster’s capabilities and telemetry collected. |
| `/add_device` | Generates a 6-digit pairing code to link a new machine. |
| `/devices` | Lists all paired devices and highlights the currently active one. |
| `/manage <id>` | Locks subsequent commands to the specified device ID. |
| `/stop_manage` | Unlocks device-specific mode. |

### 📊 Monitoring & Telemetry
| Command | Description |
| :--- | :--- |
| `/stats` | Returns a formatted hardware snapshot (CPU, RAM, GPU, Disk, etc.). |
| `/processes` | Shows top resource-using processes (grouped by app name) with PIDs. |
| `/storage` | Lists large/old files and directories; highlights safe-to-delete candidates. |
| `show failed logins` | Displays count of failed OS login attempts in the last 24h. |
| `show exposed ports` | Lists listening ports bound to `0.0.0.0` or `::` (externally reachable). |
| `show firewall status` | Reports if the OS firewall is active (ufw, pf, Windows Defender). |
| `show antivirus status` | Indicates if native OS antivirus/security is enabled. |

### ⚡ Remote Actions
| Command | Description |
| :--- | :--- |
| `/kill <pid>` | Terminates the specified process ID (Requires `/manage` mode). |
| `terminate <app_name>` | Kills all processes matching the given app name. |
| `kill tab using most resources in <app_name>` | Finds the heaviest process of the named app and kills only that one. |
| `find me path of folder <name>` | Returns absolute paths matching the folder name within `$HOME`. |
| `delete folder <path>` | Deletes the specified folder/file (Restricted to `$HOME`). |

### 🧠 AI & Natural Language
Devaster understands conversational requests. You don't always need exact commands!

*   *"Why is my PC slow?"* ➔ Triggers AI analysis of current stats/processes with actionable advice.
*   *"Which apps are using most resources?"* ➔ Groups processes by app and shows top consumers.
*   *"Top 3 apps using resources"*
*   *"How hot is my CPU?"*
*   *"Delete folder /home/user/v1"*

---
*Built to make device monitoring accessible, intelligent, and completely free.*
