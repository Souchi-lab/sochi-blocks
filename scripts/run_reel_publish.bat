@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo  SoChi BLOCKS — Instagram Reel Publish (Scheduled)
echo  ※ run_daily_publish.bat の約20分後に実行してください
echo ============================================================
echo.

REM ── Docker DB 起動 ──
echo Docker DB を起動中...
docker compose -f infra/docker/docker-compose.yml up db -d
echo DB起動待機中...
timeout /t 5 > nul
echo.

REM ── tmp/reel_queue.txt を読んで Reel を投稿 ──────────────────────
echo [1/1] Instagram Reel 投稿中...
poetry run python scripts/post_reel_from_queue.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Reel 投稿に失敗しました。ログを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完了！
echo ============================================================
pause
