@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo  SoChi BLOCKS — Daily Instagram Publish
echo ============================================================
echo.

REM ── Docker DB 起動 ──
echo Docker DB を起動中...
docker compose -f infra/docker/docker-compose.yml up db -d
echo DB起動待機中...
timeout /t 5 > nul
echo.

REM ── パズル生成 → カルーセル投稿（Reel は run_reel_publish.bat で別途実行） ──
echo [1/1] Instagram カルーセル投稿中...
poetry run python scripts/auto_publish.py --all --instagram --twitter --tiktok --tiktok-auto
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 投稿に失敗したパズルがあります。ログを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完了！（Reel は約20分後に run_reel_publish.bat を実行してください）
echo ============================================================
pause
