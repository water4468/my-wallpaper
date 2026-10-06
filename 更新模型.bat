@echo off
cd /d "%~dp0"
echo ============================================
echo   Update local 3D model for index.html
echo ============================================
if not exist "assets\model\rounded-cube.glb" (
  echo [ERROR] Not found: assets\model\rounded-cube.glb
  echo Put your new .glb there with that exact name, then run again.
  pause
  exit /b 1
)
python --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python was not found. Ask Doubao to update the model instead.
  pause
  exit /b 1
)
python -c "import base64;f=open(r'assets/model/rounded-cube.glb','rb');b=base64.b64encode(f.read()).decode();f.close();g=open(r'assets/model/rounded-cube-data.js','w',encoding='utf-8');g.write('window.MODEL_GLB_B64 = \x22'+b+'\x22;\n');g.close();print('[OK] Model updated. Refresh the page with Ctrl+F5.')"
pause
