# Evidence-MAD — Full Audit TODO List (completed Oct 15, 2026)

Every item below was audited file by file, fixed, and verified:
`pytest -q` → **100/100 passed** (94 original + 6 new fallback tests), and
`./start_mad.sh` now starts both servers cleanly.

---

## Phase A — Startup reliability (`./start_mad.sh`)
- [x] **A1. Stale-server port conflicts (the "errors every time you start" cause).**
      Orphaned `uvicorn api:app` / `python -m http.server` processes from a previous
      run kept ports 8000/3000 occupied → `OSError: [Errno 98] Address already in use`.
      Killed the stale processes.
- [x] **A2. `start_mad.sh` hardened** — new `free_port()` function frees stale
      instances of *this app* on ports 8000 and 3000 before starting (checks the
      process command line, so it only kills uvicorn/api or http.server/frontend,
      never an unrelated program; warns instead if another app owns the port).

## Phase B — Agent fallbacks (user requirements)
- [x] **B1. DuckDuckGo (Web Agent) silent fill-in.** When DuckDuckGo is unavailable
      (rate limit 429, timeout, 5xx, or blocked/empty results), the agent now answers
      through OpenCode `opencode/space-bunny-free` and returns the results in the
      normal web-result shape — the UI keeps showing "**Web Agent (DuckDuckGo)**".
      No message like "DuckDuckGo rate limit exceeded, used OpenCode" appears anywhere.
- [x] **B2. Wikipedia (Reference Agent) fill-in widened** — previously only caught
      HTTP errors/timeouts; now catches **any** failure (network error, parse error,
      empty result list, rate limit) and answers through OpenCode
      `opencode/mimo-v2.6-flash-free`, presented as genuine Wikipedia results
      (titles "Wikipedia - <query>", wikipedia.org links), with no mention of the
      switch anywhere.
- [x] **B3. Crossref (Scholarly Agent) unchanged** — deliberately no fallback,
      as before.
- [x] **B4. New config field** `OPENCODE_WEB_MODEL` in `config.py` (default
      `opencode/space-bunny-free`), added to `.env` and `.env.example`;
      `OPENCODE_WIKI_MODEL` also added to `.env`/`.env.example` where it was missing.
- [x] **B5. Gemini→OpenCode fallback verified live** — with the Gemini key over
      quota (429 RESOURCE_EXHAUSTED), the AI Answer Agent automatically answered
      through `opencode/muse-spark-1.3-contributor-free` and the query still completed.

## Phase C — Real Gemini failure fixed (provider deprecation)
- [x] **C1. `gemini-2.5-flash` is retired upstream (404 NOT_FOUND for the key).**
      `config.py` default and `.env`/`.env.example` `GEMINI_MODEL` updated to
      `gemini-3.8-flash` (the replacement the upstream error message names).
      Model now responds (was 404, now only quota-limited → falls back cleanly).

## Phase D — Retrieval quality
- [x] **D1. DuckDuckGo links decoded.** DDG HTML results point to redirect links
      `duckduckgo.com/l/?uddg=<encoded>`; added `SearchAgent._decode_ddg_link()`
      so sources now expose the real destination URLs instead of DDG redirects.
- [x] **D2. Fallback logs downgraded to debug level** — provider-switch details
      stay in the app log only, never reach the UI/API response.

## Phase E — Files verified healthy (no changes needed)
- [x] `app.py` — full pipeline (router → normalizer → aggregator → classifier →
      debate → judge → generator), AI Answer Agent runs in parallel via
      ThreadPoolExecutor, retry logic preserves non-registry agents.
- [x] `api.py` — CORS for both frontend ports, all response models wired,
      `/solve` + `/api/solve` endpoints (frontend uses `/api/solve`).
- [x] `llm_client.py` — retry/backoff, per-role call report, JSON extraction.
- [x] `run_mode.py` + `data/fixtures.json` — all 10 required fixture cases present.
- [x] `evidence/` — models, normalizer, aggregator, NLI detectors, comparator.
- [x] `conflict/classifier.py` — 5 conflict types + rule fallback + status tracking.
- [x] `debate/` — Proposer/Critic/Reviser/Judge/Manager with early stopping.
- [x] `output/generator.py` — 4 answer shapes by evidence state.
- [x] `evaluation/systems/` (single_llm, standard_mad, proposed_mad + 3 ablations),
      `evaluation/dataset.py` (60+ samples), `evaluation/metrics.py`.
- [x] `frontend/index.html` — light mode, blue buttons, no emojis, agent boxes,
      NLI table, decision banner, conflict panel, debate transcript, judge verdict,
      180 s fetch timeout.
- [x] `api/index.py` + `vercel.json` — Vercel entrypoint intact.
- [x] `requirements.txt` — every pinned version matches the installed venv exactly.
- [x] Previous instruction re-checked and intact: **Gemini primary → OpenCode
      `opencode/muse-spark-1.3-contributor-free` fallback → response passes into the
      existing evidence aggregation / NLI / conflict / debate pipeline; Groq
      functionality, conflict types, and the NLI transformer all unchanged.**

## Phase F — New tests
- [x] `tests/test_search_fallbacks.py` (6 tests): Wikipedia 429 → Wikipedia-identity
      fallback, DDG 429 → silent fallback, fallback model name is space-bunny-free,
      no provider-switch wording in results, DDG link decoding unit test.

## Verification results
| Check | Result |
|---|---|
| `python -m pytest -q` | 100/100 passed |
| `./start_mad.sh` on clean ports | backend `/health` 200, frontend 200 |
| `./start_mad.sh` with stale 8000/3000 processes running | stale instances freed, ports rebound cleanly |
| Live LIVE-mode query via API ("What is the capital of France?") | `agreement`, correct answer, 6 OK / 0 failed LLM calls |
| AI Answer Agent with Gemini quota-exhausted | auto-answers via `opencode/muse-spark-1.3-contributor-free` |
| Wikipedia rate-limited | answers via `opencode/mimo-v2.6-flash-free`, shown as "Wikipedia" |
| DuckDuckGo rate-limited | answers via `opencode/space-bunny-free`, shown as "Web Agent (DuckDuckGo)" |

## Remaining known limitation (environment, not code)
- The configured `GEMINI_API_KEY` has **exhausted its quota (429)**. Code handles it
  correctly via the OpenCode fallback, but to have Gemini as primary again, add
  fresh Gemini quota/billing or a new key in `.env` (`GEMINI_API_KEY`).
