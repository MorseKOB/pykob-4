@echo off

rem MIT License
rem 
rem Copyright (c) 2020 PyKOB - MorseKOB in Python
rem 
rem Permission is hereby granted, free of charge, to any person obtaining a copy
rem of this software and associated documentation files (the "Software"), to deal
rem in the Software without restriction, including without limitation the rights
rem to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
rem copies of the Software, and to permit persons to whom the Software is
rem furnished to do so, subject to the following conditions:
rem
rem The above copyright notice and this permission notice shall be included in all
rem copies or substantial portions of the Software.
rem 
rem THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
rem IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
rem FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
rem AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
rem LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
rem OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
rem SOFTWARE.

rem called from `make64` or `make32`

echo Make the Windows bundle

echo Python: %_PYTHON_EXE_%
echo Build Folder: %_BUILD_DIR_%
echo Dist Folder: %_DIST_DIR_%

if exist %_BUILD_DIR_% rmdir /S /Q %_BUILD_DIR_%
if exist %_DIST_DIR_% rmdir /S /Q %_DIST_DIR_%

rem Run PyInstaller with a specific Python install to generate 
rem the appropriate bundle in the configured 'dist*' folder
echo Building Configure...
%_PYTHON_EXE_% -m PyInstaller --clean --log-level INFO --workpath=%_BUILD_DIR_% --distpath=%_DIST_DIR_% Configure.spec
if errorlevel 1 (
    echo PyInstaller Failure on Configure: %errorlevel%
    GOTO ERROR_EXIT
)

rem %_PYTHON_EXE_% -m PyInstaller --distpath=%_DIST_DIR_% Sample.py
rem %_PYTHON_EXE_% -m PyInstaller --distpath=%_DIST_DIR_% Clock.py
echo Building MKOB...
%_PYTHON_EXE_% -m PyInstaller --clean --log-level INFO --workpath=%_BUILD_DIR_% --distpath=%_DIST_DIR_% MKOB.spec
if errorlevel 1 (
    echo PyInstaller Failure: %errorlevel%
    GOTO ERROR_EXIT
)

echo Copy Configure.exe into the MKOB folder
copy %_DIST_DIR_%\Configure\Configure.exe %_DIST_DIR_%\MKOB4

echo Create ZIP for %_PKG_NAME_%
echo  to %_DIST_DIR_%\%_PKG_NAME_%.zip
powershell Compress-Archive %_DIST_DIR_%\* %_DIST_DIR_%\%_PKG_NAME_%.zip
if errorlevel 1 (
    echo Powershell Compress-Archive Failure: %errorlevel%
    GOTO ERROR_EXIT
)

exit /b 0

:ERROR_EXIT
    if exist %_DIST_DIR_% rmdir /S /Q %_DIST_DIR_%
    exit /b %errorlevel%
