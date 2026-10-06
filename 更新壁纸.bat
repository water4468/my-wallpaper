@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在扫描 images 文件夹并更新壁纸清单...
echo.
set "PY=C:\Users\liuwenhao\AppData\Local\Doubao\User Data\sandbox_runtime\bases\c98c5042338ed152c6f10ecd8591889f\python\python.exe"
if exist "%PY%" (
  "%PY%" generate_wallpapers.py
) else (
  python generate_wallpapers.py
)
echo.
echo 完成！刷新浏览器即可看到新壁纸。
pause