"""
================================================================================
SUFI CLOUD 1-MINUTE CONTINUOUS NSE OI SPURTS RECORDER (GITHUB ACTIONS RUNNER)  v3
================================================================================
Runs in GitHub Actions while the PC is OFF.
  - GitHub starts scheduled jobs late (often by hours), so the workflow fires every 15 minutes all day.
    A run that starts between 05:00 and 15:30 IST on a weekday stays: it waits for 09:15 and then records.
    Any other run exits in seconds.
  - GitHub stops a job after 6 hours: after 5h50m a run asks GitHub to start its own successor (the
    workflow's "Hand over" step) and stops; the successor carries on to 15:30. Only one run works at a time.
  - The Google Sheet script wipes yesterday's data once a day and keeps exactly one record set per minute.
  - RUN_MODE=test : one NSE fetch, result shown on the run page, nothing written to the sheet.
================================================================================
"""

import sys
import time
import json
import os
from datetime import datetime
import pytz

try:
    from curl_cffi import requests
except ImportError:
    import requests

# Webhook URL for Google Sheet
WEBHOOK_URL = os.environ.get(
    "GSHEET_WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbxgojskx6zSHeSPHnhqPwxVNpcbE2HfDDCon41vGRJXTLMlk8BK3h95ganuUqOCGYtz/exec"
)

IST = pytz.timezone("Asia/Kolkata")

def get_ist_now():
    return datetime.now(IST)

def log_msg(msg: str):
    timestamp = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp} IST] {msg}", flush=True)

def create_nse_session():
    """Initializes a new session with Chrome 120 browser impersonation and fresh cookies."""
    try:
        session = requests.Session(impersonate="chrome120")
    except Exception:
        session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    try:
        session.get("https://www.nseindia.com", headers=headers, timeout=12)
        log_msg("✅ NSE Session Handshake Complete with fresh cookies.")
    except Exception as e:
        log_msg(f"NSE Handshake warning: {e}")
    return session

def fetch_nse_live_spurts(session):
    """Fetches official NSE Change in Open Interest with automatic retry."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/oi-spurts"
    }
    url = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"
    
    for attempt in range(3):
        try:
            r = session.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return data
            elif r.status_code in (401, 403):
                log_msg(f"NSE 403/401 on attempt {attempt+1}. Re-handshaking...")
                try:
                    session.get("https://www.nseindia.com", headers={"User-Agent": headers["User-Agent"]}, timeout=10)
                except Exception:
                    pass
                time.sleep(2)
        except Exception as e:
            log_msg(f"NSE fetch attempt {attempt+1} warning: {e}")
            time.sleep(2)
    return []

def push_to_gsheet(payload: dict):
    try:
        r = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=45
        )
        if r.status_code == 200:
            return True, r.text
        return False, f"HTTP {r.status_code}: {r.text[:80]}"
    except Exception as e:
        return False, str(e)

def send_morning_reset():
    """Asks the sheet to wipe yesterday's data. The sheet does it once per day only, so this is always safe."""
    ok, resp = push_to_gsheet({"action": "wipe_morning_reset"})
    log_msg(f"Daily reset request -> {resp[:120] if isinstance(resp, str) else resp}")


def summary(text: str):
    """Shown on the run page (readable without opening the logs)."""
    print(f"::notice title=OI Spurts Recorder::{text}", flush=True)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text + "\n\n")
        except Exception:
            pass


def to_records(items, time_stamp_str):
    records = []
    for it in items:
        sym = str(it.get("symbol", "")).strip()
        if not sym:
            continue
        records.append({
            "symbol": sym,
            "pct_chg_oi": float(it.get("avgInOI") or 0.0),
            "pct_1m_change": 0.0,          # the sheet works out the 1-minute changes
            "oi_1m_change": 0.0,
            "chg_oi": float(it.get("changeInOI") or 0.0),
            "today_oi": float(it.get("latestOI") or 0.0),
            "prev_oi": float(it.get("prevOI") or 0.0),
            "volume": float(it.get("volume") or 0.0),
            "futures_val": round(float(it.get("futValue") or 0.0), 2),
            "ltp": float(it.get("underlyingValue") or 0.0),
            "timestamp": time_stamp_str,
        })
    records.sort(key=lambda r: r["pct_chg_oi"], reverse=True)
    return records


