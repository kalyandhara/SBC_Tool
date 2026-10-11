@echo off
REM B-57 / B-59: download Dukascopy hourly gold and silver, and refresh the US release calendar.
REM Output goes to data\intraday\fetch.log so the run can be checked afterwards.
SET ROOT=%~dp0
SET PY=%ROOT%venv\Scripts\python.exe
IF NOT EXIST "%PY%" SET PY=python
cd /d "%ROOT%"
IF NOT EXIST data\intraday mkdir data\intraday
echo === start %DATE% %TIME% === > data\intraday\fetch.log
"%PY%" scripts\refresh_econ_calendar.py >> data\intraday\fetch.log 2>&1
"%PY%" scripts\fetch_dukascopy.py --symbols XAUUSD --start 2024-01 --end 2024-01 >> data\intraday\fetch.log 2>&1
IF ERRORLEVEL 1 GOTO failed
"%PY%" scripts\fetch_dukascopy.py >> data\intraday\fetch.log 2>&1
IF ERRORLEVEL 1 GOTO failed
echo === done %DATE% %TIME% === >> data\intraday\fetch.log
echo Finished. Details in data\intraday\fetch.log
pause
exit /b 0
:failed
echo === FAILED %DATE% %TIME% === >> data\intraday\fetch.log
echo Download failed. See data\intraday\fetch.log
pause
exit /b 1
