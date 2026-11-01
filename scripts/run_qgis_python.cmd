@echo off
setlocal
if not defined MUSA_QGIS_ROOT (
  echo Set MUSA_QGIS_ROOT to the existing QGIS installation on the development PC.
  exit /b 2
)
if not exist "%MUSA_QGIS_ROOT%\bin\python-qgis-ltr.bat" (
  echo QGIS Python launcher was not found under MUSA_QGIS_ROOT.
  exit /b 2
)
call "%MUSA_QGIS_ROOT%\bin\python-qgis-ltr.bat" %*
exit /b %errorlevel%
