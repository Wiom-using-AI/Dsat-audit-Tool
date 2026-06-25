@echo off
echo Installing dependencies...
pip install flask --quiet
echo Starting DSAT Audit Tool...
echo Open your browser at: http://localhost:5001
echo Default login: admin@wiom.in / admin123
echo.
python app.py
pause
