import os
import json
import subprocess
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import ticketing
import monitor
import alerter
import reporter

console = Console()

TARGETS_FILE = "config/targets.json"
ENV_FILE = "config/settings.env"
PID_FILE = ".opsbot.pid"

def run_onboarding():
    console.print(Panel.fit("[bold cyan]Welcome to OpsBot![/bold cyan]\nIT Helpdesk Automation CLI Tool"))
    console.print("Let's set up your first target.")
    
    os.makedirs("config", exist_ok=True)
    
    name = click.prompt("Enter a name for the target (e.g., Google)")
    url = click.prompt("Enter the URL to monitor (e.g., https://google.com)")
    
    targets = [{"name": name, "url": url, "expected_status": 200}]
    with open(TARGETS_FILE, "w") as f:
        json.dump(targets, f, indent=2)
        
    console.print("\nNow let's configure alerting (optional).")
    email_sender = click.prompt("Gmail Sender Email", default="your@gmail.com")
    email_pass = click.prompt("Gmail App Password", default="your_app_password", hide_input=True)
    email_recv = click.prompt("Alert Receiver Email", default="alert@yourdomain.com")
    bot_token = click.prompt("Telegram Bot Token", default="your_bot_token", hide_input=True)
    chat_id = click.prompt("Telegram Chat ID", default="your_chat_id")
    
    env_content = f"""# Gmail SMTP Settings
EMAIL_SENDER={email_sender}
EMAIL_PASSWORD={email_pass}
EMAIL_RECEIVER={email_recv}
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN={bot_token}
TELEGRAM_CHAT_ID={chat_id}
"""
    with open(ENV_FILE, "w") as f:
        f.write(env_content)
        
    console.print("[green]Setup complete![/green]")
    console.print("Starting background monitor...")
    start_background()

