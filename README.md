Devaster – Telegram‑Based AI RMM
Turn your Telegram chat into a remote console for Windows, macOS, and Linux devices. Pair each machine once with a temporary 6‑digit code, then monitor stats, run diagnostics, and get AI‑driven optimisation advice—all from your phone or desktop.

What it can do

- Collect real‑time telemetry: CPU (temp, per‑core, load), RAM, swap, GPU, battery, disk usage & health, network I/O, process list, storage scan, oldest files, exposed ports, failed logins, firewall/AV status.
- Execute remote actions: kill a process or an entire app, delete/unlink files, find paths, scan storage for large/old items.
- AI analysis (free Gemini/Groq) turns raw data into plain‑language insights and concrete recommendations (“Chrome is using 4 GB RAM – should I close it?”).
- Multi‑device support: pair many machines and switch context with /manage <id> / /stop_manage.
- Automatic persistence via systemd (Linux) or launchd (macOS) so the agent survives reboots.
- Zero‑cost: uses only free APIs, no subscriptions.

How it’s useful

- Quickly spot performance hogs or memory leaks without opening a terminal.
- Free disk space by locating and reviewing large/unused files.
- Check hardware health (temps, battery wear, disk SMART) to prevent overheating or failures.
- Get AI‑suggested optimisations tailored to your actual usage.
- Control all your computers from a single Telegram chat, anywhere you have internet.

Telegram Bot
🔗 https://t.me/device_master_bot

Core Commands (after pairing a device)

Command	Brief
- /start / /help	Shows welcome message and usage guide.
- /about	Summary of Devaster’s capabilities and telemetry collected.
- /add_device	Generates a 6‑digit pairing code to link a new machine.
- /devices	Lists all paired devices; shows the currently active one.
- /manage <device_id>	Locks subsequent commands to the specified device.
- /stop_manage	Unlocks device‑specific mode; next command will need a device selector.
- /stats	Returns a formatted hardware‑health snapshot (CPU, RAM, disk, battery, GPU, network, etc.).
- /processes	Shows top resource‑using processes (grouped by app name) with copyable PIDs.
- /storage	Lists large/old files and directories; highlights safe‑to‑delete candidates.
- /kill <pid>	Terminates the specified process ID (only works while managing a device).
- terminate <app_name>	Kills all processes matching the given app name (e.g., terminate spotify).
- kill tab using most resources in <app_name>	Finds the heaviest process of the named app and kills only that one.
- find me path of folder <folder_name>	Returns absolute paths matching the folder name (searches in $HOME).
- delete folder <folder_path>	Deletes the specified folder/file (restricted to inside your home directory).
- which apps are using most resources	Groups processes by app and shows the top consumers (name, total CPU+RAM, process count).
- why is my pc slow?	AI analysis of current stats/processes/storage with actionable advice.
- show failed logins	Displays count of failed OS login attempts in the last 24 h.
- show exposed ports	Lists listening ports bound to 0.0.0.0 or :: (externally reachable).
- show firewall status	Reports whether the OS firewall is active (Linux ufw/firewalld, macOS pf, Windows Defender Firewall).
- show antivirus status	Indicates if Windows Defender, macOS Gatekeeper/XProtect, or Linux AV is enabled.
- The bot will also respond to natural‑language variants of the above (e.g., “Top 3 apps using resources”, “Find path of folder v1”, “Delete folder /home/ubuntu/v1”, “How hot is my CPU?”).

Just open Telegram, start the bot, run /add_device to get your code, then run the Linux/macOS installer (or the Windows .exe) and paste the code when prompted. After that, you’re ready to manage your devices straight from chat.
