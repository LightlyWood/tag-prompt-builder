@echo off
title 运行 Tag Prompt Builder

:: 切换到项目根目录（脚本所在目录）
cd /d "%~dp0"

:: 激活虚拟环境
if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
    echo 虚拟环境已激活。
) else (
    echo 未找到虚拟环境，尝试使用系统 Python。
)

:: 运行主程序
if exist "tag_prompt_builder\main.py" (
    python tag_prompt_builder\main.py
) else (
    echo 错误：找不到 main.py
    pause
    exit /b
)

pause