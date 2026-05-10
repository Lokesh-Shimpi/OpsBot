import time
import os
import sys
from datetime import datetime
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.console import Console
from rich import box

from monitor import load_targets
from reporter import load_incidents, generate_report
from ticketing import get_open_tickets

def generate_dashboard():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=2)
    )
    layout["right"].split_column(
        Layout(name="tickets", ratio=2),
        Layout(name="stats", ratio=1)
    )

    # Header
    header_text = Table.grid(expand=True)
    header_text.add_column(justify="left")
    header_text.add_column(justify="right")
    header_text.add_row(
        "[bold cyan]OpsBot Dashboard[/bold cyan]", 
        f"Last: {datetime.now().strftime('%H:%M:%S')}"
    )
    layout["header"].update(Panel(header_text, style="white on blue"))

    # Left: LIVE STATUS
    targets = load_targets()
    incidents = load_incidents()
    
    # Get latest incident for each url
    latest_status = {}
    for inc in incidents:
        latest_status[inc["url"]] = inc
        
    status_table = Table(box=None, expand=True, show_header=False)
    status_table.add_column("Status")
    
    for t in targets:
        url = t["url"]
        name = t["name"]
        if url in latest_status:
            inc = latest_status[url]
            is_up = inc["is_up"]
            status_code = inc["status_code"]
            lat = inc["latency_ms"]
            
            if is_up:
                icon = "✅"
                color = "green"
            else:
                if str(status_code) in ["DOWN", "TIMEOUT"] or isinstance(status_code, int) and status_code >= 500:
                    icon = "🔴"
                    color = "red"
                else:
                    icon = "⚠️"
                    color = "yellow"
                    
            status_table.add_row(f"[{color}]{icon} {name}[/{color}]")
            status_table.add_row(f"   [dim]{status_code} | {lat}ms[/dim]")
            status_table.add_row("")
        else:
            status_table.add_row(f"[gray]⚪ {name}[/gray]")
            status_table.add_row("   [dim]No data yet[/dim]")
            status_table.add_row("")

    layout["left"].update(Panel(status_table, title="LIVE STATUS", border_style="cyan"))

    # Right Top: OPEN TICKETS
    tickets = get_open_tickets()
    ticket_table = Table(box=None, expand=True, show_header=False)
    ticket_table.add_column("Ticket")
    
    if not tickets:
        ticket_table.add_row("[dim]No open tickets.[/dim]")
    else:
        for t in tickets[:5]: # show top 5
            color = "red" if t["priority"] == "P1" else "yellow"
            ticket_table.add_row(f"[{color}]{t['ticket_id']} {t['priority']} {t['title']}[/{color}]")

    layout["tickets"].update(Panel(ticket_table, title="OPEN TICKETS", border_style="cyan"))

    # Right Bottom: STATS (24h)
    try:
        report, _, _ = generate_report()
        stats_table = Table(box=None, expand=True, show_header=False)
        stats_table.add_column("Stat")
        
        total_checks = report["total_checks_24h"]
        total_incidents = sum(report["incidents_by_priority"].values())
        
        # Calculate overall uptime
        if total_checks > 0:
            up_checks = sum(1 for inc in load_incidents() if inc["is_up"] and (datetime.now(timezone.utc) - datetime.fromisoformat(inc["timestamp"])).days < 1)
            uptime_pct = round((up_checks / total_checks) * 100, 1)
        else:
            uptime_pct = 0.0
            
        stats_table.add_row(f"Checks: {total_checks}")
        stats_table.add_row(f"Incidents: {total_incidents}")
        stats_table.add_row(f"Uptime: {uptime_pct}%")
        
    except Exception as e:
        stats_table = Text(f"Error loading stats: {e}")

    layout["stats"].update(Panel(stats_table, title="STATS (24h)", border_style="cyan"))

    return layout

def run_dashboard():
    console = Console()
    try:
        with Live(generate_dashboard(), refresh_per_second=1, screen=True) as live:
            while True:
                time.sleep(30)
                live.update(generate_dashboard())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run_dashboard()
