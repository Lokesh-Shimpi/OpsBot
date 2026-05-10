import json
import csv
import os
from datetime import datetime, timezone, timedelta
from monitor import load_targets
from ticketing import load_tickets

INCIDENTS_FILE = "data/incidents.json"
REPORTS_DIR = "data/reports"

def load_incidents():
    if not os.path.exists(INCIDENTS_FILE):
        return []
    try:
        with open(INCIDENTS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def generate_report(target_date_str=None):
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        
    if target_date_str:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        target_date = datetime.now(timezone.utc)
        
    start_time = target_date - timedelta(days=1)
    
    incidents = load_incidents()
    tickets = load_tickets()
    targets = load_targets()
    
    # Filter incidents to last 24h of target date
    recent_incidents = []
    for inc in incidents:
        inc_time = datetime.fromisoformat(inc["timestamp"])
        if start_time <= inc_time <= target_date:
            recent_incidents.append(inc)
            
    total_checks = len(recent_incidents)
    
    url_stats = {}
    for t in targets:
        url_stats[t["url"]] = {
            "url": t["url"],
            "total_checks": 0,
            "up_checks": 0,
            "total_latency": 0.0,
            "incidents": []
        }
        
    for inc in recent_incidents:
        url = inc["url"]
        if url not in url_stats:
            continue
        url_stats[url]["total_checks"] += 1
        if inc["is_up"]:
            url_stats[url]["up_checks"] += 1
        url_stats[url]["total_latency"] += inc["latency_ms"]
        
        # Determine incident level
        if not inc["is_up"]:
            url_stats[url]["incidents"].append(inc)

    # Filter tickets
    recent_tickets = [t for t in tickets if datetime.fromisoformat(t["created_at"]) >= start_time]
    open_tickets = [t for t in tickets if t["status"] in ["OPEN", "IN_PROGRESS"]]
    resolved_tickets = [t for t in recent_tickets if t["status"] == "RESOLVED"]
    
    p_counts = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    url_incident_counts = {}
    
    for t in recent_tickets:
        p = t["priority"]
        if p in p_counts:
            p_counts[p] += t.get("occurrence_count", 1)
        
        url = t["url"]
        url_incident_counts[url] = url_incident_counts.get(url, 0) + t.get("occurrence_count", 1)
        
    # Top 3 problematic
    top_problematic = sorted(url_incident_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # SSL certs
    expiring_ssl = []
    for inc in reversed(incidents): # get latest
        url = inc["url"]
        if not any(e["url"] == url for e in expiring_ssl):
            if inc["ssl_days_left"] is not None and inc["ssl_days_left"] <= 30:
                expiring_ssl.append({"url": url, "days_left": inc["ssl_days_left"]})
                
    # Prepare CSV data
    csv_data = []
    for url, stats in url_stats.items():
        tc = stats["total_checks"]
        uptime = round((stats["up_checks"] / tc * 100) if tc > 0 else 0, 2)
        avg_lat = round((stats["total_latency"] / tc) if tc > 0 else 0, 2)
        
        url_tix = [t for t in recent_tickets if t["url"] == url]
        p1 = sum(t.get("occurrence_count", 1) for t in url_tix if t["priority"] == "P1")
        p2 = sum(t.get("occurrence_count", 1) for t in url_tix if t["priority"] == "P2")
        p3 = sum(t.get("occurrence_count", 1) for t in url_tix if t["priority"] == "P3")
        tot = p1 + p2 + p3
        
        csv_data.append({
            "URL": url,
            "Uptime%": uptime,
            "Avg_Latency_ms": avg_lat,
            "P1_Count": p1,
            "P2_Count": p2,
            "P3_Count": p3,
            "Total_Incidents": tot
        })
        
    report = {
        "report_date": target_date.strftime("%Y-%m-%d"),
        "total_checks_24h": total_checks,
        "incidents_by_priority": p_counts,
        "tickets": {
            "created_24h": len(recent_tickets),
            "resolved_24h": len(resolved_tickets),
            "currently_open": len(open_tickets)
        },
        "top_problematic_urls": [{"url": u, "count": c} for u, c in top_problematic],
        "expiring_ssl": expiring_ssl,
        "url_stats": csv_data
    }
    
    date_str = target_date.strftime("%Y-%m-%d")
    json_path = os.path.join(REPORTS_DIR, f"report_{date_str}.json")
    csv_path = os.path.join(REPORTS_DIR, f"report_{date_str}.csv")
    
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
        
    with open(csv_path, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["URL", "Uptime%", "Avg_Latency_ms", "P1_Count", "P2_Count", "P3_Count", "Total_Incidents"])
        writer.writeheader()
        writer.writerows(csv_data)
        
    return report, json_path, csv_path

if __name__ == "__main__":
    rep, j, c = generate_report()
    print(f"Generated {j} and {c}")
