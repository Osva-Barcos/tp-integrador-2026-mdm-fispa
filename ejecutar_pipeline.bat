@echo off
REM ==========================================================================
REM  Actualizar Base Maestra Fispa - ejecucion en un solo paso (doble clic)
REM  1) Verifica que Python este instalado
REM  2) Prepara el entorno e instala lo necesario (solo la primera vez)
REM  3) Ejecuta el proceso y avisa donde quedaron los archivos
REM ==========================================================================
chcp 65001 >nul
title Actualizar Base Maestra Fispa
cd /d "%~dp0"
echo.
echo  ==========================================================
echo     ACTUALIZACION DE LA BASE MAESTRA FISPA
echo  ==========================================================
echo.

REM --- 1. Buscar Python ------------------------------------------------------
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py -3"
if not defined PYTHON where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    echo  [!] No se encontro Python en esta computadora.
    echo      Pida a Sistemas que lo instale desde https://www.python.org/downloads/
    echo      ^(marcar la opcion "Add Python to PATH" al instalar^).
    echo.
    pause
    exit /b 1
)

REM --- 2. Preparar entorno (solo la primera vez) -----------------------------
if not exist ".venv\Scripts\python.exe" (
    echo  Preparando el programa por primera vez, espere unos minutos...
    %PYTHON% -m venv .venv
    if errorlevel 1 goto error_entorno
)
".venv\Scripts\python.exe" -c "import pandas, openpyxl, requests, bs4" >nul 2>nul
if errorlevel 1 (
    echo  Instalando componentes necesarios ^(requiere internet^)...
    ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
    if errorlevel 1 goto error_entorno
)

REM --- 3. Ejecutar el proceso ------------------------------------------------
echo  Procesando, no cierre esta ventana...
echo.
".venv\Scripts\python.exe" src\pipeline.py
set "RESULTADO=%errorlevel%"
echo.
echo  ==========================================================
if "%RESULTADO%"=="0" (
    echo   PROCESO TERMINADO CORRECTAMENTE
) else if "%RESULTADO%"=="2" (
    echo   NO SE PUDO PROCESAR: revise el mensaje "PROBLEMA" de arriba.
) else (
    echo   PROCESO TERMINADO CON ADVERTENCIAS GRAVES: NO DISTRIBUIR.
)
echo  ==========================================================
echo.
echo   Los archivos quedaron en la carpeta:
echo     %~dp0salida
echo.
echo     - base_maestra.csv        ^(base para publicar^)
echo     - errores_sin_mapeo.csv   ^(articulos que no se pudieron cruzar^)
echo     - control_calidad.txt     ^(LEER ANTES DE DISTRIBUIR^)
echo     - log_proceso.txt         ^(detalle completo del proceso^)
echo     - precio_menor_costo.csv  ^(precios por debajo del costo, para Comercial^)
echo.
if exist "salida" start "" explorer "%~dp0salida"
pause
exit /b %RESULTADO%

:error_entorno
echo.
echo  [!] No se pudieron instalar los componentes necesarios.
echo      Verifique la conexion a internet y vuelva a intentar.
echo      Si el problema sigue, avise a Sistemas.
pause
exit /b 1