def start_background():
    if os.path.exists(PID_FILE):
        console.print("[yellow]OpsBot is already running.[/yellow]")
        return
        
    # Launch scheduler.py as a background process
    if os.name == 'nt':
        CREATE_NO_WINDOW = 0x08000000
        p = subprocess.Popen(["python", "scheduler.py"], creationflags=CREATE_NO_WINDOW)
    else:
        p = subprocess.Popen(["python", "scheduler.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
        
    with open(PID_FILE, "w") as f:
        f.write(str(p.pid))
    console.print(f"[green]OpsBot started in background (PID {p.pid}).[/green]")

@click.group()
def cli():
    """OpsBot - IT Helpdesk Automation CLI Tool"""
    if not os.path.exists(TARGETS_FILE) and click.get_current_context().invoked_subcommand != 'onboard':
        run_onboarding()

@cli.command()
def onboard():
    """Force run the onboarding wizard."""
    run_onboarding()

@cli.command()
def start():
    """Start monitoring all targets in background."""
    start_background()

@cli.command()
def stop():
    """Stop background monitoring."""
    if not os.path.exists(PID_FILE):
        console.print("[yellow]OpsBot is not running.[/yellow]")
        return
        
    with open(PID_FILE, "r") as f:
        pid = f.read().strip()
        
    try:
        if os.name == 'nt':
            subprocess.run(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.system(f"kill {pid}")
        console.print(f"[green]Stopped OpsBot (PID {pid}).[/green]")
    except Exception as e:
        console.print(f"[red]Error stopping OpsBot: {e}[/red]")
        
    os.remove(PID_FILE)

@cli.command()
def status():
    """Show current status of all monitored URLs (one-time check)."""
    targets = monitor.load_targets()
    console.print(f"Checking {len(targets)} targets...")
    
    table = Table()
    table.add_column("Target")
    table.add_column("URL")
    table.add_column("Status")
    table.add_column("Latency")
    
    for t in targets:
        res = monitor.check_url(t)
        color = "green" if res.is_up else "red"
        table.add_row(
            t["name"], 
            t["url"], 
            f"[{color}]{res.status_code}[/{color}]", 
            f"{res.latency_ms}ms"
        )
    console.print(table)

@cli.command()
def add_target():
    """Interactive prompt to add new URL to targets.json."""
    name = click.prompt("Name")
    url = click.prompt("URL")
    status = click.prompt("Expected Status", default=200, type=int)
    
    targets = monitor.load_targets()
    targets.append({"name": name, "url": url, "expected_status": status})
    
    with open(TARGETS_FILE, "w") as f:
        json.dump(targets, f, indent=2)
    console.print(f"[green]Added {name} ({url})[/green]")

@cli.command()
def remove_target():
    """Interactive prompt to remove URL from targets.json."""
    targets = monitor.load_targets()
    for i, t in enumerate(targets):
        console.print(f"{i+1}. {t['name']} ({t['url']})")
        
    idx = click.prompt("Enter number to remove", type=int)
    if 1 <= idx <= len(targets):
        removed = targets.pop(idx-1)
        with open(TARGETS_FILE, "w") as f:
            json.dump(targets, f, indent=2)
        console.print(f"[green]Removed {removed['name']}[/green]")
    else:
        console.print("[red]Invalid selection[/red]")

@cli.command()
def test_alert():
    """Send a test alert to verify email/telegram config."""
    mock_ticket = {
        "ticket_id": "OPS-TEST-000",
        "title": "P1: OpsBot Test Alert",
        "priority": "P1",
        "status": "OPEN",
        "url": "https://example.com",
        "reason": "Test alert triggered manually",
        "suggested_action": "Verify if you received this alert via Email & Telegram.",
        "created_at": "2024-01-01T00:00:00",
        "escalated": True
    }
    console.print("Sending test alerts (ignoring rate limits)...")
    
    alerter.send_email_alert(mock_ticket)
    alerter.send_telegram_alert(mock_ticket)
    console.print("[green]Test alerts dispatched![/green]")

@cli.group()
def tickets():
    """Manage incident tickets."""
    pass

@tickets.command()
@click.option('--all', 'show_all', is_flag=True, help='Show all tickets including resolved.')
def list(show_all):
    """List open tickets."""
    if show_all:
        t_list = ticketing.get_all_tickets()
        title = "All Tickets"
    else:
        t_list = ticketing.get_open_tickets()
        title = "Open Tickets"

    if not t_list:
        console.print(f"[green]No {title.lower()} found.[/green]")
        return

    table = Table(title=title)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Priority", style="bold")
    table.add_column("Status", style="bold")
    table.add_column("URL", style="blue")
    table.add_column("Occurrences", justify="right")

    for t in t_list:
        priority_color = "red" if t["priority"] == "P1" else "yellow" if t["priority"] == "P2" else "white"
        status_color = "green" if t["status"] == "RESOLVED" else "red"
        
        table.add_row(
            t["ticket_id"],
            f"[{priority_color}]{t['priority']}[/{priority_color}]",
            f"[{status_color}]{t['status']}[/{status_color}]",
            t["url"],
            str(t.get("occurrence_count", 1))
        )

    console.print(table)

@tickets.command()
@click.argument('ticket_id')
def show(ticket_id):
    """Show full details for a ticket."""
    t = ticketing.get_ticket(ticket_id)
    if not t:
        console.print(f"[red]Error: Ticket {ticket_id} not found.[/red]")
        return

    priority_color = "red" if t["priority"] == "P1" else "yellow" if t["priority"] == "P2" else "white"
    
    details = (
        f"[bold]Title:[/bold] {t['title']}\n"
        f"[bold]Status:[/bold] {t['status']}\n"
        f"[bold]Priority:[/bold] [{priority_color}]{t['priority']}[/{priority_color}]\n"
        f"[bold]URL:[/bold] {t['url']}\n"
        f"[bold]Reason:[/bold] {t['reason']}\n"
        f"[bold]Suggested Action:[/bold] {t['suggested_action']}\n"
        f"[bold]Occurrences:[/bold] {t.get('occurrence_count', 1)}\n"
        f"[bold]Created At:[/bold] {t['created_at']}\n"
        f"[bold]Last Seen:[/bold] {t.get('last_seen_at', t['created_at'])}\n"
    )

    if t.get("resolution_notes"):
        details += f"[bold]Resolved At:[/bold] {t['resolved_at']}\n"
        details += f"[bold]Resolution Notes:[/bold] {t['resolution_notes']}\n"

    console.print(Panel(details, title=f"Ticket {ticket_id} Details", expand=False))

@tickets.command()
@click.argument('ticket_id')
def resolve(ticket_id):
    """Mark a ticket as resolved."""
    t = ticketing.get_ticket(ticket_id)
    if not t:
        console.print(f"[red]Error: Ticket {ticket_id} not found.[/red]")
        return
        
    if t["status"] in ["RESOLVED", "CLOSED"]:
        console.print(f"[yellow]Ticket {ticket_id} is already {t['status']}.[/yellow]")
        return

    notes = click.prompt("Enter resolution notes", type=str)
    success, msg = ticketing.resolve_ticket(ticket_id, notes)
    
    if success:
        console.print(f"[green]{msg}[/green]")
    else:
        console.print(f"[red]{msg}[/red]")

@cli.command()
@click.option('--date', default=None, help='Generate report for a specific date (YYYY-MM-DD)')
@click.option('--show', is_flag=True, help='Print report to terminal')
def report(date, show):
    """Generate daily summary report."""
    rep, json_path, csv_path = reporter.generate_report(date)
    console.print(f"[green]Reports generated successfully:[/green]")
    console.print(f"- {json_path}")
    console.print(f"- {csv_path}")
    
    if show:
        table = Table(title=f"OpsBot Report ({rep['report_date']})")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")
        
        table.add_row("Total Checks (24h)", str(rep['total_checks_24h']))
        table.add_row("Incidents", str(sum(rep['incidents_by_priority'].values())))
        table.add_row("Tickets Created", str(rep['tickets']['created_24h']))
        table.add_row("Tickets Resolved", str(rep['tickets']['resolved_24h']))
        
        console.print(table)

@cli.command()
def dashboard():
    """Launch live terminal dashboard."""
    import dashboard as db
    db.run_dashboard()

if __name__ == '__main__':
    cli()
