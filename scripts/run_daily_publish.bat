@echo off
cd /d "%~dp0.."
echo Initializing environment (Docker, etc.)...
REM Start database if not running
docker-compose up -d

echo Running daily puzzle publish...
poetry run python scripts/auto_publish.py --all --instagram
echo Done.
pause
