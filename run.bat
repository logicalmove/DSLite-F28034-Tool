@echo off
chcp 65001 >nul
title DSLite工具_F28034

:: 查找 exe 文件
set "EXE_FOUND=0"
for /r "%~dp0" %%f in (*.exe) do (
    if /i "%%~nxf"=="DSLite_F28034.exe" (
        set "EXE_PATH=%%f"
        set "EXE_FOUND=1"
        goto :run
    )
)

echo ❌ 找不到 DSLite_F28034.exe
echo 请把 run.bat 放到和 exe 同一个文件夹
pause
exit

:run
echo ✅ 找到: %EXE_PATH%
echo.

:: 设置工作目录为 exe 所在目录
cd /d "%~dp0"

:: 运行
start "" "%EXE_PATH%"
exit
