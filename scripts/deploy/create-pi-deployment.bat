@echo off
REM Create a minimal deployment package for Raspberry Pi (Windows version)
REM Excludes tests, simulation, documentation, and development files

setlocal enabledelayedexpansion

set DEPLOY_DIR=pi-deployment
set SOURCE_DIR=software

echo Creating Raspberry Pi deployment package...

REM Remove old deployment if it exists
if exist "%DEPLOY_DIR%" (
    echo Removing old deployment directory...
    rmdir /s /q "%DEPLOY_DIR%"
)

REM Create deployment directory structure
mkdir "%DEPLOY_DIR%"

REM Copy essential Python files
echo Copying essential files...

REM Main entry point
copy "%SOURCE_DIR%\main.py" "%DEPLOY_DIR%\" >nul

REM Path bootstrapper (needed for imports)
copy "%SOURCE_DIR%\path_bootstrap.py" "%DEPLOY_DIR%\" >nul

REM Configuration
copy "%SOURCE_DIR%\config.py" "%DEPLOY_DIR%\" >nul
copy "%SOURCE_DIR%\flow_control_modes.py" "%DEPLOY_DIR%\" >nul

REM Controllers (all Python files, exclude __pycache__)
xcopy /E /I /Y "%SOURCE_DIR%\controllers" "%DEPLOY_DIR%\controllers\" >nul
for /r "%DEPLOY_DIR%\controllers" %%f in (*.pyc) do del /q "%%f" 2>nul
for /d /r "%DEPLOY_DIR%\controllers" %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul

REM Drivers (all Python files)
xcopy /E /I /Y "%SOURCE_DIR%\drivers" "%DEPLOY_DIR%\drivers\" >nul
for /r "%DEPLOY_DIR%\drivers" %%f in (*.pyc) do del /q "%%f" 2>nul
for /d /r "%DEPLOY_DIR%\drivers" %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul
REM Remove test files from drivers/camera
for /r "%DEPLOY_DIR%\drivers\camera" %%f in (test_*.py) do del /q "%%f" 2>nul

REM Droplet detection (all Python files, exclude tests)
xcopy /E /I /Y "%SOURCE_DIR%\droplet-detection" "%DEPLOY_DIR%\droplet-detection" >nul
for /r "%DEPLOY_DIR%\droplet-detection" %%f in (*.pyc) do del /q "%%f" 2>nul
for /d /r "%DEPLOY_DIR%\droplet-detection" %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul
REM Remove test and benchmark files
for /r "%DEPLOY_DIR%\droplet-detection" %%f in (test_*.py benchmark.py optimize.py run_tests.sh) do del /q "%%f" 2>nul

REM Web app (all files)
xcopy /E /I /Y "%SOURCE_DIR%\rio-webapp" "%DEPLOY_DIR%\rio-webapp\" >nul
for /r "%DEPLOY_DIR%\rio-webapp" %%f in (*.pyc) do del /q "%%f" 2>nul
for /d /r "%DEPLOY_DIR%\rio-webapp" %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul

REM Configurations
xcopy /E /I /Y "%SOURCE_DIR%\configurations" "%DEPLOY_DIR%\configurations\" >nul

REM Requirements file (works for both 32-bit and 64-bit)
copy "%SOURCE_DIR%\requirements-pi.txt" "%DEPLOY_DIR%\" >nul

REM Create setup script for Pi (using heredoc-like approach)
(
echo #!/bin/bash
echo # Setup script for Raspberry Pi ^(First time only^)
echo # Run this after copying the deployment package to the Pi
echo # Installs packages to system Python ^(no virtual environment^)
echo.
echo set -e
echo.
echo echo "Rio Microfluidics Controller - Pi Setup"
echo echo "========================================"
echo echo ""
echo.
echo # Check if we're in the right directory
echo if [ ! -f "main.py" ]; then
echo     echo "Error: main.py not found. Please run this script from the deployment directory."
echo     exit 1
echo fi
echo.
echo echo "Step 1: Upgrading pip..."
echo python3 -m pip install --user --upgrade pip
echo.
echo echo "Step 2: Installing packages to system Python..."
echo echo "Note: Installing to system Python ^(no virtual environment^)."
echo echo "      Using --user flag to avoid permission issues ^(installs to ~/.local/lib/python3.x/site-packages^)"
echo echo ""
echo if [ -f "requirements-pi.txt" ]; then
echo     python3 -m pip install --user -r requirements-pi.txt
echo else
echo     echo "Warning: requirements file not found, installing manually..."
echo     python3 -m pip install --user "Flask&gt;=2.0.0,^&lt;4.0.0"
echo     python3 -m pip install --user "Flask-SocketIO&gt;=5.4.0,^&lt;6.0.0"
echo     python3 -m pip install --user "Werkzeug&gt;=2.0.0,^&lt;4.0.0"
echo     python3 -m pip install --user "Jinja2&gt;=3.0.0"
echo     python3 -m pip install --user "MarkupSafe&gt;=2.0.0"
echo     python3 -m pip install --user "itsdangerous&gt;=2.0.0"
echo     python3 -m pip install --user "gevent&gt;=23.0.0,^&lt;25.0.0" "gevent-websocket&gt;=0.10.1"
echo     python3 -m pip install --user "python-socketio&gt;=5.14.0" "python-engineio&gt;=4.9.0"
echo     python3 -m pip install --user "eventlet&gt;=0.33.0,^&lt;1.0.0"
echo     python3 -m pip install --user "opencv-python-headless&gt;=4.5.0,^&lt;5.0.0"
echo     python3 -m pip install --user "numpy&gt;=1.19.0,^&lt;2.0.0" "Pillow&gt;=9.0.0"
echo     python3 -m pip install --user "PyYAML&gt;=6.0"
echo fi
echo.
echo echo ""
echo echo "Step 3: Verifying installation..."
echo python3 -m pip list --user ^| grep -E "Flask^|SocketIO^|Werkzeug^|Jinja2^|MarkupSafe^|opencv^|numpy^|Pillow^|PyYAML" ^|^| echo "Warning: Some packages may not be installed correctly"
echo.
echo echo ""
echo echo "Setup complete!"
echo echo ""
echo echo "To run the application:"
echo echo "  1. export RIO_STROBE_CONTROL_MODE=strobe-centric  # or camera-centric"
echo echo "  2. export RIO_SIMULATION=false"
echo echo "  3. export RIO_DROPLET_ANALYSIS_ENABLED=true"
echo echo "  4. python main.py"
echo echo ""
echo echo "Or use the run.sh script after setting environment variables."
echo echo ""
echo echo "Note: Packages are installed to system Python. No virtual environment is used."
) > "%DEPLOY_DIR%\setup.sh"

