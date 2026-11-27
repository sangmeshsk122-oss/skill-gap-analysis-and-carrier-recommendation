@echo off
setlocal

set "MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.4\bin"
set "MYSQL_CONFIG=C:\Users\sangm\AppData\Local\SkillMatrixMySQL\my.ini"

if not exist "%MYSQL_CONFIG%" (
    echo MySQL config not found: "%MYSQL_CONFIG%"
    pause
    exit /b 1
)

if not exist "C:\my.ini" (
    copy "%MYSQL_CONFIG%" "C:\my.ini" >nul
    if errorlevel 1 (
        echo Could not copy the MySQL config to C:\my.ini. Run this script as Administrator.
        pause
        exit /b 1
    )
)

sc.exe query MySQL84 >nul 2>&1
if errorlevel 1 (
    "%MYSQL_BIN%\mysqld.exe" --install MySQL84
    if errorlevel 1 (
        echo Could not register the MySQL84 service.
        pause
        exit /b 1
    )
)

sc.exe config MySQL84 start= auto
if errorlevel 1 (
    echo Could not set MySQL84 to start automatically.
    pause
    exit /b 1
)

sc.exe start MySQL84
if errorlevel 1 (
    sc.exe query MySQL84 | findstr /C:"RUNNING" >nul
    if errorlevel 1 (
        echo MySQL84 did not start. Check the service error above.
        pause
        exit /b 1
    )
)

sc.exe query MySQL84
pause
