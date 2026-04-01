# Windows 11 Deployment Guide

Permanent installation of New Business Locator on a Windows 11 machine, including the API server, frontend dashboard, and scheduled weekly ETL pipeline runs.

---

## Prerequisites

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.11+ | https://www.python.org/downloads/ |
| Node.js | 18 LTS+ | https://nodejs.org/ |
| Git | latest | https://git-scm.com/download/win |

During Python installation, **check "Add python.exe to PATH"** on the first screen.

---

## 1. Clone the Repository

Open **PowerShell** (not CMD) and run:

```powershell
cd C:\
git clone https://github.com/AJStudios63/newBusinessLocator.git
cd newBusinessLocator
```

> All paths below assume `C:\newBusinessLocator`. Adjust if you chose a different location.

---

## 2. Python Backend Setup

### Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If you get an execution policy error, run this first (as Administrator):
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Set the Tavily API key

Create a `.env` file in the project root:

```powershell
New-Item -Path .env -ItemType File
```

Open it in Notepad and add:

```
TAVILY_API_KEY=your-key-here
```

### Verify

```powershell
python -m pytest tests/ -q
```

All 330 tests should pass.

---

## 3. Frontend Setup

```powershell
cd frontend
npm install
npm run build
cd ..
```

---

## 4. Test Run (Manual)

Open two PowerShell windows, both in `C:\newBusinessLocator` with the venv activated:

**Window 1 -- API server:**
```powershell
.venv\Scripts\Activate.ps1
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Window 2 -- Frontend:**
```powershell
cd frontend
npm run start
```

Open http://localhost:3000 in a browser. If the dashboard loads, everything works.

Press `Ctrl+C` in both windows to stop.

---

## 5. Run as Windows Services (Permanent)

### Option A: NSSM (Recommended -- simplest)

[NSSM](https://nssm.cc/download) (Non-Sucking Service Manager) wraps any executable as a Windows service.

1. Download `nssm.exe` and place it in `C:\newBusinessLocator\scripts\`.

2. **Install the API service:**

```powershell
.\scripts\nssm.exe install NewBusinessLocatorAPI "C:\newBusinessLocator\.venv\Scripts\python.exe" "-m uvicorn api.main:app --host 127.0.0.1 --port 8000"
.\scripts\nssm.exe set NewBusinessLocatorAPI AppDirectory "C:\newBusinessLocator"
.\scripts\nssm.exe set NewBusinessLocatorAPI AppEnvironmentExtra "TAVILY_API_KEY=your-key-here"
.\scripts\nssm.exe set NewBusinessLocatorAPI DisplayName "New Business Locator API"
.\scripts\nssm.exe set NewBusinessLocatorAPI Start SERVICE_AUTO_START
.\scripts\nssm.exe set NewBusinessLocatorAPI AppStdout "C:\newBusinessLocator\logs\api_stdout.log"
.\scripts\nssm.exe set NewBusinessLocatorAPI AppStderr "C:\newBusinessLocator\logs\api_stderr.log"
.\scripts\nssm.exe start NewBusinessLocatorAPI
```

3. **Install the Frontend service:**

```powershell
.\scripts\nssm.exe install NewBusinessLocatorWeb "C:\Program Files\nodejs\node.exe" "node_modules\.bin\next" "start" "--port" "3000"
.\scripts\nssm.exe set NewBusinessLocatorWeb AppDirectory "C:\newBusinessLocator\frontend"
.\scripts\nssm.exe set NewBusinessLocatorWeb DisplayName "New Business Locator Web"
.\scripts\nssm.exe set NewBusinessLocatorWeb Start SERVICE_AUTO_START
.\scripts\nssm.exe set NewBusinessLocatorWeb AppStdout "C:\newBusinessLocator\logs\web_stdout.log"
.\scripts\nssm.exe set NewBusinessLocatorWeb AppStderr "C:\newBusinessLocator\logs\web_stderr.log"
.\scripts\nssm.exe start NewBusinessLocatorWeb
```

Both services will now start automatically on boot.

**Managing services:**
```powershell
# Stop / start / restart
.\scripts\nssm.exe stop NewBusinessLocatorAPI
.\scripts\nssm.exe start NewBusinessLocatorAPI
.\scripts\nssm.exe restart NewBusinessLocatorAPI

# Edit configuration (opens GUI)
.\scripts\nssm.exe edit NewBusinessLocatorAPI

# Remove a service
.\scripts\nssm.exe remove NewBusinessLocatorAPI confirm
```

### Option B: Task Scheduler (No extra software)

If you prefer not to install NSSM, you can use PowerShell startup scripts:

1. Create `C:\newBusinessLocator\scripts\start-servers.ps1`:

```powershell
# Start API server
$apiProcess = Start-Process -FilePath "C:\newBusinessLocator\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory "C:\newBusinessLocator" `
    -WindowStyle Hidden -PassThru

