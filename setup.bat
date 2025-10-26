@echo off
echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install opencv-python ultralytics firebase-admin

echo Setup complete! Run 'venv\Scripts\activate.bat' to activate the environment
