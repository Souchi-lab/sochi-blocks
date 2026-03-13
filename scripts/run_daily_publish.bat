@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo  SoChi BLOCKS — Daily Instagram Publish
echo ============================================================
echo.

REM ── パズル生成 → カルーセル + Reels を全件投稿 ─────────────────
echo [1/1] Instagram 投稿中...
poetry run python scripts/auto_publish.py --all --instagram --also-reel
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 投稿に失敗したパズルがあります。ログを確認してください。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  完了！
echo ============================================================
pause
