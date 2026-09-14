# Run doc — BIS Buddy (backend :8000 + frontend :5173)

## One-time artifact reproduction (fresh checkout)

All commands run from the repo root unless noted. Python is `python` (Anaconda, on
PATH). Node is a portable install at
`C:\Users\deepak patel\bisbuddy-tools\node-v22.20.0-win-x64` — it is NOT on the
system PATH, so prefix PATH for every npm/node command:

```
export PATH="$HOME/bisbuddy-tools/node-v22.20.0-win-x64:$PATH"
```

1. Backend deps: `pip install -r backend/requirements.txt` (already installed).
2. Frontend deps: `cd frontend && npm install` (already installed — `node_modules` exists).
3. Config: `cp .env.example .env` — only needed when enabling Gemini
   (see `GEMINI_SETUP.md`). Offline fallback mode needs no `.env`.
4. Sample data (only if `data/bisbuddy.db` is missing):
   `python scripts/build_sample_pdfs.py` then `python scripts/seed_data.py`.
   Seeded logins: `admin@bisbuddy.in / Admin@12345`, `demo@bisbuddy.in / Demo@12345`.

## Running the servers

Backend (detached, log to .freebuff/backend.log / .freebuff/backend.err.log):

```
powershell -NoProfile -Command "(Start-Process -FilePath 'python.exe' -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory '<repo>\backend' -RedirectStandardOutput '<repo>\.freebuff\backend.log' -RedirectStandardError '<repo>\.freebuff\backend.err.log' -WindowStyle Hidden -PassThru).Id"
```

Note: the Start-Process call can time out the shell tool even though the server
starts — verify with `netstat -ano | grep ":8000"` and
`curl http://127.0.0.1:8000/health` instead of trusting the exit status.

Frontend (detached; PATH must include node for the npm.cmd shim):

```
powershell -NoProfile -Command '$env:Path = "C:\Users\deepak patel\bisbuddy-tools\node-v22.20.0-win-x64;" + $env:Path; (Start-Process -FilePath "C:\Users\deepak patel\bisbuddy-tools\node-v22.20.0-win-x64\npm.cmd" -ArgumentList "run","dev" -WorkingDirectory "<repo>\frontend" -RedirectStandardOutput "<repo>\.freebuff\frontend.log" -RedirectStandardError "<repo>\.freebuff\frontend.err.log" -WindowStyle Hidden -PassThru).Id'
```

Vite listens on port 5173 (config in `frontend/vite.config.ts`, proxy `/api` → :8000).
If 5173 is taken, Vite auto-increments — check `.freebuff/frontend.log` for the actual
port and register the preview with that URL.

Health checks: `curl http://127.0.0.1:8000/health` and
`curl -o /dev/null -w "%{http_code}" http://localhost:5173/`.
