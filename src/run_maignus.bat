@echo off
:: Change to the script's directory
cd /d %~dp0

:: Create a log directory if it doesn't exist
if not exist logs mkdir logs

:: Set timestamp for log filename
set timestamp=%date:~-4,4%%date:~-7,2%%date:~-10,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =0%

:: Log file path
set logfile=logs\maignus_run_%timestamp%.log

:: Check for --force parameter
set FORCE_PARAM=
if "%1"=="--force" set FORCE_PARAM=--force

:: Log start time and parameters
echo ===== MAIgnus_CAIrlsen Started at %date% %time% with parameters: [%FORCE_PARAM%] ===== > "%logfile%"

:: Path to Python - using your specific Python path
python "%~dp0\maignus_bot.py" %FORCE_PARAM% >> "%logfile%" 2>&1

:: Run the script and log output
echo Running MAIgnus_CAIrlsen chess analysis bot... >> "%logfile%"
python maignus_bot.py %FORCE_PARAM% >> "%logfile%" 2>&1

:: Log completion
echo ===== MAIgnus_CAIrlsen Completed at %date% %time% ===== >> "%logfile%"

:: Return exit code
exit /b %errorlevel%