@echo off

powershell -WindowStyle Hidden -Command ^
"Start-Process 'python' ^
-ArgumentList 'app.py' ^
-WorkingDirectory 'C:\Users\Produccion\mapeo-inventario' ^
-WindowStyle Hidden"
