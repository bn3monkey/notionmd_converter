@REM py -m venv venv
@REM echo "Create Virtual Environment"
@REM call ./venv/Scripts/activate.bat
@REM echo "Virtual Environment Activated"
@REM pip install -r requirements.txt
echo "Dependency installed"
py main.py --out 1
@REM echo --out 1(html) 2(markdown) 3(pdf)
@REM echo "Run"
@REM deactivate
@REM echo "Deactivate"