# Start frontend
$webProcess = Start-Process -FilePath "npm" `
    -ArgumentList "run", "start" `
    -WorkingDirectory "C:\newBusinessLocator\frontend" `
    -WindowStyle Hidden -PassThru

# Log PIDs for management
"API PID: $($apiProcess.Id)" | Out-File "C:\newBusinessLocator\logs\pids.txt"
"Web PID: $($webProcess.Id)" | Add-Content "C:\newBusinessLocator\logs\pids.txt"
```

2. Open **Task Scheduler** (`taskschd.msc`), create a new task:
   - **General tab:** Name = `NewBusinessLocator`, check "Run whether user is logged on or not", check "Run with highest privileges"
   - **Trigger:** At startup
   - **Action:** Start a program: `powershell.exe`, Arguments: `-ExecutionPolicy Bypass -File C:\newBusinessLocator\scripts\start-servers.ps1`
   - **Settings:** Uncheck "Stop the task if it runs longer than..."

---

## 6. Scheduled Weekly ETL Pipeline

The macOS LaunchAgent equivalent on Windows is **Task Scheduler**.

1. Open **Task Scheduler** (`Win+R` -> `taskschd.msc`)
2. Click **Create Task** (not "Create Basic Task")

**General tab:**
- Name: `NewBusinessLocator Weekly ETL`
- Check "Run whether user is logged on or not"

**Trigger tab:**
- New -> Weekly, every Sunday at 6:00 AM

**Action tab:**
- Program: `C:\newBusinessLocator\.venv\Scripts\python.exe`
- Arguments: `-m cli.main run`
- Start in: `C:\newBusinessLocator`

**Settings tab:**
- Uncheck "Stop the task if it runs longer than..."
- Check "If the task fails, restart every 10 minutes, up to 3 times"

**Environment:** To ensure the Tavily API key is available, wrap the call in a batch file:

Create `C:\newBusinessLocator\scripts\weekly-etl.bat`:
```batch
@echo off
cd /d C:\newBusinessLocator
set TAVILY_API_KEY=your-key-here
C:\newBusinessLocator\.venv\Scripts\python.exe -m cli.main run >> logs\etl_stdout.log 2>> logs\etl_stderr.log
```

Then point the Task Scheduler action at `weekly-etl.bat` instead.

---

## 7. Windows Firewall (Optional -- LAN access)

If you want other devices on your network to access the dashboard:

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "NewBusinessLocator API" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "NewBusinessLocator Web" -Direction Inbound -Port 3000 -Protocol TCP -Action Allow
```

Then change the API `--host` from `127.0.0.1` to `0.0.0.0` in your NSSM config or startup script. Access from other devices at `http://<windows-ip>:3000`.

---

## 8. Updating

```powershell
cd C:\newBusinessLocator
git pull origin main

# Update Python deps
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Update frontend
cd frontend
npm install
npm run build
cd ..

# Restart services (NSSM)
.\scripts\nssm.exe restart NewBusinessLocatorAPI
.\scripts\nssm.exe restart NewBusinessLocatorWeb
```

---

## 9. Logs and Troubleshooting

| Log | Location |
|-----|----------|
| ETL pipeline | `logs\pipeline.log` |
| API stdout/stderr | `logs\api_stdout.log`, `logs\api_stderr.log` |
| Frontend stdout/stderr | `logs\web_stdout.log`, `logs\web_stderr.log` |
| Scheduled ETL | `logs\etl_stdout.log`, `logs\etl_stderr.log` |

**Common issues:**

| Problem | Fix |
|---------|-----|
| `python` not found | Re-install Python with "Add to PATH" checked, or use full path `C:\Python312\python.exe` |
| Port 8000/3000 in use | Check with `netstat -ano \| findstr :8000` and kill the process, or change the port |
| NSSM service won't start | Run `.\scripts\nssm.exe edit ServiceName` and verify all paths are correct |
| Execution policy error | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| SQLite locked errors | Ensure only one ETL run is active at a time; the API uses WAL mode for concurrent reads |
| `.env` not loaded | Services don't read `.env` automatically -- set env vars via NSSM or the `.bat` wrapper |

---

## Quick Reference

```
Dashboard:    http://localhost:3000
API Docs:     http://localhost:8000/docs
Project root: C:\newBusinessLocator
Virtual env:  C:\newBusinessLocator\.venv
Database:     C:\newBusinessLocator\data\leads.db
```
