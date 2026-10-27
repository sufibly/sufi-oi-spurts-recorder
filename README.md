# 🚀 Sufi 1-Minute Live NSE OI Spurts Cloud Recorder

100% Free, Autonomous Cloud Runner powered by GitHub Actions.
Streams all 220 F&O stocks every 60 seconds directly into your Google Sheet while your computer is completely turned off.

---

### Features
1. **Runs While Your PC is OFF**: Executes on GitHub's cloud servers.
2. **Every 60 Seconds**: Streams live NSE OI Spurts with `%CHNG IN OI`, `1-MIN %CHNG CHANGE`, `1-MIN OI CHANGE`.
3. **09:13 AM IST Auto-Reset**: Wipes yesterday's data automatically and starts fresh for the day.
4. **Market Hours Only**: Starts at 09:10 AM IST and automatically terminates at 03:30 PM IST.
5. **100% Free Forever**: Public GitHub repositories have unlimited free GitHub Actions minutes.

---

### Setup (Takes 2 Minutes)

1. Go to [github.com/new](https://github.com/new) and create a new repository:
   - Name: `sufi-oi-spurts-recorder`
   - Set to: **Public** (Public repositories get **unlimited free** GitHub Actions minutes!)
2. Upload the files from this folder (`recorder.py`, `requirements.txt`, `.github/workflows/oi_spurts_recorder.yml`).
3. Done!
   - To test it immediately: Go to the **Actions** tab in your GitHub repository, click **1-Minute Live NSE OI Spurts Cloud Recorder**, and click **Run workflow**.
   - Otherwise, it will trigger automatically at **09:10 AM IST** every weekday morning!
