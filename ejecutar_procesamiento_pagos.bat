@echo off
REM Script para ejecutar el procesamiento automático de pagos
REM Se debe programar en el Programador de Tareas de Windows para ejecutarse diariamente

echo ========================================
echo LAMBDA - PROCESAMIENTO AUTOMATICO PAGOS
echo ========================================
echo Fecha: %date% %time%
echo.

REM Cambiar al directorio del proyecto
cd /d "C:\Users\Jorman\Desktop\LAMBDA_proyecto_b2b_API"

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar comando con envío de emails
echo Ejecutando procesamiento de pagos...
python manage.py procesar_pagos --enviar-emails

REM Verificar resultado
if %errorlevel% equ 0 (
    echo.
    echo ✅ Procesamiento completado exitosamente
) else (
    echo.
    echo ❌ Error en el procesamiento
)

echo.
echo ========================================
echo Procesamiento finalizado: %date% %time%
echo ========================================

REM Opcional: Guardar log
echo [%date% %time%] Procesamiento de pagos ejecutado >> logs\procesamiento_pagos.log

pause