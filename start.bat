@echo off
REM SBC Tool startup
REM Uses venv python
SET ROOT=%~dp0
SET VENV=%ROOT%venv\Scripts\python.exe

IF EXIST "%VENV%" (
    "%VENV%" "%ROOT%run_app.py" --host 0.0.0.0 --port 8000
) ELSE (
    python "%ROOT%run_app.py" --host 0.0.0.0 --port 8000
)

pause