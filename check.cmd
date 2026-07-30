@echo off
REM seo-forge — CI local del motor (R10): el auditor se audita a sí mismo.
REM Corre lint (ruff) + tests (pytest). Úsalo antes de commitear cambios al motor.
cd /d "%~dp0"
set PYTHONUTF8=1
echo === ruff (lint) ===
".venv\Scripts\python.exe" -m ruff check execution tests || goto :fail
echo === pytest (tests) ===
".venv\Scripts\python.exe" -m pytest || goto :fail
echo.
echo OK: lint limpio + tests verdes.
exit /b 0
:fail
echo.
echo FALLO: revisa el output de arriba.
exit /b 1
