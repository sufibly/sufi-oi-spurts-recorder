"""
================================================================================
SUFI CLOUD 1-MINUTE CONTINUOUS NSE OI SPURTS RECORDER (GITHUB ACTIONS RUNNER)
================================================================================
100% Autonomous Cloud Engine: Runs in GitHub Actions cloud while your PC is OFF.
Schedule:
  - Starts automatically at 09:10 AM IST every Monday to Friday.
  - Automatically wipes yesterday's session at 09:13 AM IST.
  - Streams all 220 F&O stocks every 60 seconds from 09:15 AM to 03:30 PM IST.
  - Calculates real-time 1-minute momentum:
      * %CHNG IN OI (Day spurt from NSE)
      * 1-MIN %CHNG CHANGE (Delta vs last minute, e.g. 19.26 - 19.06 = +0.20%)
      * 1-MIN OI CHANGE (Contracts delta vs last minute)
  - Automatically terminates at 03:30 PM IST market close.
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

# Webhook URL for Google Sheet Version 5
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

def fetch_nse_live_spurts(session):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/oi-spurts"
    }
    url = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"
    
    try:
        r = session.get(url, headers=headers, timeout=12)
        if r.status_code == 200:
            return r.json().get("data", [])
        elif r.status_code in (401, 403):
            log_msg("Re-initializing session cookies with NSE...")
            session.get("https://www.nseindia.com", headers={"User-Agent": headers["User-Agent"]}, timeout=8)
            time.sleep(1)
            r = session.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                return r.json().get("data", [])
    except Exception as e:
        log_msg(f"NSE Fetch Warning: {e}")
        try:
            session.get("https://www.nseindia.com", headers={"User-Agent": headers["User-Agent"]}, timeout=8)
        except Exception:
            pass
    return []

def push_to_gsheet(payload: dict):
    try:
        r = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=25
        )
        if r.status_code == 200:
            return True, r.text
        return False, f"HTTP {r.status_code}: {r.text[:80]}"
    except Exception as e:
        return False, str(e)

def send_morning_reset():
    log_msg("🧹 Executing 09:13 AM Morning Reset on Google Sheet...")
    ok, resp = push_to_gsheet({"action": "wipe_morning_reset"})
    log_msg(f"Reset Response: {resp}")

def main():
    log_msg("🚀 Sufi Cloud 1-Minute NSE OI Spurts Recorder Initializing...")
    
    # Initialize session with Chrome 120 impersonation
    try:
        session = requests.Session(impersonate="chrome120")
    except Exception:
        session = requests.Session()
    
    # Handshake with NSE homepage to grab initial session cookies
    try:
        session.get("https://www.nseindia.com", headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }, timeout=10)
        log_msg("✅ NSE Session Handshake Complete.")
    except Exception as e:
        log_msg(f"Handshake warning: {e}")

    last_minute_recorded = ""
    last_reset_date = ""
    last_minute_symbol_data = {}  # symbol -> {"pct_chg_oi": float, "today_oi": float}

    log_msg("🟢 Running Market Loop (Will stream every 60 seconds until 03:30 PM IST)...")

    while True:
        now_ist = get_ist_now()
        curr_date = now_ist.strftime("%Y-%m-%d")
        curr_minute = now_ist.strftime("%Y-%m-%d %H:%M")
        hour = now_ist.hour
        minute = now_ist.minute

        # 1. Terminate when market closes (03:30 PM IST)
        if (hour > 15) or (hour == 15 and minute >= 31):
            log_msg(f"🏁 Market closed at {curr_minute} IST. Cloud recorder finished for the day.")
            break

        # 2. Automatic 09:13 AM Morning Reset
        if hour == 9 and minute == 13 and last_reset_date != curr_date:
            send_morning_reset()
            last_minute_symbol_data.clear()
            last_reset_date = curr_date
            time.sleep(30)
            continue

        # 3. Stream data if new minute
        if curr_minute != last_minute_recorded:
            t0 = time.time()
            items = fetch_nse_live_spurts(session)

            if items:
                # Sort by avgInOI (% Chg in OI) descending
                items.sort(key=lambda x: float(x.get("avgInOI") or 0), reverse=True)
                time_stamp_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")
                records = []

                for it in items:
                    sym = str(it.get("symbol", "")).strip()
                    raw_pct = float(it.get("avgInOI") or 0.0)      # e.g. 19.26
                    cur_oi = float(it.get("latestOI") or 0.0)      # Today's OI
                    prev_oi = float(it.get("prevOI") or 0.0)       # Yesterday's OI
                    chg_oi = float(it.get("changeInOI") or 0.0)    # Today Chg vs Yesterday
                    ltp = float(it.get("underlyingValue") or 0.0)
                    vol = float(it.get("volume") or 0.0)
                    fut_val = round(float(it.get("futValue") or 0.0), 2)

                    # Calculate 1-Minute Change in %CHNG IN OI (e.g. 19.26 - 19.06 = +0.20)
                    prev_data = last_minute_symbol_data.get(sym)
                    if prev_data is not None:
                        pct_1m_change = round(raw_pct - prev_data["pct_chg_oi"], 2)
                        oi_1m_change = round(cur_oi - prev_data["today_oi"], 0)
                    else:
                        pct_1m_change = 0.0
                        oi_1m_change = 0.0

                    last_minute_symbol_data[sym] = {
                        "pct_chg_oi": raw_pct,
                        "today_oi": cur_oi
                    }

                    records.append({
                        "symbol": sym,
                        "pct_chg_oi": raw_pct,
                        "pct_1m_change": pct_1m_change,
                        "oi_1m_change": oi_1m_change,
                        "chg_oi": chg_oi,
                        "today_oi": cur_oi,
                        "prev_oi": prev_oi,
                        "volume": vol,
                        "futures_val": fut_val,
                        "ltp": ltp,
                        "timestamp": time_stamp_str
                    })

                ok, resp_str = push_to_gsheet({
                    "action": "append_batch",
                    "records": records
                })

                elapsed = round(time.time() - t0, 1)
                top_sym = records[0]["symbol"] if records else "N/A"
                top_pct = records[0]["pct_chg_oi"] if records else 0
                top_1m = records[0]["pct_1m_change"] if records else 0
                sign_1m = f"+{top_1m}%" if top_1m >= 0 else f"{top_1m}%"

                if ok:
                    log_msg(f"✅ [{curr_minute} IST] Streamed {len(records)} stocks in {elapsed}s | Top: {top_sym} (Day: +{top_pct}%, 1-Min Chg: {sign_1m})")
                    last_minute_recorded = curr_minute
                else:
                    log_msg(f"⚠️ [{curr_minute} IST] Push failed: {resp_str}")
            else:
                log_msg(f"⚠️ [{curr_minute} IST] NSE returned 0 records. Retrying...")

        sec_to_next_min = 60 - get_ist_now().second
        time.sleep(max(min(sec_to_next_min, 10), 1))

if __name__ == "__main__":
    main()
