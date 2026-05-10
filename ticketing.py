import json
import os
from datetime import datetime, timezone
from classifier import Classification
from monitor import MonitorResult

TICKETS_FILE = "data/tickets.json"

def load_tickets():
    if not os.path.exists(TICKETS_FILE):
        return []
    try:
        with open(TICKETS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=2)

def generate_ticket_id(tickets):
    year = datetime.now(timezone.utc).year
    # Find max ID for current year
    max_num = 0
    prefix = f"OPS-{year}-"
    for t in tickets:
        tid = t.get("ticket_id", "")
        if tid.startswith(prefix):
            try:
                num = int(tid.split("-")[-1])
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"{prefix}{max_num + 1:03d}"

def process_incident(result: MonitorResult, classification: Classification):
    """
    If classification is P1 or P2, auto-create or update an existing ticket.
    """
    if classification.priority not in ["P1", "P2"]:
        return None

    tickets = load_tickets()

    # Duplicate detection: Find OPEN ticket for same URL
    for t in tickets:
        if t["url"] == result.url and t["status"] in ["OPEN", "IN_PROGRESS"]:
            # Update existing ticket
            t["occurrence_count"] = t.get("occurrence_count", 1) + 1
            t["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            save_tickets(tickets)
            
            # Trigger alerts (rate limited inside alerter)
            from alerter import send_alerts
            send_alerts(t)
            return t

    # Create new ticket
    ticket = {
        "ticket_id": generate_ticket_id(tickets),
        "title": f"{classification.priority}: {result.name} is DOWN" if not result.is_up else f"{classification.priority}: Issue with {result.name}",
        "priority": classification.priority,
        "status": "OPEN",
        "url": result.url,
        "reason": classification.reason,
        "suggested_action": classification.suggested_action,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None,
        "resolution_notes": None,
        "escalated": classification.escalate,
        "occurrence_count": 1
    }
    
    # Customize title if it's explicitly DOWN
    if classification.reason == "Site completely DOWN or DNS resolution failure" or classification.reason == "Connection TIMEOUT":
        ticket["title"] = f"{classification.priority}: {result.name} is DOWN"

    tickets.append(ticket)
    save_tickets(tickets)
    
    from alerter import send_alerts
    send_alerts(ticket)
    
    return ticket

def get_open_tickets():
    return [t for t in load_tickets() if t["status"] in ["OPEN", "IN_PROGRESS"]]

def get_all_tickets():
    return load_tickets()

def get_ticket(ticket_id):
    for t in load_tickets():
        if t["ticket_id"] == ticket_id:
            return t
    return None

def resolve_ticket(ticket_id, notes):
    tickets = load_tickets()
    for t in tickets:
        if t["ticket_id"] == ticket_id:
            if t["status"] in ["RESOLVED", "CLOSED"]:
                return False, "Ticket is already resolved or closed."
            t["status"] = "RESOLVED"
            t["resolved_at"] = datetime.now(timezone.utc).isoformat()
            t["resolution_notes"] = notes
            save_tickets(tickets)
            return True, "Ticket marked as resolved."
    return False, "Ticket not found."

if __name__ == "__main__":
    # Test Ticket Generation
    r = MonitorResult("https://myapp.com", "My App", "TIMEOUT", 0, False, None, True, datetime.now(timezone.utc).isoformat(), False)
    c = Classification("P1", "Connection TIMEOUT", "Check server", True)
    t1 = process_incident(r, c)
    print("Created:", t1["ticket_id"])
    
    # Test duplicate detection
    t2 = process_incident(r, c)
    print("Duplicate occurrence_count:", t2["occurrence_count"])