REM Create run script for Pi
(
echo #!/bin/bash
echo # Run script for Raspberry Pi
echo # Uses system Python ^(no virtual environment^)
echo.
echo cd "$^(dirname "$0"^)"
echo.
echo # Set default environment variables if not set
echo export RIO_STROBE_CONTROL_MODE=${RIO_STROBE_CONTROL_MODE:-strobe-centric}
echo export RIO_SIMULATION=${RIO_SIMULATION:-false}
echo export RIO_DROPLET_ANALYSIS_ENABLED=${RIO_DROPLET_ANALYSIS_ENABLED:-true}
echo export RIO_FLOW_ENABLED=${RIO_FLOW_ENABLED:-false}
echo export RIO_HEATER_ENABLED=${RIO_HEATER_ENABLED:-false}
echo.
echo echo "Starting Rio microfluidics controller..."
echo echo "Control mode: $RIO_STROBE_CONTROL_MODE"
echo echo "Simulation: $RIO_SIMULATION"
echo echo "Droplet detection: $RIO_DROPLET_ANALYSIS_ENABLED"
echo echo ""
echo.
echo python main.py
) > "%DEPLOY_DIR%\run.sh"

REM Create .gitignore for deployment
(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *$py.class
echo *.so
echo .Python
echo venv-rio/
echo *.egg-info/
echo dist/
echo build/
echo.
echo # Snapshots
echo home/pi/snapshots/*.jpg
echo.
echo # IDE
echo .vscode/
echo .idea/
echo *.swp
echo *.swo
echo.
echo # OS
echo .DS_Store
echo Thumbs.db
) > "%DEPLOY_DIR%\.gitignore"

REM Create deployment info file
(
echo Rio Microfluidics Controller - Deployment Package
echo Created: %date% %time%
echo Source: open-microfluidics-workstation/software
echo.
echo This package contains:
echo - Main application code ^(main.py, config.py^)
echo - Controllers ^(hardware control logic^)
echo - Drivers ^(hardware communication^)
echo - Droplet detection module
echo - Web application ^(Flask, templates, static files^)
echo - Configuration examples
echo.
echo Excluded:
echo - Tests
echo - Simulation code
echo - Documentation ^(see main repository^)
echo - Development files
echo - Python cache files
) > "%DEPLOY_DIR%\DEPLOYMENT_INFO.txt"

echo.
echo Deployment package created in: %DEPLOY_DIR%\
echo.
echo To deploy to Raspberry Pi:
echo   1. Copy the %DEPLOY_DIR% folder contents to ~/rio-controller/ on your Raspberry Pi
echo   2. You can use:
echo      - SSH/SCP: scp -r %DEPLOY_DIR%\* pi@raspberrypi.local:~/rio-controller/
echo      - WinSCP: Connect to pi@raspberrypi.local, copy %DEPLOY_DIR%\ contents to ~/rio-controller/
echo      - USB Stick: Copy %DEPLOY_DIR%\ to USB stick, plug into Pi, copy from USB to ~/rio-controller/
echo   3. SSH to your Pi: ssh pi@raspberrypi.local
echo   4. Navigate to: cd ~/rio-controller
echo   5. Run setup ^(first time only^): ./setup.sh
echo   6. Run the application: ./run.sh
echo.
echo Important: Copy the CONTENTS of %DEPLOY_DIR%\ to ~/rio-controller/, not the folder itself.
echo            The destination should be ~/rio-controller/main.py, not ~/rio-controller/%DEPLOY_DIR%/main.py
echo.

endlocal

