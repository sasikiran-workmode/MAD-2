"""Part 4: Chapters 3–5: System Design, Agents Layer, Evidence Pipeline"""

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 3 – SYSTEM DESIGN AND ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(3, "SYSTEM DESIGN AND ARCHITECTURE")

section_heading("3.1  High-Level Architecture")

body_para(
    "The Evidence-MAD system is structured as a linear pipeline that transforms a user query "
    "into a final answer through a sequence of well-defined stages. The pipeline is implemented "
    "in MADSystem.solve() in app.py and is entirely synchronous. The key design principle is "
    "that each stage has a clearly defined input and output type, and each stage can fail "
    "gracefully without bringing down the entire pipeline."
)

body_para(
    "At the highest level, the pipeline can be summarized as follows. The user submits a "
    "natural language question. Four agents — Web, Reference, Scholarly, and AI Answer — "
    "retrieve evidence for the query in parallel using a ThreadPoolExecutor. The evidence "
    "from the three search agents passes through a two-stage normalization process to produce "
    "one clean normalized claim per agent. The AI Answer Agent's output is already normalized "
    "and bypasses this stage. The EvidenceAggregator then runs pairwise NLI comparison on "
    "all agent claims to produce one of four evidence decisions: AGREEMENT, DISAGREEMENT, "
    "UNCERTAIN, or INSUFFICIENT. Three of these four paths lead to direct answer generation "
    "without any debate. Only the DISAGREEMENT path proceeds to the ConflictClassifier and "
    "DebateManager."
)

body_para(
    "When disagreement is detected, the ConflictClassifier assigns a conflict type to the "
    "top-scoring contradicting pair. The DebateManager then runs up to MAX_DEBATE_ROUNDS "
    "cycles of Proposer, Critic, and Reviser, using conflict-type-specific strategy text "
    "in the Proposer's prompt. After debate completes (or stops early), the Judge evaluates "
    "the debate transcript and selects a winner. Finally, the AnswerGenerator produces a "
    "structured final answer, and the entire execution is saved as a JSON trace file."
)

section_heading("3.2  Two-Mode Operation")

body_para(
    "The system supports two strictly isolated operating modes controlled by the RunMode enum "
    "in run_mode.py. In FIXTURE mode (demo_mode=True), all agent evidence is loaded from "
    "data/fixtures.json rather than making any live API calls. The NLI detector uses "
    "exact-match lookup from the fixture table. All debate stages return deterministic canned "
    "text. FIXTURE mode requires no API keys and is used for offline demonstrations and unit "
    "tests."
)

body_para(
    "In LIVE mode (demo_mode=False), the full real pipeline executes. The LLM_API_KEY must "
    "be set in the .env file. The system uses LLMNLIDetector (default) or NLIDetector "
    "(HuggingFace transformer if NLI_MODE=transformers). The AI Answer Agent calls the "
    "Gemini API with Google Search grounding, falling back to the OpenCode CLI if Gemini "
    "fails. Search agents hit real HTTP endpoints with retry logic and exponential backoff."
)

body_para(
    "The RunMode is passed explicitly into every component constructor. No component reads "
    "settings.demo_mode directly — this was an explicit architectural decision to prevent "
    "mode leakage, where a LIVE-mode component might accidentally fall back to fixture "
    "behavior. The separation also makes unit testing straightforward: any component can "
    "be tested in FIXTURE mode without requiring API credentials."
)

section_heading("3.3  Component Dependency Map")

body_para(
    "The system is organized into seven functional layers: Configuration, LLM Client, Agents, "
    "Evidence, Conflict, Debate, and Output. Each layer depends only on layers below it, "
    "creating a clean dependency hierarchy with no circular references."
)

body_para(
    "The Configuration layer (config.py) uses pydantic-settings to load all parameters from "
    "the .env file. The singleton pattern via @lru_cache ensures Settings is created once per "
    "process. The LLM Client layer (llm_client.py) wraps the Groq/OpenAI-compatible API and "
    "tracks per-role call counts. The Agents layer provides four independent retrieval agents "
    "and a QueryRouter for parallel dispatch. The Evidence layer handles normalization, "
    "aggregation, and NLI comparison. The Conflict layer classifies detected disagreements. "
    "The Debate layer orchestrates the multi-round argument. The Output layer formats the "
    "final answer based on the evidence state."
)

