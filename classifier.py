from dataclasses import dataclass
from monitor import MonitorResult

@dataclass
class Classification:
    priority: str
    reason: str
    suggested_action: str
    escalate: bool

def classify_incident(result: MonitorResult, expected_status: int = 200) -> Classification | None:
    """
    Takes a MonitorResult and returns a Classification based on ITIL-logic.
    Returns None if there is no incident.
    """
    
    # ---------------------------------------------------------
    # P1 — CRITICAL (immediate action required)
    # ---------------------------------------------------------
    if str(result.status_code) in ["DOWN", "TIMEOUT", "SSL_FAILURE", "ERROR"] or not result.dns_ok:
        reason = "Site completely DOWN or DNS resolution failure"
        if str(result.status_code) == "TIMEOUT": reason = "Connection TIMEOUT"
        elif not result.dns_ok: reason = "DNS resolution failure"
        
        return Classification(
            priority="P1",
            reason=reason,
            suggested_action="Immediately check server status, verify DNS, escalate to L2 if not resolved in 5 mins",
            escalate=True
        )
        
    if isinstance(result.status_code, int) and result.status_code in [500, 502, 503, 504]:
        return Classification(
            priority="P1",
            reason=f"HTTP {result.status_code} Internal Server Error",
            suggested_action="Immediately check server status, escalate to L2 if not resolved in 5 mins",
            escalate=True
        )
        
    if result.ssl_days_left is not None and result.ssl_days_left <= 0:
        return Classification(
            priority="P1",
            reason="SSL certificate expired",
            suggested_action="SSL certificate expired. Contact DevOps team immediately to renew certificate.",
            escalate=True
        )

    # ---------------------------------------------------------
    # P2 — HIGH (action required within 1 hour)
    # ---------------------------------------------------------
    if isinstance(result.status_code, int) and result.status_code in [400, 401, 403, 404]:
        return Classification(
            priority="P2",
            reason=f"HTTP {result.status_code} Client Error",
            suggested_action="Verify client request and endpoint availability. Investigate access logs.",
            escalate=True
        )
        
    if result.ssl_days_left is not None and result.ssl_days_left <= 7:
        return Classification(
            priority="P2",
            reason=f"SSL certificate expiring very soon ({result.ssl_days_left} days left)",
            suggested_action="SSL certificate expiring within 7 days. Schedule urgent renewal.",
            escalate=True
        )
        
    if result.latency_ms > 3000:
        return Classification(
            priority="P2",
            reason=f"Very high response latency: {result.latency_ms}ms",
            suggested_action="High latency detected. Check server CPU/memory, verify no active deployments.",
            escalate=True
        )

    # ---------------------------------------------------------
    # P3 — MEDIUM (action required within 4 hours)
    # ---------------------------------------------------------
    if result.ssl_days_left is not None and result.ssl_days_left <= 30:
        return Classification(
            priority="P3",
            reason=f"SSL certificate expiring soon ({result.ssl_days_left} days left)",
            suggested_action="SSL certificate expiring soon. Schedule renewal within this week.",
            escalate=False
        )
        
    if 1000 < result.latency_ms <= 3000:
        return Classification(
            priority="P3",
            reason=f"Elevated response latency: {result.latency_ms}ms",
            suggested_action="Monitor performance trends. Consider scaling resources if sustained.",
            escalate=False
        )
        
    if isinstance(result.status_code, int) and result.status_code != expected_status:
        return Classification(
            priority="P3",
            reason=f"Unexpected HTTP status code: {result.status_code} (expected {expected_status})",
            suggested_action="Investigate endpoint behavior. Check application logs.",
            escalate=False
        )

    # ---------------------------------------------------------
    # P4 — LOW (informational)
    # ---------------------------------------------------------
    if 500 <= result.latency_ms <= 1000:
        return Classification(
            priority="P4",
            reason=f"Slightly elevated latency: {result.latency_ms}ms",
            suggested_action="Informational: Latency is slightly above optimal levels.",
            escalate=False
        )
        
    if not result.is_up:
        return Classification(
            priority="P4",
            reason=f"Anomaly detected: Status {result.status_code}",
            suggested_action="Investigate anomaly.",
            escalate=False
        )

    return None

if __name__ == "__main__":
    from datetime import datetime, timezone
    
    # Test cases
    test_results = [
        MonitorResult("http://test.com", "Test1", "TIMEOUT", 0, False, None, True, datetime.now(timezone.utc).isoformat(), False),
        MonitorResult("http://test.com", "Test2", 503, 1200, True, 40, True, datetime.now(timezone.utc).isoformat(), False),
        MonitorResult("http://test.com", "Test3", 200, 3500, True, 40, True, datetime.now(timezone.utc).isoformat(), True),
        MonitorResult("http://test.com", "Test4", 200, 200, True, 5, True, datetime.now(timezone.utc).isoformat(), True),
        MonitorResult("http://test.com", "Test5", 200, 200, True, 15, True, datetime.now(timezone.utc).isoformat(), True),
        MonitorResult("http://test.com", "Test6", 200, 600, True, 100, True, datetime.now(timezone.utc).isoformat(), True),
        MonitorResult("http://test.com", "Test7", 200, 100, True, 100, True, datetime.now(timezone.utc).isoformat(), True),
    ]
    
    for r in test_results:
        classification = classify_incident(r)
        if classification:
            print(f"{r.name}: {classification.priority} - {classification.reason} (Escalate: {classification.escalate})")
        else:
            print(f"{r.name}: OK")
