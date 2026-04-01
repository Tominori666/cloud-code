@echo off
REM 用法: dispatch.bat "你的指令"
REM 例如: dispatch.bat "写一个hello world python脚本"

set CLAUDE_CODE_GIT_BASH_PATH=D:\Git\Git\bin\bash.exe
set ANTHROPIC_BASE_URL=http://127.0.0.1:5678
set ANTHROPIC_API_KEY=proxy
set DISABLE_AUTOUPDATER=1
set CLAUDE_CODE_SYNTAX_HIGHLIGHT=0
set CLAUDE_CONFIG_DIR=%TEMP%\claude-clone
if not exist "%CLAUDE_CONFIG_DIR%" mkdir "%CLAUDE_CONFIG_DIR%"
cd /d D:\CC\cloud-code\claude-code-source
bun dist/cli.js --permission-mode default -p %*
