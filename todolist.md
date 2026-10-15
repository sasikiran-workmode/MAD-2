# MAD-1 Upgrade: AI Answer Agent -- TODO List

## Phase 1: Dependencies and Configuration
- [x] Add `google-genai` to `requirements.txt`
- [x] Install `google-genai` in venv
- [x] Add Gemini/OpenCode settings to `config.py` (5 new fields)
- [x] Add Gemini/OpenCode block to `.env.example`
- [x] Add Gemini API key and OpenCode settings to `.env`

## Phase 2: Evidence Model
- [x] Add `metadata: Dict[str, Any]` field to `AgentEvidence` in `evidence/models.py`

## Phase 3: New Agent Files (3 files)
- [x] Create `agents/gemini_client.py` -- Gemini API wrapper with Google Search grounding
- [x] Create `agents/opencode_client.py` -- subprocess wrapper for OpenCode CLI
- [x] Create `agents/ai_answer_agent.py` -- Gemini-then-OpenCode orchestrator

## Phase 4: Pipeline Wiring (app.py -- 3 edits)
- [x] Edit A: Add imports (`ThreadPoolExecutor`, `AIAnswerAgent`) and init `self.ai_answer_agent`
- [x] Edit B: Launch AI agent in parallel, collect result, handle exceptions
- [x] Edit C: Fix `_retry_failed_agents` -- preserve evidence for agents not in registry

## Phase 5: API Enrichment (api.py)
- [x] Fix CORS: add `http://127.0.0.1:3000` to allow_origins
- [x] Add response models: `AgentEvidenceOut`, `PairwiseOut`, `DebateArgumentOut`
- [x] Expand `QueryResponse` with all new fields
- [x] Fill response from trace in `solve_query`

## Phase 6: Frontend Redesign (frontend/index.html)
- [x] Light mode: white/light gray background, black text
- [x] Blue buttons (#2563EB), Inter font
- [x] No emojis anywhere
- [x] Raise fetch timeout from 45s to 180s
- [x] Agent Thinking Boxes: rectangular bordered boxes per agent
- [x] NLI Matrix: pairwise scores table
- [x] Decision Banner: state + rationale + failed agents
- [x] Conflict Panel: two claims side by side
- [x] Debate Transcript: rounds with roles
- [x] Judge Verdict: winner, confidence, reason
- [x] Final Answer: answer text + sources list
- [x] Metrics: latency, usable agents, LLM calls

## Phase 7: Start Script
- [x] Create `start_mad.sh` and `chmod +x`

## Phase 8: Tests
- [x] Create `tests/test_ai_answer_agent.py` -- 16/16 passed
- [x] Run `pytest -q` -- 93/94 passed (1 pre-existing Atria API 401 failure)

## Phase 9: Integration Testing
- [ ] Start with `./start_mad.sh`
- [ ] Test normal question in browser (3 agents)
- [ ] Test scholarly question (4 agents)
- [ ] Test Gemini failure (blank key) -- see fallback badge
- [ ] Test both failing (bogus model) -- app still answers with search agents
- [ ] Verify frontend: light mode, blue buttons, black text, no emojis, agent boxes
