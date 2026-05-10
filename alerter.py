import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv

# Load settings
load_dotenv("config/settings.env")

ALERT_HISTORY_FILE = "data/alert_history.json"

def load_alert_history():
    if not os.path.exists(ALERT_HISTORY_FILE):
        return {}
    try:
        with open(ALERT_HISTORY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_alert_history(history):
    with open(ALERT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def check_rate_limit(url, channel, cooldown_minutes):
    history = load_alert_history()
    key = f"{channel}_{url}"
    now = datetime.now(timezone.utc)
    
    if key in history:
        last_sent = datetime.fromisoformat(history[key])
        if now - last_sent < timedelta(minutes=cooldown_minutes):
            return False # Rate limited
    
    history[key] = now.isoformat()
    save_alert_history(history)
    return True

def send_email_alert(ticket):
    """Send an HTML email alert for P1 and P2 incidents."""
    if ticket["priority"] not in ["P1", "P2"]:
        return

    if not check_rate_limit(ticket["url"], "email", 10):
        print(f"Email rate limited for {ticket['url']}")
        return

    sender = os.environ.get("EMAIL_SENDER")
    password = os.environ.get("EMAIL_PASSWORD")
    receiver = os.environ.get("EMAIL_RECEIVER")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))

    if not sender or not password or not receiver or sender == "your@gmail.com":
        print(f"MOCK EMAIL ALERT: {ticket['title']}")
        return

    color = "red" if ticket["priority"] == "P1" else "orange"
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: white; background-color: {color}; padding: 10px; border-radius: 5px; display: inline-block;">
          {ticket['priority']} ALERT
        </h2>
        <h3>{ticket['title']}</h3>
        
        <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin-bottom: 20px;">
          <tr style="border-bottom: 1px solid #ddd;">
            <th style="text-align: left; padding: 8px;">Ticket ID</th>
            <td style="padding: 8px;">{ticket['ticket_id']}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd;">
            <th style="text-align: left; padding: 8px;">URL</th>
            <td style="padding: 8px;"><a href="{ticket['url']}">{ticket['url']}</a></td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd;">
            <th style="text-align: left; padding: 8px;">Reason</th>
            <td style="padding: 8px;">{ticket['reason']}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd;">
            <th style="text-align: left; padding: 8px;">Time</th>
            <td style="padding: 8px;">{ticket['created_at']}</td>
          </tr>
        </table>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid {color};">
          <strong>Suggested Action:</strong><br>
          {ticket['suggested_action']}
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[OpsBot] {ticket['priority']} ALERT - {ticket['url']}"
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print(f"Sent email alert for {ticket['ticket_id']}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def send_telegram_alert(ticket):
    """Send a Markdown alert to Telegram for P1, P2, P3 incidents."""
    if ticket["priority"] not in ["P1", "P2", "P3"]:
        return

    if not check_rate_limit(ticket["url"], "telegram", 5):
        print(f"Telegram rate limited for {ticket['url']}")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id or token == "your_bot_token":
        print(f"MOCK TELEGRAM ALERT: {ticket['title']}")
        return

    icon = "🔴" if ticket["priority"] == "P1" else "🟠" if ticket["priority"] == "P2" else "🟡"
    escalate_str = "YES" if ticket["escalated"] else "NO"

    text = f"""{icon} *{ticket['title']}*

📋 Ticket: {ticket['ticket_id']}
🌐 URL: {ticket['url']}
⏱ Reason: {ticket['reason']}
🕐 Time: {ticket['created_at']}

❗ Action: {ticket['suggested_action']}
📌 Escalate: {escalate_str}"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print(f"Sent Telegram alert for {ticket['ticket_id']}")
        else:
            print(f"Failed to send Telegram alert: {r.text}")
    except Exception as e:
        print(f"Failed to send Telegram: {e}")

def send_alerts(ticket):
    send_email_alert(ticket)
    send_telegram_alert(ticket)

if __name__ == "__main__":
    # Test alert logic with mock ticket
    mock_ticket = {
        "ticket_id": "OPS-2024-001",
        "title": "P1: myapp.com is DOWN",
        "priority": "P1",
        "status": "OPEN",
        "url": "https://myapp.com",
        "reason": "Connection refused",
        "suggested_action": "Immediately check server status.",
        "created_at": "2024-01-15T10:30:00",
        "escalated": True
    }
    
    print("Attempt 1 (Should trigger mock alerts):")
    send_alerts(mock_ticket)
    
    print("\nAttempt 2 (Should be rate limited):")
    send_alerts(mock_ticket)
