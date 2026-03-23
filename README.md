# TFT Monitor

Backend-focused Python app that tracks Teamfight Tactics (TFT) games and enforces play-time limits after each game ends.

It combines:
- Riot API match history (`riotwatcher`) for counts/history
- Local League Client (LCU) event monitoring (`lcu-driver`) for real-time `EndOfGame` detection
- Optional desktop notifications and force-close behavior

## Tech Stack

- Python 3
- FastAPI
- Uvicorn
- Pydantic + pydantic-settings
- riotwatcher
- lcu-driver
- plyer
- psutil

## Features

- `GET /games/count` for total/today/session counts
- `GET /games/session` for current session summary
- `GET /games/history?count=N` for recent match summaries
- `GET /limits` for current limiter configuration
- Real-time game-end detection via LCU gameflow events
- Notification when nearing or hitting limits
- Optional process termination after limit reached

## Prerequisites

- Python 3.10+ recommended
- Riot API key from <https://developer.riotgames.com>
- League client installed (for LCU monitoring features)

## Setup

### macOS / Linux

1. Clone and enter project:

```bash
git clone <your-repo-url>
cd TFTMonitor
```

2. Create virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create `.env` file (example below).

### Windows (PowerShell)

1. Clone and enter project:

```powershell
git clone <your-repo-url>
cd TFTMonitor
```

2. Create virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Create `.env` file (example below).

## Environment Variables

Create `.env` in the project root:

```env
# Riot API
RIOT_API_KEY=RGAPI-your-key
RIOT_REGION=americas
RIOT_PLATFORM=na1

# Player identity: either set PUUID directly OR game name + tag
PUUID=
GAME_NAME=your_game_name
TAG_LINE=your_tag

# Limits
DAILY_GAME_CAP=10
SESSION_GAME_CAP=5
ENABLE_NOTIFICATION=true
ENABLE_FORCE_CLOSE=false
FORCE_CLOSE_DELAY_SECONDS=8

# Polling / server
MATCH_POLL_INTERVAL=90
HOST=127.0.0.1
PORT=8000
```

Notes:
- Valid `RIOT_REGION` values: `americas`, `europe`, `asia`, `sea`
- For NA accounts, use `RIOT_REGION=americas` and `RIOT_PLATFORM=na1`

## Run

### macOS / Linux

```bash
source venv/bin/activate
uvicorn main:app --reload
```

### Windows (PowerShell)

```powershell
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Open:
- API root: <http://127.0.0.1:8000>
- Health: <http://127.0.0.1:8000/health>
- Swagger docs: <http://127.0.0.1:8000/docs>

## Quick Test: Notify After 1 Game

To verify end-to-end behavior quickly:

1. Set in `.env`:

```env
SESSION_GAME_CAP=1
DAILY_GAME_CAP=1
ENABLE_NOTIFICATION=true
ENABLE_FORCE_CLOSE=false
```

2. Restart app:

```bash
uvicorn main:app --reload
```

3. Ensure League client is open and logged in.
4. Play and finish one TFT game.
5. Expected:
   - LCU logs phase changes
   - Session count increments to 1
   - Limit-reached notification appears

## API Endpoints

- `GET /` - service status
- `GET /health` - runtime health + region/platform + session game count
- `GET /games/count` - recent total/today/session counts
- `GET /games/session` - session metadata and count
- `GET /games/history?count=10` - recent match summaries (1-100)
- `GET /limits` - current limiter config

## Auto-Start on macOS (Optional)

Included helper files:
- `scripts/start_tft_monitor.sh`
- `scripts/com.tftmonitor.plist.example`

Basic flow:
1. Create logs dir:
   ```bash
   mkdir -p logs
   ```
2. Copy plist template:
   ```bash
   cp scripts/com.tftmonitor.plist.example ~/Library/LaunchAgents/com.tftmonitor.plist
   ```
3. Update paths in plist if needed.
4. Load agent:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.tftmonitor.plist
   ```

Disable:
```bash
launchctl unload ~/Library/LaunchAgents/com.tftmonitor.plist
```

## Auto-Start on Windows (Optional)

Use Task Scheduler to run the app at logon.

1. Open **Task Scheduler** -> **Create Task...**
2. **General** tab:
   - Name: `TFT Monitor`
3. **Triggers** tab:
   - New -> Begin the task: `At log on`
4. **Actions** tab:
   - New -> Action: `Start a program`
   - Program/script:
     `C:\path\to\TFTMonitor\venv\Scripts\python.exe`
   - Add arguments:
     `-m uvicorn main:app --host 127.0.0.1 --port 8000`
   - Start in:
     `C:\path\to\TFTMonitor`
5. Save task and test with **Run**.

Disable by opening Task Scheduler and disabling/deleting the `TFT Monitor` task.

## Security Notes

- Do not commit `.env` (already gitignored).
- Rotate Riot API key if accidentally exposed.
- Keep `ENABLE_FORCE_CLOSE=false` until you verify notifications and flow.

## Troubleshooting

- `403` from Riot API:
  - Check API key is valid (dev keys expire every 24h)
  - Confirm `RIOT_REGION` is correct (`americas` for NA)
- No LCU events:
  - Ensure League client is running and logged in
- No desktop notifications:
  - Check OS notification permissions for terminal/python