section_heading("3.4  Configuration and Environment")

body_para(
    "All runtime configuration is managed through environment variables defined in the .env "
    "file and validated by the Settings class in config.py. The most important parameters "
    "are summarized in Table 3.1."
)

add_table(
    ["Environment Variable", "Default", "Description"],
    [
        ["LLM_API_KEY", "(empty)", "Groq / OpenAI-compatible key"],
        ["LLM_BASE_URL", "https://api.groq.com/openai/v1", "LLM endpoint URL"],
        ["LLM_MODEL", "qwen/qwen3.8-27b", "Model identifier"],
        ["LLM_TEMPERATURE", "0.0", "Deterministic outputs"],
        ["NLI_MODE", "mock", "mock = LLM NLI, transformers = HuggingFace"],
        ["DISAGREEMENT_THRESHOLD", "0.70", "Min contradiction score for DISAGREEMENT"],
        ["ENTAILMENT_THRESHOLD", "0.70", "Min entailment score for AGREEMENT"],
        ["MAX_DEBATE_ROUNDS", "3", "Maximum debate iterations"],
        ["DEMO_MODE", "false", "Use FIXTURE mode if true"],
        ["GEMINI_API_KEY", "(empty)", "Google Gemini API key"],
        ["GEMINI_MODEL", "gemini-3.8-flash", "Gemini model identifier"],
    ],
    caption="Table 3.1: Key Configuration Parameters and Their Defaults"
)