def run_test():
    t0 = time.time()
    session = create_nse_session()
    items = fetch_nse_live_spurts(session)
    secs = round(time.time() - t0, 1)
    now = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    if len(items) >= 100:
        top = max(items, key=lambda x: float(x.get("avgInOI") or 0))
        summary(f"TEST OK at {now} IST: NSE answered this GitHub server with {len(items)} stocks in {secs}s "
                f"(top {top.get('symbol')} {top.get('avgInOI')}%).")
        return 0
    summary(f"TEST FAILED at {now} IST: NSE gave {len(items)} stocks to this GitHub server after {secs}s.")
    return 1


def main():
    mode = (os.environ.get("RUN_MODE") or "normal").strip().lower()
    if mode == "test":
        sys.exit(run_test())
    if mode == "handover_test":                    # proves that a run can start its own successor
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write("handover=true\n")
        summary("HANDOVER TEST: asking GitHub to start the next run now.")
        return

    started = time.time()
    max_run_seconds = int(float(os.environ.get("MAX_RUN_MINUTES", "350")) * 60)
    now_ist = get_ist_now()
    tm = now_ist.hour * 60 + now_ist.minute
    if now_ist.weekday() >= 5:
        summary(f"{now_ist:%Y-%m-%d %H:%M} IST is a weekend - nothing to record.")
        return
    if tm < 5 * 60 or tm > 15 * 60 + 30:
        summary(f"Started {now_ist:%Y-%m-%d %H:%M} IST, outside 05:00-15:30 - exiting (a later run records).")
        return

    log_msg("Recorder on duty (waits for 09:15 if early).")
    handover = False
    session = create_nse_session()
    last_minute_recorded = ""
    reset_sent = False
    empty = 0
    saved = 0
    failed = 0

    while True:
        try:
            now_ist = get_ist_now()
            curr_minute = now_ist.strftime("%Y-%m-%d %H:%M")
            tm = now_ist.hour * 60 + now_ist.minute
            if tm > 15 * 60 + 30:
                break
            if time.time() - started > max_run_seconds:
                log_msg("Handing over to a fresh run (GitHub's 6-hour job limit).")
                handover = True
                break
            if tm < 9 * 60 + 13:
                time.sleep(20)
                continue
            if not reset_sent:
                send_morning_reset()
                reset_sent = True
            if tm < 9 * 60 + 15:
                time.sleep(10)
                continue

            if curr_minute != last_minute_recorded:
                t0 = time.time()
                items = fetch_nse_live_spurts(session)
                if items:
                    empty = 0
                    records = to_records(items, now_ist.strftime("%Y-%m-%d %H:%M:%S"))
                    ok, resp_str = push_to_gsheet({"action": "append_batch", "records": records})
                    if not ok:                                   # one retry; the sheet ignores a minute it already has
                        time.sleep(3)
                        ok, resp_str = push_to_gsheet({"action": "append_batch", "records": records})
                    if ok:
                        saved += 1
                        last_minute_recorded = curr_minute
                        log_msg(f"OK [{curr_minute}] {len(records)} stocks in {round(time.time() - t0, 1)}s -> {str(resp_str)[:100]}")
                    else:
                        failed += 1
                        log_msg(f"PUSH FAILED [{curr_minute}]: {resp_str}")
                else:
                    empty += 1
                    failed += 1
                    log_msg(f"NSE returned nothing [{curr_minute}] (in a row: {empty})")
                    if empty >= 2:
                        session = create_nse_session()
                        empty = 0

            time.sleep(max(min(60 - get_ist_now().second, 10), 1))
        except Exception as e:
            log_msg(f"Loop exception (recovering): {e}")
            time.sleep(5)

    if handover:
        out = os.environ.get("GITHUB_OUTPUT")
        if out:
            with open(out, "a", encoding="utf-8") as f:
                f.write("handover=true\n")
    summary(f"Recorded {saved} minutes ({failed} failed attempts) between {datetime.fromtimestamp(started, IST):%H:%M} "
            f"and {get_ist_now():%H:%M} IST." + (" Handed over to the next run." if handover else ""))


if __name__ == "__main__":
    main()
