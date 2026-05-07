import hashlib
import hmac
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import paho.mqtt.client as mqtt
import psutil
import requests
from dotenv import load_dotenv

try:
    import GPUtil
except Exception:
    GPUtil = None


ENV_PATH = Path(os.getenv("DEVASTER_ENV_FILE", str(Path(__file__).resolve().parent / ".env")))
load_dotenv(dotenv_path=ENV_PATH)

CONFIG_PATH = Path(os.getenv("DEVASTER_CONFIG_PATH", str(Path.home() / ".devaster_client.json")))
DEFAULT_BROKER = os.getenv("DEVASTER_MQTT_BROKER", "broker.hivemq.com")
DEFAULT_PORT = int(os.getenv("DEVASTER_MQTT_PORT", "1883"))
DEFAULT_TLS = os.getenv("DEVASTER_MQTT_USE_TLS", "0") == "1"
DEFAULT_NAMESPACE = os.getenv("DEVASTER_MQTT_NAMESPACE", "devaster")
PAIRING_TIMEOUT = 180


def canonical_payload(payload: Dict[str, Any]) -> bytes:
    clean = {k: v for k, v in payload.items() if k != "signature"}
    return json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_payload(device_key: str, payload: Dict[str, Any]) -> str:
    return hmac.new(device_key.encode("utf-8"), canonical_payload(payload), hashlib.sha256).hexdigest()


def verify_signature(device_key: str, payload: Dict[str, Any]) -> bool:
    provided = payload.get("signature", "")
    if not provided:
        return False
    expected = sign_payload(device_key, payload)
    return hmac.compare_digest(provided, expected)


def get_device_id() -> str:
    mac = uuid.getnode()
    host = socket.gethostname()
    raw = f"{host}-{mac}-{platform.system()}-{platform.machine()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except Exception:
        pass