body_para(
    "The validate() method of Settings is called at startup in LIVE mode and raises "
    "ValueError if LLM_API_KEY is not set. This prevents the system from starting without "
    "credentials and making partial progress before failing on the first LLM call. The "
    "settings object is accessed through get_settings(), which is decorated with @lru_cache "
    "to ensure it is created only once per process."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 4 – AGENTS LAYER
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(4, "AGENTS LAYER")

section_heading("4.1  Agent Registry and Base Class")

body_para(
    "All search agents in the system inherit from BaseAgent, an abstract base class defined "
    "in agents/base_agent.py. The BaseAgent requires implementing a single abstract method, "
    "retrieve(query: str) → Evidence, which must return an Evidence object containing a list "
    "of raw search results. Each agent is identified by a unique string agent_id. The "
    "AgentRegistry is a global singleton dictionary that maps agent_id to BaseAgent instance, "
    "allowing the QueryRouter to look up agents by identifier."
)

body_para(
    "Agent configuration is managed by AgentConfig, a Pydantic model that stores the "
    "agent_id, timeout in seconds, max_retries count, and an enabled flag. Setting "
    "enabled=False allows an agent to be deactivated through configuration without removing "
    "it from the codebase — useful for disabling the ScholarlyAgent when Crossref is "
    "temporarily unavailable."
)

add_table(
    ["Agent Class", "Agent ID", "Primary Source", "Fallback"],
    [
        ["WebAgent", "web_agent", "DuckDuckGo HTML", "OpenCode CLI"],
        ["ReferenceAgent", "reference_agent", "Wikipedia API", "OpenCode CLI"],
        ["ScholarlyAgent", "scholarly_agent", "Crossref REST", "DuckDuckGo"],
        ["AIAnswerAgent", "ai_answer_agent", "Google Gemini", "OpenCode CLI"],
    ],
    caption="Table 4.1: Search Agent Summary"
)

section_heading("4.2  QueryRouter")

body_para(
    "The QueryRouter in agents/router.py dispatches a user query to multiple agents in "
    "parallel using Python's concurrent.futures.ThreadPoolExecutor. For each query, it "
    "determines which agents to run: the Web Agent and Reference Agent always run; the "
    "Scholarly Agent is conditionally dispatched based on a keyword heuristic."
)

body_para(
    "The scholarly routing heuristic scans the query for academic vocabulary including "
    "keywords such as study, trial, meta-analysis, doi, peer-reviewed, systematic review, "
    "rct, cohort, clinical, journal, research, findings, published, abstract, citation, "
    "and paper. If any of these appear in the query, the ScholarlyAgent is dispatched "
    "alongside the Web and Reference agents. This selective routing ensures that the "
    "Crossref API is only called for queries where scholarly results are likely to be "
    "relevant, reducing unnecessary API calls for general factual questions."
)

body_para(
    "The AI Answer Agent is dispatched separately from the main router, using its own "
    "single-thread executor that runs concurrently with the QueryRouter's dispatch. This "
    "means all four agents execute in parallel, maximizing throughput and minimizing "
    "total retrieval latency. The router collects results from all futures with a timeout "
    "and gracefully handles any agent that times out or raises an exception by marking "
    "that agent as RETRIEVAL_FAILED."
)

section_heading("4.3  Web Agent")

body_para(
    "The WebAgent (agents/search_agent.py) retrieves results from DuckDuckGo's HTML "
    "interface at https://html.duckduckgo.com/html/. Unlike DuckDuckGo's JavaScript-heavy "
    "main interface, the HTML version is scrapable with simple HTTP requests and regex "
    "pattern matching. The agent extracts result titles from elements with class "
    "result__a and snippets from class result__snippet. DuckDuckGo encodes redirect URLs "
    "in the format /l/?uddg=<encoded>, which the agent decodes using urllib.parse.parse_qs "
    "to extract the actual destination URL."
)

body_para(
    "The agent implements retry logic with exponential backoff: up to three attempts with "
    "delays of 2, 4, and 8 seconds on HTTP 429 (rate limit), 5xx (server error), and "
    "connection timeout responses. If all retries are exhausted, the fallback path calls "
    "_opencode_web_fallback(), which submits the query to an OpenCode CLI model and "
    "returns synthetic search results. The fallback results are labeled with the same "
    "web_agent identity — the NLI and debate layers never see provider-level information, "
    "maintaining a clean abstraction boundary."
)

section_heading("4.4  Reference Agent")

body_para(
    "The ReferenceAgent queries the Wikipedia MediaWiki API at "
    "https://en.wikipedia.org/w/api.php with parameters action=query, list=search, "
    "and srsearch=<query>, retrieving up to five results per query. For each result, "
    "the agent fetches the page extract (summary paragraph) using a second API call "
    "with action=query and prop=extracts. The extract is truncated to the first 500 "
    "characters to keep the claim within the normalizer's expected snippet length."
)

body_para(
    "Wikipedia imposes rate limits that can trigger HTTP 429 responses, particularly "
    "during rapid successive queries. When a 429 is received, the agent waits using "
    "exponential backoff and retries up to three times. If the rate limit persists, "
    "the agent falls back to the OpenCode CLI using the OPENCODE_WIKI_MODEL, which "
    "is a lighter model optimized for reference-style knowledge retrieval. The fallback "
    "behaviour ensures that the Reference Agent always contributes a claim to the "
    "evidence pool, maintaining N ≥ 2 usable agents in most cases."
)

section_heading("4.5  Scholarly Agent")

body_para(
    "The ScholarlyAgent queries the Crossref REST API at "
    "https://api.crossref.org/works?query=<query>&rows=5. Crossref returns JSON with a "
    "message.items list, each item containing fields for title, DOI, abstract, author, "
    "and published date. The agent extracts the title and abstract for each item, "
    "truncating long abstracts to 300 characters. If Crossref returns no results or "
    "fails with an HTTP error, the agent falls back to the DuckDuckGo search function "
    "with the query modified to append the word research to bias results toward "
    "academic sources."
)

body_para(
    "One design consideration with the ScholarlyAgent is that Crossref results are "
    "academic paper metadata, not direct answers to factual questions. The LLM "
    "normalization step (Section 5.3) is particularly important for scholarly results "
    "because it must extract a claim-relevant statement from paper abstracts that may "
    "be written for a specialist audience. The relevance filter (Section 5.2) also "
    "plays a larger role for scholarly results because many retrieved papers may be "
    "tangentially related to the query topic without directly answering it."
)

section_heading("4.6  AI Answer Agent")

body_para(
    "The AIAnswerAgent (agents/ai_answer_agent.py) differs from the three search agents "
    "in an important way: it does not retrieve search results and normalize them. Instead, "
    "it directly produces a single normalized claim by querying the Google Gemini API with "
    "Google Search grounding enabled. The Gemini model with Search grounding can access "
    "real-time web results as part of its inference, effectively combining retrieval and "
    "normalization into a single step."
)

body_para(
    "The agent's prompt (PROMPT_TEMPLATE) explicitly instructs: \"Preserve every named "
    "entity exactly as written in the question: never silently correct, replace, or assume "
    "that a similarly named paper, product, person, or work is the same entity.\" This "
    "instruction directly addresses the entity-substitution problem described in Section 6.3. "
    "Without this instruction, Gemini would sometimes autocorrect a misspelled entity name "
    "and return information about the corrected entity, causing a false positive for the "
    "entity-substitution NLI guard."
)

body_para(
    "The claim text produced by the AI Answer Agent is trimmed to at most 600 characters "
    "at a sentence boundary by the _short() helper function. This is necessary because "
    "Gemini often produces multi-paragraph responses, which would compare poorly against "
    "the one-sentence claims produced by the search agents during NLI comparison. The "
    "full, untrimmed response is preserved in the metadata['full_answer'] field and "
    "included in the final answer generation step."
)

body_para(
    "When the Gemini API is unavailable, raises an authentication error, or exceeds the "
    "GEMINI_TIMEOUT (default 20 seconds), the agent falls back to the OpenCode CLI using "
    "the OPENCODE_MODEL. The OpenCode fallback calls the opencode run subprocess with the "
    "same prompt, enforces a OPENCODE_TIMEOUT (default 45 seconds), and returns the "
    "stdout as the claim text."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 5 – EVIDENCE PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(5, "EVIDENCE PIPELINE")

section_heading("5.1  Evidence Flow Overview")

body_para(
    "The evidence pipeline transforms raw search results from the three search agents into "
    "clean, normalized, query-focused claims suitable for NLI comparison. The AI Answer "
    "Agent bypasses the first two stages (relevance filter and LLM normalization) because "
    "its output is already a single synthesized claim. For search agents, the pipeline "
    "has three stages: relevance filtering, LLM normalization, and NLI aggregation."
)

body_para(
    "After retrieval, each search agent has a list of raw results, each with a title and "
    "snippet. The relevance filter discards results whose content words do not overlap "
    "sufficiently with the query. Surviving results are passed to the LLM normalizer, "
    "which produces one NormalizedClaim with structured fields (text, date, version, "
    "scope, source). The EvidenceAggregator then takes all agent claims and runs pairwise "
    "NLI to produce the final EvidenceDecision."
)

section_heading("5.2  Relevance Filter")

body_para(
    "The relevance filter is implemented in the _is_relevant() function in "
    "evidence/normalizer.py. It computes the content-word overlap between the query and "
    "a candidate result's title concatenated with its snippet. Content words are defined "
    "as all words not in a hardcoded stopword list of approximately 50 common English words. "
    "Numbers are always included as content words regardless of length, because year "
    "strings like 2020 are often the most discriminating feature for temporal queries."
)

body_para(
    "The filter's min_overlap threshold is set to 1, meaning at least one content word "
    "from the query must appear in the result's title or snippet. For very short queries "
    "with two or fewer content words, the threshold is always 1 to prevent over-filtering. "
    "Results that fail this check are counted in the filtered_out_count field of the "
    "AgentEvidence object, which is reported in the execution trace and used by the "
    "evaluation framework to compute the average irrelevant evidence rate."
)

body_para(
    "If all results for an agent are filtered out, the agent's status is set to "
    "EvidenceStatus.NO_RELEVANT_RESULTS. This is distinct from EvidenceStatus.RETRIEVAL_FAILED: "
    "the former means the agent successfully retrieved results but none were relevant to "
    "the query, while the latter means the agent could not retrieve results at all due to "
    "a network error, API failure, or timeout. Both statuses cause the agent to be excluded "
    "from the NLI comparison, but they are reported separately for diagnostic purposes."
)

section_heading("5.3  LLM Normalization")

body_para(
    "After relevance filtering, surviving search results are passed to the LLM normalizer "
    "with a carefully designed prompt. The prompt provides the original query and a numbered "
    "list of surviving result titles and snippets, and asks the LLM to synthesize one "
    "concise answer sentence. The normalizer also extracts structured metadata fields "
    "alongside the answer: date (year), version, and scope (population or platform)."
)

body_para(
    "These structured fields are critical downstream. The date field enables the NLI "
    "pattern detector to identify temporal conflicts between claims (e.g., one claim "
    "says 2019 and another says 2020). The version field enables version conflict "
    "detection. The scope field enables contextual conflict detection (e.g., one claim "
    "applies to adults, another to children). Without these fields, the pattern-based "
    "NLI fallback would have to extract dates and versions from free text, which is "
    "error-prone."
)

body_para(
    "The normalizer also implements meta-claim detection. Sometimes the LLM returns a "
    "statement like 'The snippets do not contain information about this topic' rather than "
    "an actual answer. The normalizer checks for ten meta-language patterns such as "
    "do not contain, no information, no relevant, unable to find, and not mentioned. "
    "If any of these patterns appear in the LLM's response, the normalizer treats the "
    "result as NO_RELEVANT_RESULTS rather than storing a useless meta-claim in the "
    "evidence pool. This prevents meta-language from being compared against real claims "
    "during NLI, which would systematically produce false contradictions."
)

section_heading("5.4  Evidence Aggregator")

body_para(
    "The EvidenceAggregator (evidence/aggregator.py) runs NLI for every unordered pair "
    "of usable agents. For three usable agents, this produces three pairwise comparisons "
    "(A-B, A-C, B-C). The aggregator applies an asymmetric decision rule: disagreement "
    "requires only one contradicting pair (conservative sensitivity), while agreement "
    "requires all pairs to confirm entailment (conservative specificity)."
)

body_para(
    "This asymmetry is a deliberate design choice. In the context of evidence-triggered "
    "debate, a false negative (missing a real disagreement and returning an incorrect "
    "agreed answer) is typically worse than a false positive (triggering unnecessary "
    "debate when agents actually agree). The asymmetric rule ensures that if even one pair "
    "of agents shows evidence of contradiction above the DISAGREEMENT_THRESHOLD, the "
    "system will investigate further through debate rather than silently suppressing the "
    "conflict."
)

body_para(
    "The formal decision rule is: if the count of usable agents is less than or equal "
    "to one, return INSUFFICIENT; else for each pair compute NLI scores; if any pair has "
    "contradiction_score greater than or equal to DISAGREEMENT_THRESHOLD return DISAGREEMENT; "
    "else if all pairs have entailment_score greater than or equal to ENTAILMENT_THRESHOLD "
    "return AGREEMENT; else return UNCERTAIN."
)

body_para(
    "The aggregator also identifies and records the top_conflict — the agent pair with the "
    "highest contradiction score. This pair's claims become claim_a and claim_b in the "
    "downstream ConflictClassifier and DebateManager, ensuring that the debate focuses on "
    "the most strongly conflicting evidence rather than an arbitrarily selected pair. "
    "NLI failures for individual pairs are handled gracefully: if NLI raises an NLIError "
    "for a pair, that pair is recorded with all scores equal to 0.0 and label NEUTRAL, "
    "preventing a single failing NLI call from crashing the entire aggregation."
)

add_table(
    ["EvidenceStatus", "Meaning", "Included in NLI?"],
    [
        ["OK", "Retrieval succeeded and claim normalized", "Yes"],
        ["NO_RELEVANT_RESULTS", "Retrieval ok but no relevant snippets", "No"],
        ["RETRIEVAL_FAILED", "Network/API error during retrieval", "No"],
    ],
    caption="Table 5.1: EvidenceStatus Values and Their Meanings"
)

page_break()
print("Part 4 (Chapters 3-5) done.")
