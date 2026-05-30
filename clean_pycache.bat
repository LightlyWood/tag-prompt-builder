@echo off
setlocal enabledelayedexpansion
title 清理 Python 缓存文件

echo ===============================================
echo   清理 __pycache__ 文件夹和 .pyc 文件
echo ===============================================
echo.

:: 询问是否递归删除
set /p "confirm=确认要删除当前目录下所有 __pycache__ 文件夹和 .pyc 文件吗？(Y/N): "
if /i not "!confirm!"=="Y" (
    echo 操作已取消。
    pause
    exit /b
)

echo.
echo 正在搜索并删除 __pycache__ 文件夹...
set /a del_dirs=0
for /f "delims=" %%D in ('dir /s /b /ad "__pycache__" 2^>nul') do (
    rd /s /q "%%D" 2>nul
    if !errorlevel! equ 0 (
        echo [删除] %%D
        set /a del_dirs+=1
    ) else (
        echo [失败] %%D
    )
)

echo.
echo 正在删除所有 .pyc 文件...
set /a del_files=0
for /f "delims=" %%F in ('dir /s /b "*.pyc" 2^>nul') do (
    del /f /q "%%F" 2>nul
    if !errorlevel! equ 0 (
        echo [删除] %%F
        set /a del_files+=1
    ) else (
        echo [失败] %%F
    )
)

echo.
echo ===============================================
echo 操作完成。
echo 删除 __pycache__ 文件夹: %del_dirs%
echo 删除 .pyc 文件: %del_files%
echo ===============================================
pause