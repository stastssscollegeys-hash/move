@echo off
rem start_raceday.bat - run raceday_auto.py for today (Sat/Sun/holiday morning, once). Log: daily_pdca\db\raceday_logs\YYYYMMDD.log
rem usage: start_raceday.bat [YYYYMMDD]   (no argument = today)
cd /d "%~dp0"
set D=%1
if "%D%"=="" for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set D=%%d
rem skip if already running for this date (log updated within 10 minutes)
powershell -NoProfile -Command "$f=Join-Path $env:USERPROFILE 'Desktop\競馬予想レポート\daily_pdca\db\raceday_logs\%D%.log'; if((Test-Path $f) -and ((Get-Date)-(Get-Item $f).LastWriteTime).TotalMinutes -lt 10){exit 3}"
if %ERRORLEVEL%==3 (echo already running for %D% & exit /b 0)
python raceday_auto.py --date %D%
