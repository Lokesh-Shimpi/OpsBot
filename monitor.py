import json
import socket
import ssl
import time
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import requests
from urllib.parse import urlparse

@dataclass
class MonitorResult:
    url: str
    name: str
    status_code: int | str
    latency_ms: float
    ssl_valid: bool
    ssl_days_left: int | None
    dns_ok: bool
    timestamp: str
    is_up: bool

def check_dns(hostname: str) -> bool:
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False

def check_ssl(hostname: str, port: int = 443) -> tuple[bool, int | None]:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                # e.g., 'notAfter': 'Nov 14 12:00:00 2024 GMT'
                if not cert or 'notAfter' not in cert:
                    return False, None
                expire_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                days_left = (expire_date - datetime.now(timezone.utc).replace(tzinfo=None)).days
                return True, days_left
    except Exception:
        return False, None

def check_url(target: dict) -> MonitorResult:
    url = target["url"]
    name = target["name"]
    expected_status = target.get("expected_status", 200)

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    
    dns_ok = check_dns(hostname)
    
    ssl_valid = False
    ssl_days_left = None
    if parsed.scheme == "https" and dns_ok:
        ssl_valid, ssl_days_left = check_ssl(hostname)

    status_code = "UNKNOWN"
    latency_ms = 0.0
    is_up = False

    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        status_code = response.status_code
        
        if status_code == expected_status:
            is_up = True
            
    except requests.exceptions.Timeout:
        status_code = "TIMEOUT"
    except requests.exceptions.ConnectionError as e:
        if "SSLError" in str(e):
            status_code = "SSL_FAILURE"
        else:
            status_code = "DOWN"
    except requests.exceptions.SSLError:
        status_code = "SSL_FAILURE"
    except Exception:
        status_code = "ERROR"

    if ssl_days_left is not None and ssl_days_left < 30:
        print(f"WARNING: SSL certificate for {hostname} expires in {ssl_days_left} days (< 30 days!).")

    return MonitorResult(
        url=url,
        name=name,
        status_code=status_code,
        latency_ms=latency_ms,
        ssl_valid=ssl_valid,
        ssl_days_left=ssl_days_left,
        dns_ok=dns_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
        is_up=is_up
    )

def load_targets(filepath: str = "config/targets.json") -> list:
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return []
    with open(filepath, "r") as f:
        return json.load(f)

def log_incident(result: MonitorResult, filepath: str = "data/incidents.json"):
    data = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    
    data.append(asdict(result))
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

def run_monitor():
    targets = load_targets()
    print(f"Monitoring {len(targets)} targets...")
    for target in targets:
        result = check_url(target)
        print(f"[{result.timestamp}] Checked {result.name} ({result.url}) -> UP: {result.is_up}, Status: {result.status_code}, Latency: {result.latency_ms}ms, SSL Valid: {result.ssl_valid}, DNS OK: {result.dns_ok}")
        log_incident(result)

if __name__ == "__main__":
    run_monitor()
