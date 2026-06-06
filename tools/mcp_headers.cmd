@echo off
REM Envoltura para que Claude Code (headersHelper) ejecute el helper en Python.
REM Usa el Python real (no el stub de la Store) y el script junto a este .cmd.
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%~dp0mcp_headers.py"
