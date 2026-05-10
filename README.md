# 🤖 OpsBot - IT Helpdesk Automation CLI
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Status](https://img.shields.io/badge/status-Active-brightgreen)

## What is OpsBot?
OpsBot is a lightweight IT operations automation tool built to demonstrate ITIL-based incident management, automated alerting, and operational reporting — core skills required in enterprise L1 Support and DevOps operations roles.

## Features
- ⏱️ **Active Monitoring**: 60-second polling for HTTP status, latency, DNS, and SSL validity.
- 🚨 **ITIL-aligned Classification**: Auto-prioritizes incidents from P1 (Critical) to P4 (Low).
- 🎫 **Auto-Ticketing System**: Prevents alert fatigue with smart duplicate detection and ticket auto-generation.
- 📡 **Multi-Channel Alerting**: Broadcasts P1/P2/P3 alerts via HTML Email and Telegram with strict rate-limiting.
- 📊 **Daily Reports**: Auto-generates JSON and CSV summaries every 24 hours at 08:00 AM.
- 💻 **Live Terminal Dashboard**: Beautiful `rich`-powered live dashboard for monitoring at a glance.

## Architecture

```text
targets.json → Monitor Engine → Classifier → [P1/P2 → Alerter → Email/Telegram]
                                           → [All   → Ticketing → tickets.json]
                                           → [Daily → Reporter → reports/]
```

## Installation

```bash
git clone https://github.com/yourusername/opsbot.git
cd opsbot
pip install -r requirements.txt
cp config/settings.env.example config/settings.env
# Edit settings.env with your credentials
python main.py start
```

## Configuration Guide (`settings.env`)
- `EMAIL_SENDER`: The Gmail address sending the alerts.
- `EMAIL_PASSWORD`: An App Password generated from your Google Account security settings (not your regular password).
- `EMAIL_RECEIVER`: The destination inbox for alerts.
- `TELEGRAM_BOT_TOKEN`: The HTTP API token from BotFather.
- `TELEGRAM_CHAT_ID`: Your numeric chat ID from userinfobot.

### Telegram Bot Setup
1. Message **@BotFather** on Telegram.
2. Send `/newbot`, follow the prompts, and copy the provided HTTP API token.
3. Start your new bot on Telegram.
4. Message **@userinfobot** to get your numeric Chat ID.
5. Add both to `config/settings.env`.

## Screenshots

### Live Terminal Dashboard
![Dashboard Screenshot]()

### Sample Telegram Alert
![Telegram Alert]()

### Ticket List Output
![Ticket List]()

## ITIL Concepts Demonstrated
- **Incident Management**: Auto-detection and classification based on severity.
- **Problem Management**: Duplicate ticket detection prevents alert storms and links recurring incidents.
- **Knowledge Management**: Auto-generated reports for trend analysis.
- **Escalation Management**: P1/P2 auto-escalation flag built into the classification logic.
- **Change Management**: Append-only audit log of all monitoring events in `incidents.json`.