class DevasterClient:
    def __init__(self) -> None:
        self.device_id = get_device_id()
        self.device_name = socket.gethostname()
        self.platform_name = f"{platform.system()} {platform.release()}"
        self.cfg = load_config()
        self.user_id = self.cfg.get("user_id")
        self.device_key = self.cfg.get("device_key", "")
        self.namespace = self.cfg.get("namespace", DEFAULT_NAMESPACE)
        self.broker = self.cfg.get("broker", DEFAULT_BROKER)
        self.port = int(self.cfg.get("port", DEFAULT_PORT))
        self.use_tls = bool(self.cfg.get("tls", DEFAULT_TLS))
        self.pairing_done = threading.Event()
        self.pairing_response: Dict[str, Any] = {}
        self.client = mqtt.Client(client_id=f"devaster-client-{self.device_id}")
        if self.use_tls:
            self.client.tls_set()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def connect(self) -> None:
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        if rc != 0:
            print(f"MQTT connect failed: {rc}")
            return
        if self.user_id and self.device_key:
            cmd_topic = f"{self.namespace}/u/{self.user_id}/d/{self.device_id}/cmd"
            client.subscribe(cmd_topic)
        print("Client connected to MQTT.")

    def on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        topic = msg.topic
        if topic.startswith(f"{self.namespace}/pairing/response/"):
            self.pairing_response = payload
            self.pairing_done.set()
            return
        if not (self.user_id and self.device_key):
            return
        if not verify_signature(self.device_key, payload):
            self.send_error(payload.get("request_id", ""), "invalid_signature")
            return
        request_id = payload.get("request_id", "")
        action = payload.get("action", "")
        params = payload.get("params", {}) or {}
        handler = {
            "get_stats": self.handle_get_stats,
            "get_processes": self.handle_get_processes,
            "kill_process": self.handle_kill_process,
            "kill_app_processes": self.handle_kill_app_processes,
            "kill_heaviest_process_by_name": self.handle_kill_heaviest_process_by_name,
            "scan_storage": self.handle_scan_storage,
            "delete_path": self.handle_delete_path,
            "find_paths": self.handle_find_paths,
            "get_oldest_entries": self.handle_get_oldest_entries,
        }.get(action)
        if not handler:
            self.send_error(request_id, "unknown_action")
            return
        try:
            data = handler(params)
            self.send_response(request_id, True, data=data)
        except Exception as exc:
            self.send_error(request_id, str(exc))

    def send_response(self, request_id: str, ok: bool, data: Dict[str, Any] | None = None, error: str = "") -> None:
        payload = {
            "request_id": request_id,
            "ok": ok,
            "data": data or {},
            "error": error,
            "ts": int(time.time()),
        }
        payload["signature"] = sign_payload(self.device_key, payload)
        topic = f"{self.namespace}/u/{self.user_id}/d/{self.device_id}/resp"
        self.client.publish(topic, json.dumps(payload))

    def send_error(self, request_id: str, error: str) -> None:
        self.send_response(request_id, False, error=error)

    def send_heartbeat(self) -> None:
        if not self.user_id:
            return
        topic = f"{self.namespace}/u/{self.user_id}/d/{self.device_id}/heartbeat"
        payload = {"ts": int(time.time())}
        self.client.publish(topic, json.dumps(payload))

    def pair(self, pairing_code: str) -> None:
        request_id = secrets.token_hex(8)
        reply_topic = f"{self.namespace}/pairing/response/{request_id}"
        self.client.subscribe(reply_topic)
        payload = {
            "pairing_code": pairing_code.strip(),
            "request_id": request_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
            "platform": self.platform_name,
        }
        self.client.publish(f"{self.namespace}/pairing/request", json.dumps(payload))
        if not self.pairing_done.wait(timeout=PAIRING_TIMEOUT):
            raise TimeoutError("Pairing timed out.")
        resp = self.pairing_response
        if not resp.get("ok"):
            raise RuntimeError(f"Pairing failed: {resp.get('error', 'unknown_error')}")
        self.user_id = int(resp["user_id"])
        self.device_key = str(resp["device_key"])
        self.namespace = str(resp.get("namespace", self.namespace))
        self.broker = str(resp.get("broker", self.broker))
        self.port = int(resp.get("port", self.port))
        self.use_tls = bool(resp.get("tls", self.use_tls))
        save_config(
            {
                "user_id": self.user_id,
                "device_id": self.device_id,
                "device_key": self.device_key,
                "namespace": self.namespace,
                "broker": self.broker,
                "port": self.port,
                "tls": self.use_tls,
            }
        )
        self.client.unsubscribe(reply_topic)
        self.client.subscribe(f"{self.namespace}/u/{self.user_id}/d/{self.device_id}/cmd")

    def run(self) -> None:
        self.connect()
        if not (self.user_id and self.device_key):
            code = input("Enter 6-digit pairing code from Telegram (/add_device): ").strip()
            self.pair(code)
            print("Pairing complete.")
        if os.getenv("DEVASTER_PAIR_ONLY", "0") == "1":
            return
        if os.getenv("DEVASTER_ENABLE_PERSISTENCE", "1") == "1":
            setup_persistence()
        while True:
            self.send_heartbeat()
            time.sleep(30)

    def handle_get_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=0.25)
        cpu_per_core = [round(v, 1) for v in psutil.cpu_percent(interval=None, percpu=True)]
        cpu_temp_c = self._get_cpu_temp_c()
        cpu_freq = psutil.cpu_freq()
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()
        net_if = psutil.net_if_stats()
        users = psutil.users()
        users_count = len({u.name for u in users if getattr(u, "name", None)})
        conn_summary = {"total": 0, "established": 0, "listening": 0}
        try:
            conns = psutil.net_connections(kind="inet")
            conn_summary["total"] = len(conns)
            conn_summary["established"] = sum(1 for c in conns if c.status == "ESTABLISHED")
            conn_summary["listening"] = sum(1 for c in conns if c.status == "LISTEN")
        except Exception:
            pass
        partitions = []
        for p in psutil.disk_partitions(all=False):
            try:
                du = psutil.disk_usage(p.mountpoint)
                partitions.append(
                    {
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "used_gb": round(du.used / (1024**3), 2),
                        "total_gb": round(du.total / (1024**3), 2),
                        "percent": du.percent,
                    }
                )
            except Exception:
                continue
        load_avg = None
        if hasattr(os, "getloadavg"):
            try:
                la = os.getloadavg()
                load_avg = {"1m": round(la[0], 2), "5m": round(la[1], 2), "15m": round(la[2], 2)}
            except Exception:
                load_avg = None
        battery_info = None
        try:
            batt = psutil.sensors_battery()
            if batt:
                battery_info = {
                    "percent": batt.percent,
                    "plugged": batt.power_plugged,
                    "secsleft": batt.secsleft,
                }
        except Exception:
            battery_info = None
        gpus = self._collect_gpu_stats()
        exposed_ports = self._get_exposed_ports()
        security = self._get_security_posture()
        battery_health = self._get_battery_health()
        disk_health = self._get_disk_health()
        failed_login_24h = self._get_failed_logins_24h()
        return {
            "device_name": self.device_name,
            "platform": self.platform_name,
            "uptime_seconds": int(time.time() - psutil.boot_time()),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_percent": cpu_percent,
            "cpu_per_core_percent": cpu_per_core,
            "cpu_frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
            "cpu_temp_c": cpu_temp_c,
            "process_count": len(psutil.pids()),
            "ram": {
                "total_mb": round(vm.total / (1024 * 1024), 2),
                "used_mb": round(vm.used / (1024 * 1024), 2),
                "available_mb": round(vm.available / (1024 * 1024), 2),
                "percent": vm.percent,
            },
            "swap": {
                "total_mb": round(swap.total / (1024 * 1024), 2),
                "used_mb": round(swap.used / (1024 * 1024), 2),
                "percent": swap.percent,
            },
            "disk_root": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": disk.percent,
            },
            "partitions": partitions[:6],
            "disk_io": {
                "read_mb": round((disk_io.read_bytes if disk_io else 0) / (1024 * 1024), 2),
                "write_mb": round((disk_io.write_bytes if disk_io else 0) / (1024 * 1024), 2),
                "read_count": int(disk_io.read_count) if disk_io else 0,
                "write_count": int(disk_io.write_count) if disk_io else 0,
            },
            "network_io": {
                "sent_mb": round((net_io.bytes_sent if net_io else 0) / (1024 * 1024), 2),
                "recv_mb": round((net_io.bytes_recv if net_io else 0) / (1024 * 1024), 2),
                "packets_sent": int(net_io.packets_sent) if net_io else 0,
                "packets_recv": int(net_io.packets_recv) if net_io else 0,
            },
            "network_interfaces_up": sorted([name for name, st in net_if.items() if st.isup])[:10],
            "logged_in_users": sorted(list({u.name for u in users if getattr(u, "name", None)}))[:10],
            "logged_in_users_count": users_count,
            "network_connections": conn_summary,
            "load_average": load_avg,
            "security_posture": security,
            "failed_login_attempts_24h": failed_login_24h,
            "exposed_listening_ports": exposed_ports,
            "battery_health": battery_health,
            "disk_health": disk_health,
            "battery": battery_info,
            "gpus": gpus,
        }

    def _get_cpu_temp_c(self) -> float | None:
        try:
            temps = psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            temps = {}
        if temps:
            for key in ("coretemp", "k10temp", "cpu_thermal", "acpitz", "soc_thermal"):
                entries = temps.get(key) or []
                values = [e.current for e in entries if getattr(e, "current", None) is not None]
                if values:
                    return round(sum(values) / len(values), 1)
            for entries in temps.values():
                values = [e.current for e in entries if getattr(e, "current", None) is not None]
                if values:
                    return round(sum(values) / len(values), 1)
        for zone in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
            try:
                raw = zone.read_text(encoding="utf-8").strip()
                val = float(raw)
                if val > 1000:
                    val = val / 1000.0
                if 0 < val < 130:
                    return round(val, 1)
            except Exception:
                continue
        return None

    def _collect_gpu_stats(self) -> List[Dict[str, Any]]:
        gpus: List[Dict[str, Any]] = []
        if GPUtil:
            try:
                for g in GPUtil.getGPUs():
                    gpus.append(
                        {
                            "name": g.name,
                            "load_percent": round(g.load * 100, 2),
                            "memory_used_mb": g.memoryUsed,
                            "memory_total_mb": g.memoryTotal,
                            "temperature_c": g.temperature,
                        }
                    )
            except Exception:
                gpus = []
        if gpus:
            return gpus
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    text=True,
                    timeout=8,
                )
                for line in out.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 5:
                        gpus.append(
                            {
                                "name": parts[0],
                                "load_percent": float(parts[1]),
                                "memory_used_mb": float(parts[2]),
                                "memory_total_mb": float(parts[3]),
                                "temperature_c": float(parts[4]),
                            }
                        )
            except Exception:
                pass
        if gpus:
            return gpus
        if shutil.which("lspci"):
            try:
                out = subprocess.check_output(["lspci"], text=True, timeout=8)
                for line in out.splitlines():
                    lower = line.lower()
                    if "vga" in lower or "3d controller" in lower:
                        gpus.append(
                            {
                                "name": line.split(": ", 1)[-1],
                                "load_percent": None,
                                "memory_used_mb": None,
                                "memory_total_mb": None,
                                "temperature_c": None,
                            }
                        )
            except Exception:
                pass
        return gpus

    def handle_get_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(params.get("limit", 30))
        candidates = []
        for proc in psutil.process_iter(attrs=["pid", "name", "username", "memory_info", "create_time"]):
            try:
                info = proc.info
                rss = info["memory_info"].rss if info.get("memory_info") else 0
                io = proc.io_counters()
                conn_count = 0
                try:
                    conn_count = len(proc.connections(kind="inet"))
                except Exception:
                    conn_count = 0
                candidates.append(
                    {
                        "proc": proc,
                        "pid": info["pid"],
                        "name": info.get("name") or "",
                        "app_group": self._normalize_app_name(info.get("name") or ""),
                        "user": info.get("username") or "",
                        "cpu_percent": 0.0,
                        "memory_mb": round(rss / (1024 * 1024), 2),
                        "io_read_mb": round((io.read_bytes if io else 0) / (1024 * 1024), 2),
                        "io_write_mb": round((io.write_bytes if io else 0) / (1024 * 1024), 2),
                        "connection_count": conn_count,
                        "uptime_sec": int(time.time() - info.get("create_time", time.time())),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue
        for p in candidates:
            try:
                p["proc"].cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        time.sleep(0.35)
        procs = []
        for p in candidates:
            proc = p.pop("proc")
            try:
                p["cpu_percent"] = round(proc.cpu_percent(None), 2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                p["cpu_percent"] = 0.0
            procs.append(p)
        procs.sort(key=lambda x: (x["cpu_percent"], x["memory_mb"]), reverse=True)
        return {"top_processes": procs[:limit], "count": len(procs)}

    def handle_kill_app_processes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_app_name(str(params.get("name", "")).strip())
        if not query:
            raise ValueError("name is required")
        matched: List[psutil.Process] = []
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            try:
                if proc.pid == os.getpid():
                    continue
                proc_name = self._normalize_app_name(proc.info.get("name") or "")
                if query in proc_name:
                    matched.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not matched:
            raise ValueError("no matching process found")
        killed_pids = []
        for proc in matched:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                killed_pids.append(proc.pid)
            except psutil.TimeoutExpired:
                try:
                    proc.kill()
                    killed_pids.append(proc.pid)
                except Exception:
                    pass
            except Exception:
                continue
        return {"query": query, "killed_pids": killed_pids, "killed_count": len(killed_pids)}

    def handle_kill_heaviest_process_by_name(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_app_name(str(params.get("name", "")).strip())
        if not query:
            raise ValueError("name is required")
        matches: List[psutil.Process] = []
        for proc in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
            try:
                proc_name = self._normalize_app_name(proc.info.get("name") or "")
                if query in proc_name:
                    proc.cpu_percent(None)
                    matches.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not matches:
            raise ValueError("no matching process found")
        time.sleep(0.3)
        scored = []
        for proc in matches:
            try:
                cpu = proc.cpu_percent(None)
                mem = proc.memory_info().rss / (1024 * 1024)
                scored.append((cpu, mem, proc))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if not scored:
            raise ValueError("no accessible matching process found")
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        cpu, mem, target = scored[0]
        try:
            target.terminate()
            target.wait(timeout=3)
            status = "terminated"
        except psutil.TimeoutExpired:
            target.kill()
            status = "killed"
        return {
            "query": query,
            "pid": target.pid,
            "name": target.name(),
            "cpu_percent": round(cpu, 2),
            "memory_mb": round(mem, 2),
            "status": status,
        }

    def _normalize_app_name(self, name: str) -> str:
        n = (name or "").strip().lower()
        if n.endswith(".exe"):
            n = n[:-4]
        return n

    def _get_exposed_ports(self) -> List[Dict[str, Any]]:
        exposed = []
        try:
            for c in psutil.net_connections(kind="inet"):
                if c.status != "LISTEN" or not c.laddr:
                    continue
                ip = c.laddr.ip
                if ip in {"127.0.0.1", "::1"}:
                    continue
                exposed.append({"ip": ip, "port": c.laddr.port, "pid": c.pid})
        except Exception:
            return []
        return exposed[:50]

    def _get_security_posture(self) -> Dict[str, Any]:
        os_name = platform.system()
        posture = {"firewall": "unknown", "antivirus": "unknown"}
        if os_name == "Linux":
            if shutil.which("ufw"):
                try:
                    out = subprocess.check_output(["ufw", "status"], text=True, timeout=6)
                    posture["firewall"] = "enabled" if "Status: active" in out else "disabled"
                except Exception:
                    pass
            elif shutil.which("firewall-cmd"):
                try:
                    out = subprocess.check_output(["firewall-cmd", "--state"], text=True, timeout=6).strip()
                    posture["firewall"] = "enabled" if out == "running" else "disabled"
                except Exception:
                    pass
            posture["antivirus"] = "unknown"
        elif os_name == "Darwin":
            try:
                out = subprocess.check_output(
                    ["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"],
                    text=True,
                    timeout=6,
                )
                posture["firewall"] = "enabled" if "enabled" in out.lower() else "disabled"
            except Exception:
                pass
            try:
                out = subprocess.check_output(["spctl", "--status"], text=True, timeout=6).strip().lower()
                posture["antivirus"] = "gatekeeper_on" if "assessments enabled" in out else "gatekeeper_off"
            except Exception:
                pass
        elif os_name == "Windows":
            try:
                out = subprocess.check_output(
                    ["powershell", "-Command", "(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq 'True'}).Count"],
                    text=True,
                    timeout=8,
                ).strip()
                posture["firewall"] = "enabled" if out and out != "0" else "disabled"
            except Exception:
                pass
            try:
                out = subprocess.check_output(
                    ["powershell", "-Command", "(Get-MpComputerStatus).AntivirusEnabled"],
                    text=True,
                    timeout=8,
                ).strip().lower()
                posture["antivirus"] = "enabled" if "true" in out else "disabled"
            except Exception:
                pass
        return posture

    def _get_failed_logins_24h(self) -> int:
        os_name = platform.system()
        if os_name == "Linux" and shutil.which("journalctl"):
            try:
                out = subprocess.check_output(
                    ["journalctl", "--since", "24 hours ago", "-o", "cat"],
                    text=True,
                    timeout=10,
                    stderr=subprocess.DEVNULL,
                )
                patterns = ("Failed password", "authentication failure", "FAILED LOGIN")
                return sum(out.count(p) for p in patterns)
            except Exception:
                return 0
        if os_name == "Windows":
            try:
                out = subprocess.check_output(
                    [
                        "powershell",
                        "-Command",
                        "(Get-WinEvent -FilterHashtable @{LogName='Security';ID=4625;StartTime=(Get-Date).AddHours(-24)}).Count",
                    ],
                    text=True,
                    timeout=12,
                ).strip()
                return int(out) if out.isdigit() else 0
            except Exception:
                return 0
        return 0

    def _get_battery_health(self) -> Dict[str, Any]:
        os_name = platform.system()
        if os_name == "Linux":
            for base in Path("/sys/class/power_supply").glob("BAT*"):
                try:
                    full = float((base / "charge_full").read_text().strip())
                    design = float((base / "charge_full_design").read_text().strip())
                    cycle = (base / "cycle_count").read_text().strip() if (base / "cycle_count").exists() else None
                    wear = round((1 - (full / design)) * 100, 2) if design > 0 else None
                    return {"cycle_count": int(cycle) if cycle and cycle.isdigit() else None, "wear_percent": wear}
                except Exception:
                    continue
        if os_name == "Darwin":
            try:
                out = subprocess.check_output(["system_profiler", "SPPowerDataType"], text=True, timeout=10)
                cyc = re.search(r"Cycle Count:\s+(\d+)", out)
                cond = re.search(r"Condition:\s+(.+)", out)
                return {
                    "cycle_count": int(cyc.group(1)) if cyc else None,
                    "condition": cond.group(1).strip() if cond else None,
                }
            except Exception:
                pass
        return {}

    def _get_disk_health(self) -> Dict[str, Any]:
        os_name = platform.system()
        if os_name in {"Linux", "Darwin"} and shutil.which("smartctl"):
            try:
                out = subprocess.check_output(["smartctl", "-H", "/dev/sda"], text=True, timeout=8, stderr=subprocess.DEVNULL)
                if "PASSED" in out:
                    return {"smart_status": "passed"}
                if "FAILED" in out:
                    return {"smart_status": "failed"}
            except Exception:
                pass
        return {"smart_status": "unknown"}

    def handle_kill_process(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pid = int(params["pid"])
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
            result = "terminated"
        except psutil.TimeoutExpired:
            proc.kill()
            result = "killed"
        return {"pid": pid, "status": result}

    def handle_scan_storage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        min_size_mb = int(params.get("min_size_mb", 100))
        older_than_days = int(params.get("older_than_days", 60))
        cutoff = datetime.now() - timedelta(days=older_than_days)
        roots = self._scan_roots()
        large_files = []
        old_dirs = []
        for root in roots:
            if not os.path.exists(root):
                continue
            for base, dirs, files in os.walk(root, topdown=True):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
                try:
                    st = os.stat(base)
                    mtime = datetime.fromtimestamp(st.st_mtime)
                    if mtime < cutoff:
                        old_dirs.append({"path": base, "modified": mtime.isoformat()})
                except Exception:
                    pass
                for f in files:
                    path = os.path.join(base, f)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    size_mb = st.st_size / (1024 * 1024)
                    if size_mb < min_size_mb:
                        continue
                    mtime = datetime.fromtimestamp(st.st_mtime)
                    large_files.append(
                        {
                            "path": path,
                            "size_mb": round(size_mb, 2),
                            "modified": mtime.isoformat(),
                        }
                    )
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        return {
            "large_files": large_files[:100],
            "old_directories": old_dirs[:100],
            "scan_roots": roots,
            "thresholds": {"min_size_mb": min_size_mb, "older_than_days": older_than_days},
        }

    def handle_delete_path(self, params: Dict[str, Any]) -> Dict[str, Any]:
        raw_path = str(params.get("path", "")).strip()
        if not raw_path:
            raise ValueError("path is required")
        target = Path(raw_path).expanduser().resolve()
        home = Path.home().resolve()
        if target == home or target == Path("/"):
            raise ValueError("refusing to delete protected path")
        if home not in target.parents and target != home:
            raise ValueError("path must be inside home directory")
        if not target.exists():
            raise ValueError("path does not exist")
        if target.is_dir():
            shutil.rmtree(target)
            return {"path": str(target), "deleted": True, "type": "directory"}
        target.unlink()
        return {"path": str(target), "deleted": True, "type": "file"}

    def handle_find_paths(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = str(params.get("query", "")).strip().lower()
        if not query:
            raise ValueError("query is required")
        limit = int(params.get("limit", 12))
        roots = self._scan_roots()
        matches: List[str] = []
        for root in roots:
            if not os.path.exists(root):
                continue
            for base, dirs, files in os.walk(root, topdown=True):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
                for d in dirs:
                    if query in d.lower():
                        matches.append(os.path.join(base, d))
                        if len(matches) >= limit:
                            return {"query": query, "matches": matches}
                for f in files:
                    if query in f.lower():
                        matches.append(os.path.join(base, f))
                        if len(matches) >= limit:
                            return {"query": query, "matches": matches}
        return {"query": query, "matches": matches}

    def handle_get_oldest_entries(self, params: Dict[str, Any]) -> Dict[str, Any]:
        roots = self._scan_roots()
        oldest_file = None
        oldest_dir = None
        for root in roots:
            if not os.path.exists(root):
                continue
            for base, dirs, files in os.walk(root, topdown=True):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]
                try:
                    st_base = os.stat(base)
                    base_mtime = st_base.st_mtime
                    if oldest_dir is None or base_mtime < oldest_dir["mtime"]:
                        oldest_dir = {"path": base, "mtime": base_mtime}
                except Exception:
                    pass
                for f in files:
                    path = os.path.join(base, f)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    mtime = st.st_mtime
                    if oldest_file is None or mtime < oldest_file["mtime"]:
                        oldest_file = {"path": path, "mtime": mtime}
        now = time.time()
        result = {"scan_roots": roots}
        if oldest_file:
            result["oldest_file"] = {
                "path": oldest_file["path"],
                "modified": datetime.fromtimestamp(oldest_file["mtime"]).isoformat(),
                "age_days": round((now - oldest_file["mtime"]) / 86400.0, 1),
            }
        if oldest_dir:
            result["oldest_directory"] = {
                "path": oldest_dir["path"],
                "modified": datetime.fromtimestamp(oldest_dir["mtime"]).isoformat(),
                "age_days": round((now - oldest_dir["mtime"]) / 86400.0, 1),
            }
        return result

    def _scan_roots(self) -> List[str]:
        if platform.system() == "Windows":
            roots = []
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                p = f"{letter}:\\"
                if os.path.exists(p):
                    roots.append(p)
            return roots[:3] or ["C:\\"]
        home = str(Path.home())
        return [home]


def setup_persistence() -> None:
    current = Path(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]).resolve()
    os_name = platform.system()
    if os_name == "Windows":
        startup_dir = Path(os.getenv("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup_dir.mkdir(parents=True, exist_ok=True)
        bat_path = startup_dir / "devaster_agent.bat"
        cmd = f'"{sys.executable}" "{current}"\n'
        if not bat_path.exists() or bat_path.read_text(encoding="utf-8", errors="ignore") != cmd:
            bat_path.write_text(cmd, encoding="utf-8")
    elif os_name == "Darwin":
        launch_dir = Path.home() / "Library" / "LaunchAgents"
        launch_dir.mkdir(parents=True, exist_ok=True)
        plist = launch_dir / "com.devaster.agent.plist"
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.devaster.agent</string>
<key>ProgramArguments</key><array><string>{sys.executable}</string><string>{current}</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>{str(Path.home() / 'devaster.log')}</string>
<key>StandardErrorPath</key><string>{str(Path.home() / 'devaster.err.log')}</string>
</dict></plist>"""
        plist.write_text(content, encoding="utf-8")
        subprocess.run(["launchctl", "unload", str(plist)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["launchctl", "load", str(plist)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_path = service_dir / "devaster-agent.service"
        env_file = current.parent / ".env"
        service_content = f"""[Unit]
Description=Devaster Agent

[Service]
Environment="DEVASTER_ENV_FILE={env_file}"
ExecStart=/bin/bash -lc '"{sys.executable}" "{current}"'
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""
        service_path.write_text(service_content, encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "--user", "enable", "--now", "devaster-agent.service"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    client = DevasterClient()
    client.run()


if __name__ == "__main__":
    main()
