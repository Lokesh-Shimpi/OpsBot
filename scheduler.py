import time
import schedule
from monitor import run_monitor
from reporter import generate_report

def monitor_job():
    try:
        run_monitor()
    except Exception as e:
        print(f"Error in monitor_job: {e}")

def report_job():
    try:
        generate_report()
        print("Daily report generated.")
    except Exception as e:
        print(f"Error in report_job: {e}")

if __name__ == "__main__":
    print("OpsBot Scheduler started.")
    # Run immediately once
    monitor_job()
    
    # Schedule monitor every 60 seconds
    schedule.every(60).seconds.do(monitor_job)
    
    # Schedule report at 08:00 daily
    schedule.every().day.at("08:00").do(report_job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
