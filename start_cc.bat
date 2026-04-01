@echo off
set CLAUDE_CODE_GIT_BASH_PATH=D:\Git\Git\bin\bash.exe
set DISABLE_TELEMETRY=1
set CLAUDE_CODE_SYNTAX_HIGHLIGHT=0
cd /d D:\CC\cloud-code\claude-code-source
bun dist/cli.js --permission-mode default %*
