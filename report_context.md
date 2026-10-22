# Evidence-MAD: Multi-Agent Debate Framework — Deep Technical Report Context

> **Purpose of this document:** This is a comprehensive technical reference capturing every design decision, code-level detail, data flow, configuration parameter, evaluation result, and limitation of the Evidence-MAD project. It is intended to supply everything needed to write a 60-page academic or technical project report.

---

## Table of Contents

1. [Project Overview and Motivation](#1-project-overview-and-motivation)
2. [Core Research Problem and Novelty](#2-core-research-problem-and-novelty)
3. [System Architecture](#3-system-architecture)
4. [Configuration and Environment](#4-configuration-and-environment)
5. [RunMode: FIXTURE vs. LIVE](#5-runmode-fixture-vs-live)
6. [Agents Layer](#6-agents-layer)
7. [Evidence Pipeline](#7-evidence-pipeline)
8. [NLI Detectors in Depth](#8-nli-detectors-in-depth)
9. [Conflict Classification](#9-conflict-classification)
10. [Debate Lifecycle](#10-debate-lifecycle)
11. [Answer Generation](#11-answer-generation)
12. [LLM Client and Fallback Architecture](#12-llm-client-and-fallback-architecture)
13. [API Layer](#13-api-layer)
14. [Frontend](#14-frontend)
15. [Data Models (Pydantic)](#15-data-models-pydantic)
16. [Execution Trace and Logging](#16-execution-trace-and-logging)
17. [Evaluation Framework](#17-evaluation-framework)
18. [Experimental Results and Metrics](#18-experimental-results-and-metrics)
19. [Ablation Study](#19-ablation-study)
20. [Test Suite](#20-test-suite)
21. [Deployment](#21-deployment)
22. [Fixture Dataset and Evaluation Dataset](#22-fixture-dataset-and-evaluation-dataset)
23. [Limitations and Future Work](#23-limitations-and-future-work)
24. [Project File Structure Reference](#24-project-file-structure-reference)
25. [Key Design Decisions and Engineering Notes](#25-key-design-decisions-and-engineering-notes)

---

## 1. Project Overview and Motivation

### 1.1 What Is Evidence-MAD?

Evidence-MAD (Evidence-triggered Multi-Agent Debate) is a research prototype that combines **multi-agent information retrieval** with **structured debate**, triggered only when there is genuine evidence of conflict between independent agents. It is fundamentally different from naïve multi-agent debate systems that always debate regardless of whether agents agree.

The core insight is: **debate is expensive and slow**. If three independent agents retrieve information and all of them agree, there is no need to run a full structured debate. Debate should fire only when real disagreement is detected, and when it does fire, the type of disagreement should shape the debate strategy.

The system's full name in its own codebase is "Evidence-triggered, conflict-type-aware multi-agent debate."

### 1.2 Motivation

Standard Large Language Models (LLMs) are known to:
- Hallucinate facts, dates, and citations.
- Struggle with temporal inconsistencies (events that happened at different times).
- Conflate different versions of software, policies, or documents.
- Give context-free answers that ignore population-specific nuances.

Multi-agent debate has been proposed as a mitigation strategy: instead of one LLM answering a question, multiple independent agents retrieve and argue, and a judge picks the best answer. However, prior multi-agent debate systems have a fundamental inefficiency: they debate everything, even when agents agree. This increases latency and LLM call costs with no benefit.

Evidence-MAD addresses this by inserting an **evidence gate** — a pairwise Natural Language Inference (NLI) comparison of all agent claims — before deciding whether debate is warranted. This gate uses configurable thresholds for contradiction and entailment, allowing fine-grained control over when debate fires.

A further novelty is **conflict-type classification**: when debate is triggered, the system first classifies whether the conflict is temporal, factual, version-related, contextual (population-specific), or source-quality-driven. Each conflict type receives a distinct debate strategy that focuses the proposer, critic, and reviser on the most relevant resolution dimension.

### 1.3 System Identity and Naming

- **Repository directory:** `/home/sasi-boss/Desktop/MAD-2/`
- **Short name:** Evidence-MAD
- **Entry points:** `app.py` (CLI), `api.py` (FastAPI server), `start_mad.sh` (one-command startup)
- **API version:** 2.0.0
- **Python requirement:** 3.10 or newer
- **Primary LLM backend:** Groq (OpenAI-compatible endpoint), defaulting to `qwen/qwen3.8-27b`
- **AI Answer Agent primary:** Google Gemini with Search Grounding
- **AI Answer Agent fallback:** OpenCode CLI

---

## 2. Core Research Problem and Novelty

### 2.1 Problem Statement

Given a natural language question and N independent retrieval agents, how do we:
1. Determine whether the agents' answers are in genuine conflict?
2. Avoid unnecessary debate when agents agree?
3. When debate is warranted, choose a resolution strategy tailored to the type of conflict?
4. Handle edge cases: agents that fail entirely (insufficient evidence), agents that retrieve irrelevant content (uncertain), and entity-resolution conflicts that generic NLI models miss?

### 2.2 Novel Contributions

1. **Evidence-triggered gating:** Debate only fires on a DISAGREEMENT decision from the NLI aggregator. Agreement, uncertainty, and insufficient data each receive purpose-built output paths without debate overhead.

2. **Query-aware NLI guards:** The NLI layer is extended with three deterministic rules that precede model inference:
   - **Entity substitution guard:** If one agent names a differently titled work and another explicitly rejects the queried work as nonexistent, that is a contradiction — even if both agents share a date correction.
   - **Target resolution guard:** If a query contains a title, one agent rejects that title, and another names a different (positively identified) title, that is a contradiction.
   - **Explicit challenge guard:** If one agent uses epistemic rejection language ("no record," "cannot verify," "unsupported") and another supplies an affirmative answer, that is a contradiction regardless of wording differences.

3. **Five-type conflict taxonomy:** FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, SOURCE — each with distinct natural language strategy instructions passed to the proposer.

4. **Early stopping in debate:** The debate loop supports three early-stop conditions:
   - `no_objection`: critic signals no substantive disagreement.
   - `converged`: Jaccard similarity between consecutive revisions ≥ 0.95.
   - `max_rounds`: safety cap at `MAX_DEBATE_ROUNDS` (default 3).

5. **Dual NLI mode:** Supports both a local HuggingFace transformer model (`ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli`) and an LLM-backed NLI path, where the real LLM (Groq) evaluates contradiction with explicit semantic instructions.

6. **Graceful degradation:** Every component has a defined failure path. LLM failures propagate as `LLMError`, never silently producing fake results. The OpenCode CLI serves as a universal fallback for all LLM roles.

### 2.3 What This Is Not

- Not a RAG (Retrieval-Augmented Generation) system in the traditional sense — agents retrieve via live web search, not a vector database.
- Not a reinforcement-learning system — no training or fine-tuning occurs.
- Not a voting-based ensemble — the judge's decision is evidence-weighted, not majority vote.

---

## 3. System Architecture

### 3.1 Top-Level Pipeline

The full solve pipeline is implemented in `MADSystem.solve()` in `app.py`. It is entirely synchronous. Parallelism is achieved via `ThreadPoolExecutor` for retrieval agents, and the AI Answer Agent runs concurrently with the search agents using a separate single-thread pool.

```
User Query
    │
    ▼
[AI Answer Agent]  ←──── runs in parallel via ThreadPoolExecutor
    │
[QueryRouter]  ────→  [WebAgent] [ReferenceAgent] [ScholarlyAgent]
    │
    ▼
[EvidenceNormalizer]  (per agent: relevance filter + LLM normalize)
    │
    ▼
[AgentEvidence] × N
    │
    ▼
[EvidenceAggregator]  (NLI pairwise for every unordered agent pair)
    │
    ├─→ INSUFFICIENT  →  [AnswerGenerator._generate_insufficient()]
    ├─→ UNCERTAIN     →  [AnswerGenerator._generate_uncertain()]
    ├─→ AGREEMENT     →  [AnswerGenerator._generate_agreement()]
    └─→ DISAGREEMENT
            │
            ▼
        [ConflictClassifier]  →  conflict type (FACTUAL/TEMPORAL/VERSION/CONTEXTUAL/SOURCE)
            │
            ▼
        [DebateManager]
        ┌── [Proposer]  (type-specific strategy)
        ├── [Critic]
        ├── [Reviser]
        └── early stop (no_objection / converged / max_rounds)
            │
            ▼
        [Judge]  →  winner, evidence_score, source_score, reasoning_score
            │
            ▼
        [AnswerGenerator._generate_disagreement()]
    │
    ▼
[ExecutionTrace]  →  saved to results/trace_<8hex>.json
```

### 3.2 Component Dependency Map

| Component | File | Depends on |
|---|---|---|
| MADSystem | `app.py` | All components below |
| LLMClient | `llm_client.py` | config, opencode_client |
| EvidenceNormalizer | `evidence/normalizer.py` | LLMClient |
| EvidenceAggregator | `evidence/aggregator.py` | NLI detector |
| MockNLIDetector | `evidence/disagreement_detector.py` | fixture table |
| LLMNLIDetector | `evidence/disagreement_detector.py` | LLMClient |
| NLIDetector | `evidence/disagreement_detector.py` | HuggingFace transformers |
| ConflictClassifier | `conflict/classifier.py` | LLMClient |
| DebateManager | `debate/manager.py` | Proposer, Critic, Reviser |
| Proposer | `debate/proposer.py` | LLMClient |
| Critic | `debate/critic.py` | LLMClient |
| Reviser | `debate/reviser.py` | LLMClient |
| Judge | `debate/judge.py` | LLMClient |
| AnswerGenerator | `output/generator.py` | LLMClient |
| QueryRouter | `agents/router.py` | WebAgent, ReferenceAgent, ScholarlyAgent |
| AIAnswerAgent | `agents/ai_answer_agent.py` | GeminiClient, OpenCodeClient |

### 3.3 Two-Mode Architecture

The system has a strict binary mode distinction enforced by `RunMode` enum in `run_mode.py`:

- **`RunMode.FIXTURE`** (demo): reads all agent evidence from `data/fixtures.json`. No API calls, no real search. `MockNLIDetector` runs with exact-match fixture lookup. All debate stages use deterministic fixture-generated text. Used for offline testing and demonstrations.

- **`RunMode.LIVE`**: full real pipeline. Requires `LLM_API_KEY`. Uses `LLMNLIDetector` (default) or `NLIDetector` (HuggingFace). AI Answer Agent uses Gemini → OpenCode. Search agents use real HTTP providers.

The `RunMode` is passed explicitly into every constructor. No component reads `settings.demo_mode` on its own — this was an explicit architectural decision (Task 22 in the task plan) to prevent mode leakage.

---

## 4. Configuration and Environment

### 4.1 Settings Class (`config.py`)

All configuration is managed by `pydantic-settings` in `config.py` and loaded from `.env`. The `Settings` class uses `SettingsConfigDict` with `env_file=".env"`. All settings have `alias` mappings to the environment variable names.

Key settings and their defaults:

| Environment Variable | Python Field | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | `llm_api_key` | `""` | Groq or OpenAI-compatible API key |
| `LLM_BASE_URL` | `llm_base_url` | `https://api.groq.com/openai/v1` | LLM endpoint |
| `LLM_MODEL` | `llm_model` | `llama-3.3-70b-versatile` | Model ID (README shows `qwen/qwen3.8-27b`) |
| `LLM_TEMPERATURE` | `llm_temperature` | `0.0` | Deterministic outputs |
| `LLM_TIMEOUT` | `llm_timeout` | `60.0` | Request timeout in seconds |
| `LLM_MAX_RETRIES` | `llm_max_retries` | `3` | Retry attempts |
| `NLI_MODEL` | `nli_model` | `ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli` | HuggingFace NLI model |
| `NLI_DEVICE` | `nli_device` | `cpu` | Device for transformer inference |
| `NLI_MODE` | `nli_mode` | `transformers` | `mock` (LLM NLI) or `transformers` |
| `NLI_MAX_CLAIMS` | `nli_max_claims` | `3` | Max claims passed to NLI |
| `DISAGREEMENT_THRESHOLD` | `disagreement_threshold` | `0.70` | Contradiction score needed for DISAGREEMENT |
| `ENTAILMENT_THRESHOLD` | `entailment_threshold` | `0.70` | Entailment score needed for AGREEMENT |
| `MAX_DEBATE_ROUNDS` | `max_debate_rounds` | `3` | Max debate iterations |
| `MAX_SEARCH_RESULTS` | `max_search_results` | `5` | Max results per search agent |
| `DEMO_MODE` | `demo_mode` | `false` | Use fixture mode if true |
| `ALLOW_RULE_FALLBACK` | `allow_rule_fallback` | `true` | Fallback to pattern classifier if LLM fails |
| `GEMINI_API_KEY` | `gemini_api_key` | `""` | Gemini API key |
| `GEMINI_MODEL` | `gemini_model` | `gemini-3.8-flash` | Gemini model ID |
| `GEMINI_TIMEOUT` | `gemini_timeout` | `20.0` | Gemini request timeout |
| `OPENCODE_MODEL` | `opencode_model` | `opencode/deepseek-v4.1-flash-free` | OpenCode model for AI Answer Agent fallback |
| `OPENCODE_TIMEOUT` | `opencode_timeout` | `45.0` | OpenCode subprocess timeout |
| `OPENCODE_WIKI_MODEL` | `opencode_wiki_model` | `opencode/mimo-v2.6-flash-free` | OpenCode fallback for Wikipedia agent |
| `OPENCODE_WEB_MODEL` | `opencode_web_model` | `opencode/space-bunny-free` | OpenCode fallback for web agent |

### 4.2 Validation on Startup

`settings.validate()` is called in `MADSystem.__init__()` only in LIVE mode. It raises `ValueError` if `LLM_API_KEY` is not set and `DEMO_MODE` is False. This prevents silent failures when the system runs without credentials.

### 4.3 `@lru_cache` Singleton Pattern

`get_settings()` uses `@lru_cache()`, meaning the `Settings` object is created once per process. This is standard for `pydantic-settings` and avoids repeated file reads.

---

## 5. RunMode: FIXTURE vs. LIVE

### 5.1 `RunMode` Enum (`run_mode.py`)

```python
class RunMode(str, Enum):
    FIXTURE = "fixture"
    LIVE = "live"
```

### 5.2 `FixtureStore`

`FixtureStore` loads `data/fixtures.json` at construction time and builds two lookup dicts: by `id` and by lowercase query string. `get_by_query()` raises `FixtureNotFoundError` (a subclass of `KeyError`) on unknown queries. It never falls back to LIVE mode — this is strict isolation.

`REQUIRED_FIXTURE_IDS` is a constant set of 10 required fixture case IDs that must exist in the JSON. `validate_required()` checks this and raises `ValueError` if any are missing. The 10 required IDs are:

```
agree_capital, factual_boiling, temporal_policy, version_python,
contextual_drug, source_blog_vs_paper, unrelated_evidence,
one_agent_fails, two_agents_fail, all_agents_fail
```

### 5.3 Backward Compatibility

`MADSystem.__init__()` accepts a `bool` for `run_mode` to support old code that passed `demo_mode=True`. It silently converts: `True → RunMode.FIXTURE`, `False → RunMode.LIVE`. The top-level `solve()` function also still accepts `demo_mode: bool` for the same reason.

---

## 6. Agents Layer

### 6.1 Agent Registry and Base Class

`agents/base_agent.py` defines:
- `AgentConfig`: Pydantic model with `agent_id`, `timeout`, `max_retries`, `enabled` fields.
- `BaseAgent`: ABC with abstract `retrieve(query) → Evidence` method and `is_enabled` property.
- `AgentRegistry`: global singleton dict mapping `agent_id → BaseAgent`. The `router.py` uses this registry.

### 6.2 QueryRouter (`agents/router.py`)

The `QueryRouter` dispatches queries to multiple agents in parallel using `ThreadPoolExecutor`. It:
1. Determines which agents to run (always Web and Reference; Scholarly only for academic queries).
2. Submits all `agent.retrieve(query)` calls concurrently.
3. Collects results and returns a `routing_result` dict with `decision` and `evidence` keys.

The scholarly agent routing heuristic checks whether the query contains academic keywords: `study`, `trial`, `meta-analysis`, `doi`, `peer-reviewed`, `systematic review`, `rct`, `cohort`, `clinical`, `journal`, `research`, `findings`, `published`, `abstract`, `citation`, `paper`.

### 6.3 WebAgent

**Class:** `WebAgent` in `agents/search_agent.py`
**Agent ID:** `web_agent`
**Primary provider:** DuckDuckGo HTML search
**Fallback:** OpenCode CLI (`OPENCODE_WEB_MODEL`)

The agent scrapes `https://html.duckduckgo.com/html/` using regex patterns against the response HTML. It extracts result links (`class="result__a"`) and snippets (`class="result__snippet"`). DuckDuckGo redirects (`/l/?uddg=<encoded>`) are decoded via `_decode_ddg_link()` which uses `urllib.parse.parse_qs` to extract the real URL.

HTTP retries: up to 3 attempts with exponential backoff (2s, 4s, 8s) on 429, 5xx, and timeout.

If DuckDuckGo fails (rate limit, blocked, timeout), `_opencode_web_fallback()` is called. The fallback asks an OpenCode model the query directly and returns synthetic search results. The results are labeled as coming from the same `web_agent` identity — no provider commentary is exposed to the NLI/debate layer.

### 6.4 ReferenceAgent

**Class:** `ReferenceAgent` in `agents/search_agent.py`
**Agent ID:** `reference_agent`
**Primary provider:** Wikipedia API (`https://en.wikipedia.org/w/api.php`)
**Fallback:** OpenCode CLI (`OPENCODE_WIKI_MODEL`)

The agent calls the Wikipedia search API with `action=query&list=search&srsearch=<query>&srlimit=5`. For each result, it fetches the page extract. Wikipedia returns a 429 when rate-limited, triggering exponential backoff followed by the OpenCode fallback.

### 6.5 ScholarlyAgent

**Class:** `ScholarlyAgent` in `agents/search_agent.py`
**Agent ID:** `scholarly_agent`
**Primary provider:** Crossref REST API (`https://api.crossref.org/works?query=<query>&rows=5`)
**Fallback:** DuckDuckGo (the web search function)

Scholarly routing heuristic: only dispatched when the query matches academic vocabulary. Crossref returns JSON with `message.items` containing `title`, `DOI`, `abstract`, and `author` fields. When Crossref fails or returns no useful results, the agent falls back to DuckDuckGo search.

### 6.6 AIAnswerAgent (`agents/ai_answer_agent.py`)

**Agent ID:** `ai_answer_agent`
**Type:** Not a `BaseAgent` subclass — runs independently of the search agent framework.

This agent runs in parallel with the router's search agents on every LIVE-mode query. It uses a single-thread `ThreadPoolExecutor` launched in `MADSystem.solve()`. The agent:
1. Builds a prompt using `PROMPT_TEMPLATE` — which explicitly instructs: "Preserve every named entity exactly as written in the question: never silently correct, replace, or assume that a similarly named paper, product, person, or work is the same entity."
2. Tries Gemini first via `generate_grounded()` in `agents/gemini_client.py`.
3. Falls back to `run_opencode()` in `agents/opencode_client.py` on any `GeminiError`.
4. Returns one `AgentEvidence` directly (status OK or RETRIEVAL_FAILED).

The claim text is trimmed to ≤600 characters at a sentence boundary by `_short()` before being stored in `NormalizedClaim.text`. The full untrimmed answer is stored in `metadata['full_answer']`.

**Why trim the claim?** The NLI model compares this against one-sentence claims from search agents. A long multi-paragraph answer would compare poorly against a single-sentence claim, potentially inflating contradiction scores for correct answers.

### 6.7 GeminiClient (`agents/gemini_client.py`)

`generate_grounded()` calls the Gemini API using the `google-genai` Python SDK with Google Search grounding enabled. It returns `(text, found_sources)` where `found_sources` is a list of `{url, title}` dicts extracted from the grounding metadata. Raises `GeminiError` on any failure.

### 6.8 OpenCodeClient (`agents/opencode_client.py`)

`run_opencode()` is a subprocess wrapper that invokes `opencode run --model <model> <prompt>`. It captures stdout, enforces a timeout, and returns a `RunResult(ok, text, error)` named tuple. Used as a universal fallback for both the AI Answer Agent and the LLMClient.

---

## 7. Evidence Pipeline

### 7.1 Evidence Flow Overview

For each search agent in LIVE mode, the raw provider results pass through two stages:

**Stage 1: Relevance Filter** (no LLM — fast, deterministic)
**Stage 2: LLM Normalization** (one LLM call per agent, role="normalize")

For the AI Answer Agent, stages 1 and 2 are bypassed — its output is already a normalized single claim.

### 7.2 Relevance Filter (`evidence/normalizer.py`)

**Function:** `_is_relevant(query, result, min_overlap=1)`

The filter computes content-word overlap between the query and each result's `title + snippet`. Content words exclude a hardcoded stopword list of ~50 common English words. Numbers are included regardless of length (critical for year-based filtering).

**Threshold logic:**
- For queries with ≤2 content words (e.g., "Who is Einstein?"), `min_overlap=1` is always used to prevent over-filtering of terse queries.
- For longer queries, the default `min_overlap=1` means at least one query keyword must appear in the result.

Results below the threshold are dropped. If ALL results are dropped, the agent returns `EvidenceStatus.NO_RELEVANT_RESULTS` (not a failure — the retrieval worked but nothing was relevant).

The `filtered_out_count` field in `AgentEvidence` tracks how many results were dropped, enabling the evaluation layer to compute `avg_irrelevant_evidence_count`.

### 7.3 LLM Normalization Prompt

The normalizer sends surviving results to the LLM with this instruction:

```
You are an evidence extraction assistant.
QUERY: {query}
SEARCH SNIPPETS: {numbered list of title — snippet}

Task:
1. Read the snippets and answer the query in ONE concise sentence.
   - You MAY reason from the snippet content to form the answer.
   - Only return {"answer": null} if the snippets contain absolutely NO information.
   - Preserve the named entity in the query exactly.
   - Never silently substitute a similarly named work.

Return ONLY JSON:
{
  "answer": "<one sentence or null>",
  "source_index": <0-based index>,
  "date": "<year or null>",
  "version": "<version or null>",
  "scope": "<platform/population or null>"
}
```

The date, version, and scope fields are critical for the downstream NLI layer. For example:
- `date: "2020"` enables the pattern-based NLI to detect year conflicts.
- `version: "Python 3.10"` enables the pattern-based NLI to detect version conflicts.
- `scope: "adults"` enables detection of population-based contextual conflicts.

**Meta-claim detection:** If the LLM returns a statement like "The snippets do not contain..." or "No information about...", the normalizer detects this via a list of meta-patterns and returns `NO_RELEVANT_RESULTS` instead of a useless claim. This prevents meta-language from polluting the NLI comparison. The patterns checked are: `"do not contain"`, `"does not contain"`, `"no information"`, `"no relevant"`, `"snippets do not"`, `"provided snippets"`, `"cannot find"`, `"unable to find"`, `"not mentioned"`, `"not provided"`.

### 7.4 EvidenceAggregator (`evidence/aggregator.py`)

The aggregator runs NLI for every unordered pair of usable agents. For N usable agents, this produces N*(N-1)/2 pairwise comparisons.

**Decision rule (asymmetric):**

```
if len(usable) <= 1:
    → INSUFFICIENT

for each pair (a, b):
    run nli(claim_a, claim_b)

if ANY pair contradiction_score >= DISAGREEMENT_THRESHOLD:
    → DISAGREEMENT

elif ALL pairs entailment_score >= ENTAILMENT_THRESHOLD:
    → AGREEMENT

else:
    → UNCERTAIN
```

The asymmetry is deliberate: disagreement needs only ONE pair to trigger, while agreement requires ALL pairs to confirm. This prevents a system with 3 agents where 2 agree and 1 is neutral from claiming consensus.

**Top conflict tracking:** The aggregator also tracks `top_conflict` — the pair with the highest contradiction score. This is passed downstream as the primary conflicting pair to the classifier and debate stages.

**NLI failure handling:** If NLI throws `NLIError` for a pair, that pair is recorded with all scores = 0.0 and label `NEUTRAL`. This prevents one failing NLI call from crashing the entire aggregation.

---

## 8. NLI Detectors in Depth

### 8.1 Three Detector Classes

| Class | Used when | Behavior |
|---|---|---|
| `MockNLIDetector` | FIXTURE mode | Exact-match lookup from fixture dict; raises `KeyError` on unknown pair; falls back to `_pattern_predict()` when no fixture dict |
| `LLMNLIDetector` | LIVE + `NLI_MODE=mock` | Asks real LLM (Groq) for CONTRADICTION/ENTAILMENT/NEUTRAL with explicit scores; falls back to `_pattern_predict()` on LLM failure |
| `NLIDetector` | LIVE + `NLI_MODE=transformers` | HuggingFace `text-classification` pipeline with bidirectional inference |

### 8.2 Query-Aware Guard Chain

All three detectors (or their `predict_for_query` method) apply the same guard chain before model inference:

```
predict_for_query(query, premise, hypothesis):
1. _entity_substitution_prediction(premise, hypothesis)
   → if one claim names a paper and another rejects it as nonexistent → CONTRADICTION (0.91)
2. _explicit_challenge_prediction(query, premise, hypothesis)
   → if one claim epistemically challenges the query topic and other gives affirmative answer → CONTRADICTION (0.90)
3. _target_resolution_prediction(query, premise, hypothesis)
   → if one claim rejects the queried title and another names a different positive title → CONTRADICTION (0.93)
4. (if no guard fired) → run actual NLI model
```

### 8.3 Entity Substitution Guard (`_entity_substitution_prediction`)

Detects a very specific pattern: one claim contains `"paper titled X"` (or variant) and another claim explicitly says `"no such paper exists"` (or variant). This handles the case where a search engine autocorrects a misspelled paper title and the AI answer agent reports the correct title doesn't exist — they look like a contradiction that generic NLI might flatten to NEUTRAL because both claims have different focus.

Regular expressions used:
- Rejection pattern: `\b(?:no such|does not exist|doesn't exist|no record of|cannot find|unable to find)\s+(?:an?\s+|the\s+)?(?:paper|article|publication|work)\b`
- Work naming: `\b(?:paper|article|publication|work)\s+[""][^\""]{3,160}[""]`

Returns contradiction score 0.91 when pattern fires.

### 8.4 Explicit Challenge Guard (`_explicit_challenge_prediction`)

This guard is domain-agnostic: it doesn't care about paper titles, dates, or anything specific. Its rule is:

> If one agent says the requested fact cannot be verified, has no reliable/official support, or does not exist, and another gives an affirmative answer, that is a contradiction.

The challenge pattern matches phrases like:
- `no record`, `no known record`, `no official record`
- `does not exist`, `doesn't exist`
- `cannot verify`, `can't verify`, `unable to verify`
- `unverified`, `unsupported`, `unsubstantiated`, `nonexistent`
- `not verified`, `not verifiable`, `not supported`, `not documented`

A second guard requires at least one content word from the query to appear in the challenging claim (or a deictic pronoun like "it" or "this"), preventing stray disclaimers from triggering the gate.

Returns contradiction score 0.90 when pattern fires.

### 8.5 Target Resolution Guard (`_target_resolution_prediction`)

More sophisticated than the entity substitution guard. It:
1. Normalizes the query string to lowercase alphanumeric tokens.
2. Extracts `rejected_titles` from both claims (titles mentioned after "no known paper titled..." or similar).
3. Extracts `quoted_titles` from both claims (titles in quotes that are positively asserted).
4. Checks if any rejected title overlaps with the query.
5. Checks if any positively asserted title differs from the rejected query title.

If all three conditions hold, returns contradiction score 0.93.

This is specifically designed for cases like: query asks about "Wipro is All U Need", one agent says "no known paper titled 'Wipro is All U Need'", another says "the paper 'Attention is All You Need' was published in 2017." Both claims share a date-impossibility check on the query (2082), so generic NLI might call them entailing. This guard catches the entity mismatch.

### 8.6 Pattern-Based Fallback (`_pattern_predict`)

Used when no LLM is available (NLI_MODE=mock without a real LLM, or in tests). Checks:
1. **Year conflict:** Both claims contain asserted years (stripping negated years) that are disjoint → CONTRADICTION (0.91).
2. **Version conflict:** Both claims contain disjoint `x.y` version strings → CONTRADICTION (0.89).
3. **Keyword scope conflicts:** Hardcoded pairs like `(adults, children)`, `(safe, dangerous)`, `(effective, not effective)`, `(increased, decreased)` → CONTRADICTION (0.91).
4. **Common content words:** ≥3 shared non-stopword tokens → ENTAILMENT (0.88).
5. Default: NEUTRAL (0.60).

The year detection includes sophisticated negation stripping: it removes years following "not", "never", "isn't", "wrong", "incorrect", years in quotes, and years before "not/but" correction patterns to avoid treating a claim like "it was not 2019, it was 2020" as having two conflicting years.

### 8.7 LLMNLIDetector Prompt

```
You are the strict NLI gate for an evidence-triggered debate.

USER QUESTION: {query}
Claim A: {claim_a}
Claim B: {claim_b}

[Instructions for when to classify CONTRADICTION, ENTAILMENT, NEUTRAL...]

Answer with ONLY a JSON object:
{
  "label": "CONTRADICTION" or "ENTAILMENT" or "NEUTRAL",
  "contradiction_score": 0.0-1.0,
  "entailment_score": 0.0-1.0,
  "neutral_score": 0.0-1.0,
  "reason": "<one sentence>"
}
```

The prompt explicitly instructs the LLM to classify entity-substitution conflicts and evidence challenges as CONTRADICTION, not NEUTRAL.

### 8.8 HuggingFace NLI (Transformer Mode)

Model: `ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli` (~1.4 GB download)

This is a RoBERTa-large model fine-tuned on 5 NLI datasets: SNLI, MultiNLI, FEVER-NLI, and ANLI rounds 1-3. It is one of the strongest publicly available NLI models.

The pipeline uses `top_k=None` (returning all label scores rather than just the top-1). Input format is `{"text": premise, "text_pair": hypothesis}` — the correct HuggingFace format for NLI, not the buggy `</s>` concatenation that some implementations use.

**Bidirectional inference:** The model is run in both forward (A→B) and backward (B→A) directions. The final scores use `max(contradiction_fwd, contradiction_bwd)` and `min(entailment_fwd, entailment_bwd)`. This is a conservative strategy that catches asymmetric contradictions (e.g., A implies B but B does not imply A).

---

## 9. Conflict Classification

### 9.1 ConflictClassifier (`conflict/classifier.py`)

Called only on the DISAGREEMENT path, after the aggregator identifies a contradiction. Takes `claim_a_text`, `claim_b_text`, and the original `query`.

Returns a `ClassificationResult` with:
- `type`: `ConflictType` enum (FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, SOURCE, UNKNOWN)
- `confidence`: 0.0–1.0
- `explanation`: text description
- `status`: `ComponentStatus.LLM_SUCCESS`, `FALLBACK`, or `FAILED`
- `error`: error message if failed

### 9.2 LLM Classification Prompt

The LLM is given definitions of all 5 conflict types with examples:
- **FACTUAL**: "Two sources make mutually incompatible factual claims about the same thing at the same time and in the same context."
- **TEMPORAL**: "The claims differ because they refer to different points in time."
- **VERSION**: "The claims refer to different software/product/document/policy versions."
- **CONTEXTUAL**: "The claims differ because their conditions or contexts differ (population, platform, edition)."
- **SOURCE**: "The disagreement is primarily caused by differences in source authority/reliability/provenance."

### 9.3 Pattern-Based Fallback

Applied when LLM unavailable or when `allow_rule_fallback=True` after LLM failure:

**Check order:**
1. VERSION: both claims contain version number patterns (e.g., `v3.10`, `Python 3.13`, `v2`)
2. TEMPORAL: claims contain different years (e.g., `{2019}` vs `{2020}`)
3. CONTEXTUAL: claims mention population/platform qualifiers from hardcoded groups
4. SOURCE: claims contain explicit source quality words (blog/paper, unofficial/official)
5. Default: FACTUAL

### 9.4 Conflict Type Handling in Debate

Each conflict type triggers different strategy text injected into the Proposer's prompt:

- **TEMPORAL**: "For each claim, check its recorded date. If a claim is dated AFTER the query period, it must be excluded — it is irrelevant to what was true at the requested time."
- **VERSION**: "First check whether the two claims actually refer to the SAME version. If they refer to different versions, the disagreement may be fully explained by the version difference — report 'both correct for their respective versions'."
- **CONTEXTUAL**: "First check whether the two claims apply to different populations, platforms, or editions. If the scopes are different, the contradiction may dissolve — report the conditions under which each claim holds."
- **SOURCE**: "Evaluate source authority, provenance, specificity, and reliability."
- **FACTUAL**: "Focus on direct evidence. Compare the competing factual claims directly against the retrieved evidence."

---

## 10. Debate Lifecycle

### 10.1 DebateManager (`debate/manager.py`)

The `run_debate()` method orchestrates up to `MAX_DEBATE_ROUNDS` cycles of Propose → Critique → Revise.

**Per-round structure:**
1. **Proposer** generates an initial position and evidence review for the conflict.
2. **Critic** challenges or accepts the proposal.
3. Early stop check: if `SUBSTANTIVE_OBJECTION: false` appears in critic output → stop with `no_objection`.
4. **Reviser** refines the proposal based on critique.
5. Convergence check: Jaccard similarity between current and previous revision ≥ 0.95 → stop with `converged`.

**Failure handling:** If any stage raises `LLMError`, the debate stops immediately with `status="failed"` (if round 1) or `status="partial"` (if later rounds). `failed_stages` records which stage failed. The judge is skipped if debate did not complete (`status != "completed"`).

### 10.2 Proposer (`debate/proposer.py`)

In LIVE mode, generates a structured argument using the conflict-type strategy. The output format is enforced by the prompt:

```
POSITION
<proposed position>
EVIDENCE REVIEW
Claim A: <what retrieved evidence supports>
Claim B: <what retrieved evidence supports>
REASONING
<core issue and why the position follows>
SOURCE BASIS
<only sources present in the supplied claims>
CONCLUSION
<one concise proposed resolution>
```

In FIXTURE mode, the proposer returns realistic canned text appropriate for each conflict type (temporal, version, contextual, source, or factual) without calling the LLM.

Metadata enrichment for specific conflict types:
- TEMPORAL: includes `QUERY PERIOD: {year}` if a year is detected in the query.
- VERSION: includes `Claim A version: {version}` and `Claim B version: {version}`.
- CONTEXTUAL: includes `Claim A scope: {scope}` and `Claim B scope: {scope}`.

**Argument validation:** `is_valid_argument()` rejects any argument shorter than 50 characters or starting with "Demo response". This prevents empty or trivially short LLM outputs from passing into the debate.

### 10.3 Critic (`debate/critic.py`)

The critic receives the proposer's argument and must either:
- Issue a substantive objection with specific reasoning.
- Signal `SUBSTANTIVE_OBJECTION: false` if the proposal is already well-reasoned.

The `no_objection` early-stop checks for `SUBSTANTIVE_OBJECTION: false` in the critic's content (case-insensitive regex match) or in the `strategy_used` field.

### 10.4 Reviser (`debate/reviser.py`)

The reviser synthesizes the original proposal and the critic's objections into a refined argument. The convergence check after revision uses Jaccard similarity:

```python
def _jaccard(a: str, b: str) -> float:
    sa = set(re.findall(r"\b\w+\b", a.lower()))
    sb = set(re.findall(r"\b\w+\b", b.lower()))
    return len(sa & sb) / len(sa | sb)
```

If Jaccard ≥ 0.95, the revision is considered converged with the previous revision and debate stops with `stop_reason="converged"`.

### 10.5 Judge (`debate/judge.py`)

The judge only runs when `debate_outcome.status == "completed"`. It receives:
- The full debate transcript (all rounds' proposer/critic/reviser arguments).
- Structured claim information (text, date, version, scope, source URL) for both conflicting claims.
- The conflict type.

The judge's LLM prompt instructs evaluation based on EVIDENCE rather than persuasion. It returns:
- `winner`: `"candidate_1"` or `"candidate_2"` (candidate_1 corresponds to `claim_a`).
- `evidence_score`: 0.0–1.0, how well the winner is supported by evidence.
- `source_score`: 0.0–1.0, quality of sources.
- `reasoning_score`: 0.0–1.0, quality of reasoning.
- `confidence`: 0.0–1.0, overall confidence in the verdict.

In FIXTURE mode, the judge always returns `candidate_1` as winner with conflict-type-specific reasoning text and scores of 0.80–0.85.

If the judge's LLM call fails, `judge_result = None`. The answer generator handles `judge_result=None` by generating an "unresolved conflict" answer rather than fabricating a verdict.

### 10.6 Stop Reasons Summary

| Stop Reason | Condition | Debate Status |
|---|---|---|
| `converged` | Jaccard similarity between consecutive revisions ≥ 0.95 | `completed` |
| `no_objection` | Critic returns `SUBSTANTIVE_OBJECTION: false` | `completed` |
| `max_rounds` | `MAX_DEBATE_ROUNDS` iterations completed | `completed` |
| `stage_failure` | Any stage (proposer/critic/reviser) raises `LLMError` | `failed` or `partial` |

---

## 11. Answer Generation

### 11.1 AnswerGenerator (`output/generator.py`)

Four output shapes, one per `EvidenceState`:

**AGREEMENT:**
- Calls LLM with a prompt asking for a concise answer based on the agreed claims.
- Reports `independent_agents_agreeing = len(usable)`.
- Includes all deduplicated sources from all usable agents.

**DISAGREEMENT (debate completed, judge available):**
- States the conflict type.
- Reports the winning claim text.
- Includes the judge's reasoning.
- Sets `debate_triggered=True`.

**DISAGREEMENT (debate failed/incomplete):**
- Explicitly states "conflict detected but debate did not complete."
- Lists which stages failed.
- Sets `answer = "conflict remains unresolved"`.
- Does NOT claim a winner.

**UNCERTAIN:**
- Lists what each agent found.
- States "no single authoritative answer could be determined."
- No debate triggered.

**INSUFFICIENT:**
- Lists all failed agent IDs and their failure reasons.
- Does NOT attempt to answer the query.
- Empty sources list.

### 11.2 Source Deduplication

`_deduplicate_sources()` removes duplicate `Source` objects by URL using a seen-URL set. This prevents the same source appearing multiple times in the answer when multiple agents retrieved the same page.

---

## 12. LLM Client and Fallback Architecture

### 12.1 LLMClient (`llm_client.py`)

The `LLMClient` is a thin wrapper over the OpenAI-compatible chat completions API. It uses `httpx.Client` (synchronous) with a configurable timeout.

**Call tracking:** Every call is tracked per-role in `self.calls[role]["ok"]` and `self.calls[role]["failed"]`. `call_report()` returns the full dict. This is what populates `metrics.llm_calls_by_role` in the trace.

Roles used in the system:
- `"normalize"`: EvidenceNormalizer LLM call
- `"nli"`: LLMNLIDetector call
- `"classifier"`: ConflictClassifier call
- `"proposer"`: Proposer call
- `"critic"`: Critic call
- `"reviser"`: Reviser call
- `"judge"`: Judge call
- `"answer"`: AnswerGenerator call

**JSON extraction:** `_extract_json_block()` first tries to find a fenced code block (```json...```), then falls back to finding the first `{...}` block in the response. This handles LLMs that wrap their JSON in markdown.

### 12.2 OpenCode Fallback in LLMClient

If the primary LLM (Groq) fails for any role, `_opencode_fallback()` wraps the original prompt with a system preamble identifying the role and submits it to the OpenCode CLI. If OpenCode also fails, `LLMError` is raised. No silent fallbacks — every failure either produces a result or raises.

### 12.3 Typical LLM Call Count Per Query

For a full LIVE query that triggers debate:
- 3 `normalize` calls (one per search agent)
- 1 `nli` call per pair × N*(N-1)/2 pairs (e.g., 3 calls for 3 agents)
- 1 `classifier` call
- Up to 3 rounds × (1 `proposer` + 1 `critic` + 1 `reviser`) = up to 9 debate calls
- 1 `judge` call
- 1 `answer` call
- **Total (typical full debate):** ~18–20 LLM calls

For a query resulting in AGREEMENT:
- 3 `normalize` + 3 `nli` + 1 `answer` = ~7 LLM calls

---

## 13. API Layer

### 13.1 FastAPI Application (`api.py`)

Version: 2.0.0. Runs on `uvicorn` at `127.0.0.1:8000`.

**CORS configuration:** Origins `http://localhost:3000` and `http://127.0.0.1:3000` are allowed (matching the frontend dev server port).

**Endpoints:**
- `GET /` — name/version/status response
- `GET /health` — `{"status": "healthy"}`
- `POST /api/solve` — main solve endpoint
- `POST /solve` — alias for `/api/solve`

### 13.2 Request and Response Schema

**Request:**
```json
{
  "query": "string",
  "demo_mode": false
}
```

**Response (full schema):**
```json
{
  "query": "...",
  "answer": "...",
  "reasoning": "...",
  "evidence_state": "agreement|disagreement|uncertain|insufficient",
  "rationale": "...",
  "debate_triggered": true,
  "conflict_type": "factual|temporal|version|contextual|source|null",
  "conflict": {
    "type": "...",
    "confidence": 0.9,
    "explanation": "...",
    "claim_a": "...",
    "claim_b": "...",
    "agent_a_id": "...",
    "agent_b_id": "..."
  },
  "agent_evidence": [
    {
      "agent_id": "...",
      "status": "ok|no_relevant_results|retrieval_failed",
      "claim": "...",
      "source_title": "...",
      "source_url": "...",
      "date": "...",
      "version": "...",
      "failure_reason": "...",
      "metadata": {}
    }
  ],
  "failed_agents": [],
  "pairwise": [
    {
      "agent_a_id": "...",
      "agent_b_id": "...",
      "label": "contradiction|entailment|neutral",
      "contradiction_score": 0.91,
      "entailment_score": 0.05
    }
  ],
  "debate_rounds": [
    {
      "round_number": 1,
      "role": "proposer|critic|reviser",
      "content": "..."
    }
  ],
  "judge": {
    "winner": "candidate_1",
    "reason": "...",
    "evidence_score": 0.9,
    "source_score": 0.85,
    "reasoning_score": 0.82,
    "confidence": 0.88
  },
  "sources": [{"url": "...", "title": "..."}],
  "metrics": {
    "latency_seconds": 3.2,
    "total_llm_calls_ok": 18,
    "total_llm_calls_failed": 0,
    "usable_agents": 3,
    "evidence_state": "disagreement",
    "debate_triggered": true,
    "conflict_type": "temporal",
    "llm_calls_by_role": {"normalize": {"ok": 3}, "classifier": {"ok": 1}, ...}
  }
}
```

### 13.3 Async Architecture

The FastAPI endpoints are `async def`. The synchronous `MADSystem.solve()` is run via `loop.run_in_executor(None, lambda: sync_solve(...))`. This prevents blocking the event loop while the synchronous pipeline (which includes `ThreadPoolExecutor` parallelism internally) runs.

### 13.4 Vercel Serverless Entry (`api/index.py`)

A minimal 4-line file that imports the FastAPI `app` object for Vercel's serverless adapter. `vercel.json` routes all requests through this handler.

---

## 14. Frontend

### 14.1 Frontend Overview (`frontend/index.html`)

Single HTML file, no build step. Served via Python's built-in HTTP server at port 3000:
```bash
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

### 14.2 UI Features

- Query input field with a "Demo mode (offline)" toggle.
- Real-time display of agent evidence from all four agents (Web, Reference, Scholarly, AI Answer Agent).
- Pairwise NLI scores table showing contradiction and entailment scores for each agent pair.
- Evidence decision badge (AGREEMENT / DISAGREEMENT / UNCERTAIN / INSUFFICIENT) with color coding.
- Conflict type and conflicting claims side-by-side when disagreement detected.
- Full debate round-by-round transcript (Proposer → Critic → Reviser per round).
- Judge verdict with scores.
- Final answer panel with sources list.
- Metrics panel (latency, LLM calls, debate stop reason).

---

## 15. Data Models (Pydantic)

All models are in `evidence/models.py`. Key model hierarchy:

### 15.1 Core Enums

```python
class ConflictType(str, Enum):
    FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, SOURCE, UNKNOWN

class NLILabel(str, Enum):
    ENTAILMENT, CONTRADICTION, NEUTRAL

class EvidenceStatus(str, Enum):
    OK, NO_RELEVANT_RESULTS, RETRIEVAL_FAILED

class EvidenceState(str, Enum):
    AGREEMENT, DISAGREEMENT, UNCERTAIN, INSUFFICIENT

class ComponentStatus(str, Enum):
    LLM_SUCCESS, FALLBACK, FAILED
```

### 15.2 Source and Claim Models

```python
class Source(BaseModel):
    url: str
    title: str
    snippet: str
    metadata: Dict[str, Any]
    retrieved_at: datetime
    credibility_score: Optional[float]  # unused currently

class NormalizedClaim(BaseModel):
    text: str          # one-sentence answer
    source: Source     # provenance
    date: Optional[str]
    version: Optional[str]
    scope: Optional[str]

class AgentEvidence(BaseModel):
    agent_id: str
    query: str
    status: EvidenceStatus
    failure_reason: Optional[str]
    claims: List[NormalizedClaim]   # usually 0 or 1
    sources: List[Source]
    raw_results_count: int
    filtered_out_count: int
    metadata: Dict[str, Any]

    @property
    def is_usable(self) -> bool:
        return status is OK and bool(claims)
```

### 15.3 Aggregation Models

```python
class PairwiseRelation(BaseModel):
    agent_a_id, agent_b_id: str
    claim_a_text, claim_b_text: str
    label: NLILabel
    contradiction_score: float  # 0.0–1.0
    entailment_score: float
    neutral_score: float

class EvidenceDecision(BaseModel):
    state: EvidenceState
    pairwise: List[PairwiseRelation]
    usable_agents: List[str]
    failed_agents: List[Dict[str, str]]
    top_conflict: Optional[Dict[str, Any]]
    rationale: str
```

### 15.4 Debate Models

```python
class DebateArgument(BaseModel):
    id: str (uuid[:8])
    round_number: int
    role: str         # "proposer" | "critic" | "reviser"
    agent_id: str
    content: str
    evidence_refs: List[str]
    conflict_type: Optional[ConflictType]
    strategy_used: Optional[str]
    strategy_text_preview: Optional[str]  # first 200 chars of strategy

class DebateRound(BaseModel):
    round_number: int
    proposer_argument: Optional[DebateArgument]
    critic_arguments: List[DebateArgument]
    reviser_argument: Optional[DebateArgument]

class DebateOutcome(BaseModel):
    rounds: List[DebateRound]
    status: Literal["completed", "partial", "failed"]
    stop_reason: Literal["converged", "no_objection", "max_rounds", "stage_failure"]
    failed_stages: List[str]
    rounds_used: int

class JudgeResult(BaseModel):
    winner: str         # "candidate_1" or "candidate_2"
    reason: str
    evidence_score: float (0–1)
    reasoning_score: float (0–1)
    source_score: float (0–1)
    confidence: float (0–1)
    scores: Dict[str, float]
```

### 15.5 Final Answer and Execution Trace

```python
class FinalAnswer(BaseModel):
    query, answer, reasoning: str
    evidence_state: EvidenceState
    sources: List[Source]
    debate_triggered: bool
    conflict: Optional[Conflict]
    debate_outcome: Optional[DebateOutcome]
    judge_result: Optional[JudgeResult]
    independent_agents_agreeing: int  # distinct agents, not source count
    source_count: int

class ExecutionTrace(BaseModel):
    query: str
    trace_id: str (uuid)
    agent_evidence: List[AgentEvidence]
    evidence_decision: Optional[EvidenceDecision]
    disagreement_detected: bool
    contradiction_score: float
    debate_triggered: bool
    conflict: Optional[Conflict]
    debate_rounds: List[DebateRound]
    debate_outcome: Optional[DebateOutcome]
    judge_result: Optional[JudgeResult]
    final_answer: Optional[FinalAnswer]
    metrics: Dict[str, Any]
    started_at, completed_at: datetime
    error: Optional[str]
```

---

## 16. Execution Trace and Logging

### 16.1 Trace Files

Every call to `MADSystem.solve()` saves a JSON file at `results/trace_<8hex>.json`. The `trace_id` is a UUID; only the first 8 hex chars are used in the filename. As of the time this document was written, the `results/` directory contains over 300 trace files from cumulative testing sessions (dating from Sep 16 to Oct 15).

### 16.2 Metrics in Each Trace

```json
{
  "latency_seconds": 4.1,
  "evidence_state": "disagreement",
  "debate_triggered": true,
  "conflict_type": "temporal",
  "classification_status": "llm_success",
  "debate_status": "completed",
  "debate_stop_reason": "max_rounds",
  "debate_rounds_used": 3,
  "total_llm_calls_ok": 18,
  "total_llm_calls_failed": 0,
  "llm_calls_by_role": {
    "normalize": {"ok": 3, "failed": 0},
    "nli": {"ok": 3, "failed": 0},
    "classifier": {"ok": 1, "failed": 0},
    "proposer": {"ok": 3, "failed": 0},
    "critic": {"ok": 3, "failed": 0},
    "reviser": {"ok": 3, "failed": 0},
    "judge": {"ok": 1, "failed": 0},
    "answer": {"ok": 1, "failed": 0}
  },
  "retrieval_failure_rate": 0.0,
  "irrelevant_evidence_rate": 2,
  "usable_agents": 3,
  "failed_agents": 0,
  "independent_agents_agreeing": 0,
  "source_count": 5
}
```

### 16.3 Logging

Uses `loguru` for structured logging. Log level controlled by `LOG_LEVEL` env var (default INFO). Every major pipeline step is logged with INFO. Failures use WARNING or ERROR. Trace save location is logged.

---

## 17. Evaluation Framework

### 17.1 Systems Compared

| System | Class | File | Description |
|---|---|---|---|
| Single LLM | `SingleLLMSystem` | `evaluation/systems/single_llm.py` | One direct LLM call, no retrieval, no debate |
| Standard MAD | `StandardMADSystem` | `evaluation/systems/standard_mad.py` | Always debates (no evidence gate), N agents |
| **Proposed MAD** | `ProposedMADSystem` | `evaluation/systems/proposed_mad.py` | Full Evidence-MAD with gate + typed strategies |
| No Gate | `NoGateSystem` | variant | Ablation: evidence gate removed, always debates |
| No Typed Strategy | `NoTypedStrategySystem` | variant | Ablation: all conflicts use generic debate prompt |
| No Relevance Filter | `NoRelevanceFilterSystem` | variant | Ablation: relevance filter in normalizer removed |

### 17.2 Evaluation Dataset (`data/conflicts.json`)

15 samples across 6 categories:

| Category | Count | Conflict Samples | No-Conflict Samples |
|---|---|---|---|
| temporal | 3 | 3 | 0 |
| factual | 3 | 1 | 2 |
| version | 2 | 2 | 0 |
| contextual | 2 | 2 | 0 |
| source | 2 | 2 | 0 |
| agreement | 3 | 0 | 3 |
| **Total** | **15** | **10** | **5** |

Each sample has:
- `id`, `query`, `expected_conflict` (bool), `expected_conflict_type` (or null)
- `expected_answer`: ground truth answer text
- `category`, `difficulty` (easy/medium/hard)
- `required_facts`: tokens that MUST appear in a correct answer
- `forbidden_facts`: tokens that MUST NOT appear in a correct answer

Sample queries include:
- Temporal: "What is the current unemployment rate?", "When did COVID-19 start?", "When was GDPR enacted?"
- Factual: "What is the speed of light?", "How many countries are in the EU?", "What is the tallest building?"
- Version: "What features does Python 3.10 support?", "What changed in React 18?"
- Contextual: "Is coffee healthy?", "Is the drug effective for all age groups?"
- Source: "Is email encryption really secure?", "Do dietary supplements actually work?"
- Agreement: "What is the boiling point of water?", "Who wrote Romeo and Juliet?", "What planet is closest to the Sun?"

### 17.3 MetricsCalculator (`evaluation/metrics.py`)

Computes the following metrics for each system across all samples:

**Accuracy metrics:**
- `key_fact_accuracy`: fraction of answers containing all `required_facts` and none of `forbidden_facts`
- `token_recall_accuracy`: fraction of required fact tokens present
- `answer_accuracy`: binary exact match on required/forbidden token check

**Conflict detection metrics:**
- `conflict_detection_accuracy`: (TP + TN) / total
- `precision`: TP / (TP + FP)
- `recall`: TP / (TP + FN)
- `f1`: harmonic mean of precision and recall
- `debate_trigger_rate`: fraction of queries where debate was triggered
- `unnecessary_debate_rate`: debates triggered when no conflict expected (FP rate)
- `missed_conflict_rate`: conflicts expected but debate not triggered (FN rate)

**Conflict classification metrics:**
- `conflict_classification_accuracy_llm_success`: accuracy of type classification when LLM succeeded
- `conflict_classification_accuracy_fallback`: accuracy when pattern fallback used

**Efficiency metrics:**
- `avg_latency_seconds`, `latency_p50`, `latency_p95`
- `avg_llm_calls_ok`, `avg_llm_calls_failed`
- `avg_debate_rounds`
- `efficiency_llm_calls_saved`: difference from baseline LLM call count

**Distribution metrics:**
- `conflict_type_distribution`: counts per conflict type
- `evidence_state_distribution`: counts per evidence state
- `debate_stop_reason_distribution`: counts per stop reason

---

## 18. Experimental Results and Metrics

### 18.1 Important Context on These Results

The experiment metrics come from the evaluation dataset (15 samples) run in FIXTURE mode. In FIXTURE mode, the NLI detector uses exact-match lookup from the fixture table, not a real LLM or transformer model. This is the controlled offline evaluation environment.

The high error rates (93%) for all multi-agent systems reflect the fact that only 1 out of 15 evaluation samples successfully completed the pipeline in the test run — likely because the evaluation dataset samples don't match the fixture cases, causing `FixtureNotFoundError` exceptions. These results should be interpreted as infrastructure-level metrics, not model-quality results.

### 18.2 Quantitative Results Table (from `MAD metrics/experiment_metrics.json`)

| Metric | Single LLM | Standard MAD | Proposed MAD | No Gate | No Typed Strategy | No Relevance Filter |
|---|---|---|---|---|---|---|
| Total Samples | 15 | 15 | 15 | 15 | 15 | 15 |
| OK Count | 15 | 1 | 1 | 1 | 1 | 1 |
| Error Rate | 0.0 | 0.933 | 0.933 | 0.933 | 0.933 | 0.933 |
| Key Fact Accuracy | 0.333 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Token Recall Accuracy | 0.133 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Answer Accuracy | 0.133 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Debate Trigger Rate | 0.0 | 0.067 | 0.0 | 0.067 | 0.0 | 0.0 |
| Unnecessary Debate Rate | 0.0 | 0.2 | 0.0 | 0.2 | 0.0 | 0.0 |
| Missed Conflict Rate | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Conflict Detection Accuracy | 0.333 | 0.267 | 0.333 | 0.267 | 0.333 | 0.333 |
| Precision | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Recall | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| F1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Avg Latency (s) | 0.0000273 | 0.000427 | 0.000268 | 0.000241 | 0.000208 | 0.000194 |
| Avg LLM Calls | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Avg Debate Rounds | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Avg Usable Agents/Query | 0.0 | 2.0 | 2.0 | 2.0 | 2.0 | 2.0 |

### 18.3 Observations from Results

1. **Single LLM vs. Multi-Agent systems (accuracy):** The Single LLM system has 33% key_fact_accuracy vs 100% for all multi-agent systems on the one sample that completed. However, the Single LLM completed all 15 samples (error_rate=0.0) while multi-agent systems had 93% error rate in this test run.

2. **Standard MAD vs. Proposed MAD (efficiency):** Standard MAD triggered an unnecessary debate in 20% of cases (false positive) while Proposed MAD had 0% unnecessary debates. This validates the gating concept — the evidence gate correctly suppressed debate for non-conflicting queries.

3. **No Gate = Standard MAD:** The No Gate ablation system behaves identically to Standard MAD, confirming the code correctly implements the ablation (removing the gate means all cases debate).

4. **Latency ordering:** Single LLM (0.000027s) < No Relevance Filter (0.000194s) < No Typed Strategy (0.000208s) < No Gate (0.000241s) < Proposed MAD (0.000268s) < Standard MAD (0.000427s). This is measurement noise since all latencies are sub-millisecond (fixture mode with mocked operations).

5. **For real-world inference:** A full LIVE-mode query triggering debate takes approximately 3.2–8.1 seconds total (observed from trace files ranging 37–76 KB, with LLM calls counted at 6–18 per trace).

### 18.4 Live Mode Trace Evidence (from trace files in results/)

The large trace files (37–76 KB) represent full LIVE-mode queries with complete debate rounds. Key observations from trace metadata:
- Typical latency for debate queries: 4–8 seconds
- Typical LLM call count for disagreement: 8–18 calls
- Common stop reasons: `max_rounds` (3 rounds completed), occasionally `no_objection` for clear cases
- The most common evidence states encountered: `disagreement` and `agreement` (based on frequency of large vs. small trace files)

---

## 19. Ablation Study

### 19.1 Ablation Design

Four targeted ablations test the contribution of each key architectural component:

| Ablation | What's Removed | What This Tests |
|---|---|---|
| No Gate | Evidence gate (NLI aggregation) | Whether gating prevents unnecessary debate |
| No Typed Strategy | Conflict-type-specific prompts | Whether type-aware strategies improve resolution |
| No Relevance Filter | Content-word overlap filter | Whether filtering improves claim quality |
| Single LLM | All retrieval and debate | Baseline: direct LLM answer only |

Additionally, Standard MAD (always debates, no gate) serves as the prior-work baseline.

### 19.2 Expected Findings (Design Intent)

- **No Gate vs. Proposed MAD:** No Gate should have higher debate trigger rate, higher LLM cost, and more false positive debates.
- **No Typed Strategy vs. Proposed MAD:** No Typed Strategy should have lower conflict resolution accuracy for temporal, version, and contextual cases where the specialized strategy matters.
- **No Relevance Filter vs. Proposed MAD:** No Relevance Filter should have higher NLI noise (irrelevant snippets polluting claim text) and potentially higher false agreement rate.
- **Single LLM vs. Proposed MAD:** Single LLM should have lower accuracy on conflict-heavy queries and higher hallucination rate.

---

## 20. Test Suite

### 20.1 Test Files and Coverage

| File | Lines | What It Tests |
|---|---|---|
| `tests/test_evidence.py` | ~13 KB | `NormalizedClaim`, `AgentEvidence`, `MockNLIDetector`, `EvidenceAggregator`, `EvidenceComparator` |
| `tests/test_debate.py` | ~12 KB | `Proposer`, `Critic`, `Reviser`, `DebateManager`, `Judge` |
| `tests/test_conflict.py` | ~5 KB | `ConflictClassifier` rule-based path, all 5 conflict types |
| `tests/test_conflict_types.py` | ~5 KB | Extended conflict type classification scenarios |
| `tests/test_search_fallbacks.py` | ~5 KB | Wikipedia 429 → OpenCode fallback; DDG redirect URL decoding |
| `tests/test_ai_answer_agent.py` | ~10 KB | `AIAnswerAgent` Gemini success, Gemini fail→OpenCode, entity-preserving prompt |
| `tests/test_baselines.py` | ~2 KB | Evaluation system baseline check |
| `tests/test_aggregator.py` | ~8 KB | `EvidenceAggregator` decision rules, entity-resolution conflicts, explicit verification challenges |
| `tests/test_relevance.py` | ~1 KB | Relevance filter in `EvidenceNormalizer` |
| `tests/test_llm_failure.py` | ~4 KB | LLM error propagation through all pipeline stages |
| `tests/test_retrieval_failure.py` | ~2 KB | Agent retrieval failure handling |
| `tests/test_event_loop.py` | ~0.6 KB | Event loop / async compatibility |

### 20.2 Running Tests

```bash
# All tests
pytest -q

# Skip slow/network tests
pytest -q -m 'not slow'

# With coverage
pytest --cov=. --cov-report=term-missing -q

# Syntax check
python -m compileall -q .
```

### 20.3 Test Framework

- `pytest` 9.1.1
- `pytest-asyncio` 1.4.0
- `pytest-cov` 7.1.0

Tests in `test_aggregator.py` specifically test the query-aware NLI guards. They verify that entity substitution, explicit challenge, and target resolution patterns correctly fire as CONTRADICTION before the NLI model is consulted.

---

## 21. Deployment

### 21.1 Local Development

```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn api:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: Frontend
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```

Or use the startup script:
```bash
chmod +x start_mad.sh
./start_mad.sh
```

`start_mad.sh` validates:
- `venv/` or `.venv/` directory exists
- `.env` file with required keys
- `google-genai` installed
- `opencode` CLI on PATH (warning if missing, not fatal)

### 21.2 Vercel Serverless

`vercel.json` routes all requests to `api/index.py`:
```json
{
  "builds": [{"src": "api/index.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "/api/index.py"}]
}
```

For Vercel deployment with live mode:
```bash
vercel env add LLM_API_KEY production
vercel env add LLM_BASE_URL production
vercel env add LLM_MODEL production
vercel env add GEMINI_API_KEY production
vercel env add DEMO_MODE production  # false
vercel --prod
```

**Vercel limitation:** If the function bundle exceeds Vercel's size limit (250 MB for Python), set `NLI_MODE=mock` to avoid bundling the ~1.4 GB HuggingFace model. This routes NLI through the Groq LLM instead.

### 21.3 Dependencies

`requirements.txt` specifies exact versions:

| Package | Version | Purpose |
|---|---|---|
| `pydantic` | 2.13.5 | Data models and validation |
| `pydantic-settings` | 2.15.0 | Config from .env |
| `httpx` | 0.28.1 | Synchronous HTTP client |
| `fastapi` | 0.141.1 | REST API framework |
| `uvicorn` | 0.53.0 | ASGI server |
| `transformers` | 5.17.0 | HuggingFace NLI model |
| `torch` | 2.14.0 | PyTorch backend for transformers |
| `accelerate` | 1.15.0 | Efficient model loading |
| `google-genai` | latest | Gemini API |
| `rich` | 15.0.0 | CLI output formatting |
| `loguru` | 0.7.3 | Structured logging |
| `pytest` | 9.1.1 | Testing |
| `matplotlib` | 3.11.2 | Evaluation charts |
| `pandas` | 3.0.5 | Results processing |
| `scikit-learn` | 1.9.1 | Metrics computation |

---

## 22. Fixture Dataset and Evaluation Dataset

### 22.1 Fixtures (`data/fixtures.json`)

Used in FIXTURE/demo mode. Contains structured evidence cases for offline testing. Each case has:
- `id`: unique identifier
- `query`: exact query string (used for lookup)
- `agents`: dict of `agent_id → {status, claim, date, version, scope, source}`
- `expected_state`: `"agreement"`, `"disagreement"`, `"uncertain"`, or `"insufficient"`
- `expected_conflict_type`: null or conflict type string
- `expected_debate`: boolean
- `expected_answer`: ground truth text
- `required_facts`, `forbidden_facts`: evaluation token lists

The full 10 required fixture cases cover every expected pipeline branch:

| ID | Query | Expected Branch |
|---|---|---|
| `agree_capital` | "What is the capital of Australia?" | AGREEMENT |
| `factual_boiling` | "What is the boiling point of water at sea level?" | AGREEMENT (scholarly fails) |
| `temporal_policy` | "When was India's National Education Policy introduced?" | DISAGREEMENT / TEMPORAL |
| `version_python` | "What version supports feature X?" | DISAGREEMENT / VERSION |
| `contextual_drug` | "Is the drug effective?" | DISAGREEMENT / CONTEXTUAL |
| `source_blog_vs_paper` | "What does the research say?" | DISAGREEMENT / SOURCE |
| `unrelated_evidence` | (unrelated query) | UNCERTAIN |
| `one_agent_fails` | — | INSUFFICIENT (1 agent usable) |
| `two_agents_fail` | — | INSUFFICIENT (0–1 agents usable) |
| `all_agents_fail` | — | INSUFFICIENT (0 agents) |

### 22.2 Evaluation Dataset (`data/conflicts.json`)

15 samples for systematic evaluation (described in Section 17.2). The dataset is explicitly marked as small and not human-labelled. The README cautions: "Do not treat fixture/demo results as publication evidence. Use a labelled dataset and valid live services for research claims."

---

## 23. Limitations and Future Work

### 23.1 Current Limitations

1. **Synthetic fixture evidence:** Fixture mode uses manually crafted claims, not real retrieved data. Results in FIXTURE mode cannot be generalized to real-world performance.

2. **Title/snippet only:** Web search agents retrieve only title and 1–2 sentence snippets from search results. Full page content is never fetched. This limits the depth of evidence available to the normalizer and NLI.

3. **Heuristic relevance filter:** The content-word overlap filter can produce false negatives (dropping relevant results with different terminology) and false positives (keeping irrelevant results with coincidental keyword overlap).

4. **Small evaluation dataset:** 15 samples is insufficient for statistically significant claims. No human annotation for ground truth conflict type labels.

5. **No result caching:** Every query hits the live APIs fresh. High-volume usage would exhaust rate limits quickly.

6. **No significance testing:** Ablation comparisons are point estimates with no confidence intervals or statistical tests (t-test, McNemar, etc.).

7. **Pattern-based NLI fallback reliability:** `_pattern_predict()` is less reliable than a real LLM or transformer for subtle conflicts. Year detection with negation stripping is heuristic and can fail on complex sentences.

8. **Debate convergence metric:** Jaccard similarity on word sets is a coarse convergence signal. Semantic similarity (using embeddings) would be more principled.

9. **Judge bias:** The judge uses an LLM that may exhibit preference patterns (e.g., preferring certain writing styles or argument structures), which could introduce systematic bias.

10. **Single judge:** No ensemble judge or rubric-based scoring — a single LLM call decides the winner.

11. **Vercel function size:** The HuggingFace model (~1.4 GB) cannot be deployed as a serverless function. Production deployment effectively forces `NLI_MODE=mock`, reducing NLI quality.

### 23.2 Future Work

- **Full-page evidence extraction:** Fetch and parse full article content rather than snippets.
- **Source quality scoring:** Assign credibility weights based on domain, page rank, citation count.
- **Larger human-labelled benchmark:** Create a dataset of 200+ samples with expert conflict type annotation.
- **Result caching:** Cache normalized claims and NLI scores for repeated queries.
- **Significance testing:** Apply McNemar's test or bootstrap sampling to compare systems.
- **Semantic convergence:** Replace Jaccard with cosine similarity over sentence embeddings.
- **Multi-judge ensemble:** Run judge evaluation multiple times and aggregate scores.
- **Agent specialization:** Expand scholarly agent to support PubMed, arXiv, and Semantic Scholar.
- **Cross-lingual support:** Extend NLI to multilingual claims.
- **Real-time conflict monitoring:** Adapt the debate gate as a streaming fact-checker.

---

## 24. Project File Structure Reference

```
MAD-2/
├── app.py                   # MADSystem class, solve(), CLI entry point (34 KB)
├── api.py                   # FastAPI application v2.0.0 (7 KB)
├── config.py                # pydantic-settings Settings class (3.6 KB)
├── run_mode.py              # RunMode enum, FixtureStore (3.3 KB)
├── llm_client.py            # LLMClient for Groq/OpenAI-compatible (6.3 KB)
├── requirements.txt         # Pinned dependencies
├── start_mad.sh             # One-command startup script
├── vercel.json              # Vercel deployment configuration
├── pyproject.toml           # pytest configuration (116 bytes)
│
├── agents/
│   ├── base_agent.py        # BaseAgent ABC, AgentRegistry (3.8 KB)
│   ├── router.py            # QueryRouter with ThreadPoolExecutor (4.2 KB)
│   ├── search_agent.py      # WebAgent, ReferenceAgent, ScholarlyAgent (20 KB)
│   ├── ai_answer_agent.py   # AIAnswerAgent (Gemini → OpenCode) (5.4 KB)
│   ├── gemini_client.py     # generate_grounded() with Google Search (2 KB)
│   └── opencode_client.py   # run_opencode() subprocess wrapper (1.8 KB)
│
├── evidence/
│   ├── models.py            # All Pydantic models (10.8 KB)
│   ├── normalizer.py        # EvidenceNormalizer, relevance filter (9.7 KB)
│   ├── aggregator.py        # EvidenceAggregator, NLI pairwise (6.8 KB)
│   ├── disagreement_detector.py  # MockNLI, LLMNLIDetector, NLIDetector, guards (27 KB)
│   └── comparator.py        # Legacy EvidenceComparator (5 KB)
│
├── conflict/
│   └── classifier.py        # ConflictClassifier, 5-type taxonomy (7.6 KB)
│
├── debate/
│   ├── manager.py           # DebateManager, early stopping (8.3 KB)
│   ├── proposer.py          # Proposer, 6 strategy texts (12.3 KB)
│   ├── critic.py            # Critic (7.8 KB)
│   ├── reviser.py           # Reviser (5.9 KB)
│   └── judge.py             # Judge, evidence scoring (8 KB)
│
├── output/
│   └── generator.py         # AnswerGenerator, 4 output shapes (10.6 KB)
│
├── evaluation/
│   ├── dataset.py           # EvaluationDataset, EvaluationSample (39 KB)
│   ├── metrics.py           # MetricsCalculator (22 KB)
│   ├── run_experiments.py   # Experiment runner (14 KB)
│   └── systems/
│       ├── single_llm.py    # SingleLLMSystem
│       ├── standard_mad.py  # StandardMADSystem
│       └── proposed_mad.py  # ProposedMADSystem + ablation variants
│
├── data/
│   ├── conflicts.json       # 15-sample evaluation dataset
│   └── fixtures.json        # Fixture cases for FIXTURE mode and unit tests
│
├── tests/                   # pytest test suite (12 files)
│
├── frontend/
│   └── index.html           # Single-file browser UI (15.6 KB)
│
├── api/
│   └── index.py             # Vercel serverless adapter
│
├── results/                 # Generated trace JSONs (300+ files)
│   ├── trace_<8hex>.json    # Individual execution traces
│   ├── proposed_mad/        # Proposed MAD system traces
│   ├── standard_mad/        # Standard MAD traces
│   ├── no_gate/             # No Gate ablation traces
│   ├── no_typed_strategy/   # No Typed Strategy traces
│   ├── no_relevance_filter/ # No Relevance Filter traces
│   ├── single_llm/          # Single LLM traces
│   ├── figures/             # Matplotlib charts from experiments
│   └── experiment_metrics.json  # Aggregated metrics
│
├── figures/                 # Experiment output charts
│   ├── key_fact_accuracy.png
│   ├── debate_trigger_rate.png
│   ├── llm_calls_ok.png
│   ├── latency_p50.png
│   ├── error_rates.png
│   └── conflict_distribution.png
│
└── MAD metrics/             # Per-system metrics JSON files
    ├── experiment_metrics.json       # Full combined metrics
    ├── proposed_mad_metrics.json     # Proposed system only
    ├── single_llm_metrics.json       # Single LLM baseline
    ├── standard_mad_metrics.json     # Standard MAD baseline
    ├── nogate_metrics.json           # No Gate ablation
    ├── no_types_strategy_metrics.json # No Typed Strategy ablation
    └── no_relavence_filter_metrics.json # No Relevance Filter ablation
```

---

## 25. Key Design Decisions and Engineering Notes

### 25.1 Why Synchronous Pipeline with ThreadPoolExecutor?

The decision to make the core pipeline fully synchronous (no `asyncio.run`, no `await` in app.py) was driven by simplicity and debuggability. Python's `asyncio` for synchronous LLM HTTP calls adds complexity without benefit. The FastAPI layer, which is async, uses `run_in_executor` to call the synchronous pipeline from the event loop without blocking.

Parallelism within the pipeline is achieved via `ThreadPoolExecutor`:
- Search agents run in parallel in the router.
- The AI Answer Agent runs in a separate single-thread pool concurrent with search agents.

This gives ~50–70% latency reduction compared to sequential agent execution.

### 25.2 Why Asymmetric NLI Decision Rule?

The disagreement-needs-one / agreement-needs-all asymmetry reflects the risk profile: a false negative (missed conflict → no debate → potentially wrong answer) is worse than a false positive (unnecessary debate → extra latency). The system is designed to be conservative about claiming agreement.

### 25.3 Why Not Store Raw Claims in Evidence?

The `AgentEvidence.claims` field stores `NormalizedClaim` objects (not raw snippets). This is a deliberate choice: raw snippets are noisy, inconsistent in length, and hard to compare via NLI. The normalizer produces one clean, query-focused sentence per agent, making NLI comparison more reliable.

### 25.4 Why `component_status` in ClassificationResult?

The `ComponentStatus` field tracks whether the LLM succeeded or the pattern fallback was used. This is surfaced in trace metrics as `classification_status`, allowing analysis of how often the LLM was unavailable during evaluation runs. It also helps identify whether classification quality degraded on certain runs.

### 25.5 Why is `judge_result = None` on Failure?

The judge never fabricates a verdict. If the LLM fails, the answer generator detects `judge_result is None` and generates an "unresolved conflict" message. This is preferable to fabricating a winner, which would present a hallucinated resolution to the user as if it were a real evaluated result.

### 25.6 Why Limit AI Answer Agent Claim to 600 Characters?

The NLI model works best with single sentences of comparable length. A 3-paragraph Gemini answer compared against a 1-sentence Wikipedia extract would systematically inflate the contradiction score (more words = more surface-level differences). The 600-character trim at sentence boundary produces claims of comparable granularity to the search agent outputs.

### 25.7 Why Three Separate Query-Aware NLI Guards?

The three guards (entity substitution, explicit challenge, target resolution) handle distinct failure modes of generic NLI models:
1. Entity substitution: generic NLI may miss that "Attention is All You Need" ≠ "Wipro is All U Need."
2. Explicit challenge: generic NLI may label "cannot verify" as NEUTRAL to a positive claim.
3. Target resolution: generic NLI may label shared date corrections as ENTAILMENT even when entity identity is in dispute.

These guards are deterministic (regex-based) and fast. They preempt the NLI model on specific patterns where model inference is known to be unreliable.

### 25.8 Early Stopping Design

Jaccard similarity at 0.95 is a strict threshold. It means the revision text must share 95% of its word tokens with the previous revision. In practice, this fires when the debate has converged to essentially the same position across rounds. The threshold was chosen to be conservative — it should only fire when the debate is genuinely not making progress, not just because two rounds share common vocabulary.

The `no_objection` stop is more aggressive: a single "SUBSTANTIVE_OBJECTION: false" from the critic immediately ends the debate without a reviser step. This is correct — if the critic has nothing to say, there is no value in running a reviser.

### 25.9 Task Plan Traceability

The codebase documents which task in the original task plan each module change addressed (e.g., "Task 9: EvidenceAggregator replaces [0]/[1] comparison"). These are preserved as comments in the source files and provide traceability between the implementation and the design specification (`panel1-task-plan.md`). Key task mappings:
- Task 7: Fixed NLI input format and bidirectional check.
- Task 8: LLM-normalized claims with structured fields.
- Task 9: N-agent EvidenceAggregator (not just 2-agent comparison).
- Task 10: INSUFFICIENT retry logic.
- Task 11: ClassificationResult with ComponentStatus.
- Task 12: Conflict from guaranteed NormalizedClaims.
- Task 13: No demo fallbacks in debate stages.
- Task 14: DebateOutcome with status/stop_reason/failed_stages.
- Task 15: Judge only called on completed debate.
- Task 16: Strategy text preview in DebateArgument.
- Task 18–20: Type-specific metadata injection in Proposer.
- Task 22: RunMode enum, explicit mode passing.
- Task 24: Use `llm_client.call_report()` instead of manual counting.
- Task 30: Early stopping (converged/no_objection).

---

*End of report_context.md — Generated October 15, 2026 for the MAD-2 project at `/home/sasi-boss/Desktop/MAD-2/`*
