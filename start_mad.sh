#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "== Evidence-MAD startup =="

# Check venv
if [ ! -d venv ] && [ ! -d .venv ]; then
  echo "ERROR: No venv or .venv directory found." >&2
  echo "Run: python3 -m venv venv && venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# Source the venv (prefer venv/ over .venv/)
if [ -d venv ]; then
  source venv/bin/activate
elif [ -d .venv ]; then
  source .venv/bin/activate
fi

# Check .env
if [ ! -f .env ]; then
  echo "ERROR: .env not found. Run: cp .env.example .env, then edit it." >&2
  exit 1
fi

# Check google-genai is installed
python -c "import google.genai" 2>/dev/null || {
  echo "ERROR: google-genai missing. Run: pip install google-genai" >&2
  exit 1
}

# Read settings via the app's own config loader
read -r DEMO LLMKEY GKEY MODEL < <(python - <<'PY'
from config import settings as s
print(int(s.demo_mode), int(bool(s.llm_api_key)), int(bool(s.gemini_api_key)), s.opencode_model)
PY
)

if [ "$DEMO" = "0" ] && [ "$LLMKEY" = "0" ]; then
  echo "ERROR: LLM_API_KEY (Groq/Atria) is empty and DEMO_MODE is not true." >&2
  exit 1
fi

if [ "$GKEY" = "0" ]; then
  echo "WARNING: GEMINI_API_KEY is empty. Every query will use the OpenCode fallback."
fi

# Check opencode CLI
if command -v opencode >/dev/null 2>&1; then
  echo "OpenCode CLI found. Checking model $MODEL ..."
  if timeout 90 opencode run --model "$MODEL" "Reply with the single word OK" >/tmp/mad1_opencode_check.log 2>&1; then
    echo "OpenCode OK."
  else
    echo "WARNING: OpenCode model check failed. See /tmp/mad1_opencode_check.log"
    echo "The AI agent will fall back to Gemini only, or both may fail."
  fi
else
  echo "WARNING: 'opencode' not found on PATH. The AI agent OpenCode fallback will not work."
fi

# Free stale instances of this app from a previous run (they block the ports)
free_port() {
  local port="$1"
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  elif command -v fuser >/dev/null 2>&1; then
    fuser -k tcp:"$port" 2>/dev/null || true
    return
  else
    pids=$(ss -ltnp 2>/dev/null | grep -E ":$port " | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)
  fi
  if [ -n "$pids" ]; then
    for pid in $pids; do
      local cmd
      cmd=$(ps -o cmd= -p "$pid" 2>/dev/null || true)
      case "$cmd" in
        *uvicorn*api*|*http.server*3000*)
          kill "$pid" 2>/dev/null || true
          echo "Freed port $port (stopped stale process $pid)."
          ;;
        *) echo "WARNING: port $port is used by another program (pid $pid: ${cmd}). Start it manually." ;;
      esac
    done
    sleep 1
  fi
}

free_port 8000
free_port 3000

# Cleanup on exit
cleanup() { kill ${BACKEND_PID:-} ${FRONTEND_PID:-} 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Start backend
echo "Starting backend on port 8000..."
uvicorn api:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
for _ in $(seq 1 20); do
  curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 1
done
if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "ERROR: backend did not start" >&2
  exit 1
fi
echo "Backend ready."

# Start frontend
echo "Starting frontend on port 3000..."
python -m http.server 3000 --bind 127.0.0.1 --directory frontend &
FRONTEND_PID=$!

echo ""
echo "Frontend : http://localhost:3000"
echo "API docs : http://127.0.0.1:8000/docs"
echo "Health   : http://127.0.0.1:8000/health"
echo ""
echo "Press Ctrl+C to stop."
wait
