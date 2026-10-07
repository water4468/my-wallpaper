@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   正在发布网站更新到 GitHub ...
echo ============================================
echo.
git add -A
git commit -m "更新网站内容"
echo.
echo 正在推送到 GitHub ...
git push origin main
echo.
echo ============================================
echo   完成！约 1~2 分钟后线上网站自动生效。
echo ============================================
pause
