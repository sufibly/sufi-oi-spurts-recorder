@echo off
setlocal
title Push Sufi Cloud Recorder to GitHub
color 0A
cd /d "%~dp0"

echo ==============================================================================
echo  SUFI 1-MINUTE LIVE NSE OI SPURTS CLOUD RECORDER (GITHUB ACTIONS)
echo ==============================================================================
echo.
echo  This tool links your repository to your GitHub account so GitHub Actions
echo  can stream the data into Google Sheets 100% online while your PC is OFF.
echo.
echo  Step 1: Go to https://github.com/new
echo  Step 2: Repository name: sufi-oi-spurts-recorder (Select Public)
echo  Step 3: Copy the repository URL and paste it below:
echo.
set /p REPO_URL="Enter GitHub Repo URL: "

if "%REPO_URL%"=="" (
    echo [ERROR] No URL entered.
    pause
    exit /b
)

git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
git push -u origin main

echo.
echo ==============================================================================
echo  SUCCESS! YOUR CLOUD RECORDER IS DEPLOYED TO GITHUB ACTIONS!
echo ==============================================================================
echo  - Starts automatically at 09:10 AM IST every Monday to Friday.
echo  - Wipes yesterday's data at 09:13 AM IST.
echo  - Streams all 220 stocks every 60 seconds into your Google Sheet.
echo  - Stops automatically at 03:30 PM IST.
echo  - Your computer can remain completely powered off!
echo ==============================================================================
echo.
pause
