# OpsBot - IT Helpdesk Automation CLI Tool

OpsBot is a Python-based CLI tool designed for IT Helpdesk Automation. It monitors URLs, classifies incidents by severity, auto-generates tickets, sends alerts, and produces daily summary reports.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure targets in `config/targets.json`:
   ```json
   [
     {"name": "My App", "url": "https://myapp.com", "expected_status": 200},
     {"name": "API Server", "url": "https://api.myapp.com/health", "expected_status": 200},
     {"name": "Google", "url": "https://google.com", "expected_status": 200}
   ]
   ```

## Modules
- **Module 1**: `monitor.py` - URL monitoring engine

## Usage

For now, you can run the monitor engine directly:
```bash
python monitor.py
```
