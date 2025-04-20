@echo off
echo Upgrading pip...
python -m pip install --upgrade pip || echo Failed to upgrade pip. & pause & exit /b 1

echo Installing required packages (pygame, pillow, pywin32, mutagen)...
python -m pip install pygame pillow pywin32 mutagen || echo Failed to install packages. Please check your internet connection and Python/pip setup. & pause & exit /b 1

echo.
echo Dependencies should now be installed.
pause 