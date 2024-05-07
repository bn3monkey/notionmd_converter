py -m venv venv
echo "Create Virtual Environment"
call ./venv/Scripts/activate.bat
echo "Virtual Environment Activated"
pip install -r requirements.txt
echo "Dependency installed"
py main.py
echo "Run"
deactivate
echo "Deactivate"