"""Part 3: Chapter 1 – Introduction, Chapter 2 – Literature Review"""

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 1 – INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(1, "INTRODUCTION")

section_heading("1.1  Overview and Motivation")

body_para(
    "In recent years the rapid proliferation of large language models (LLMs) has transformed how "
    "people seek and consume information. Systems like GPT-4, Gemini, and Llama have demonstrated "
    "impresssive capabilities across a broad range of tasks including summarization, translation, "
    "code generation, and open-domain question answering (Brown et al., 2020; Touvron et al., "
    "2023). Despite these advances, LLMs remain prone to a well-documented failure mode known as "
    "hallucination — the tendency to generate plausible-sounding but factually incorrect "
    "statements (Ji et al., 2023). The problem is especially acute for temporal facts (events "
    "that occurred after the model's training cutoff), version-specific details (changes between "
    "software or policy editions), and population-specific claims (findings that apply to one "
    "group but not another)."
)

body_para(
    "One promissing direction for mitigating hallucination is multi-agent debate (MAD), in which "
    "multiple independent agents each formulate an answer and then argue with each other, with a "
    "judge selecting the best-supported position (Du et al., 2023; Liang et al., 2023). The "
    "intuition behind MAD is straightforward: independent agents are unlikely to make the same "
    "mistake in the same way, so genuine disagreement between agents is a signal that at least "
    "one of them is wrong — and a structured debate can expose which. However, existing MAD "
    "systems suffer from a critical efficiency problem: they debate every query, regardless of "
    "wheather the agents actually disagree. When three agents independently retrieve the same "
    "fact and reach the same conclusion, running a full Propose-Critique-Revise-Judge cycle adds "
    "latency (typically 4–8 additional seconds) and 10–15 additional LLM calls with no benefit "
    "to answer quality."
)

body_para(
    "Evidence-MAD addresses this inefficiency through an evidence gate — a pairwise Natural "
    "Language Inference (NLI) layer that compares agent claims before deciding wheather to "
    "trigger debate. This gate evaluates whether any two agent outputs contradict each other; "
    "only when genuine disagreement is detected does the system proceed to conflict classification "
    "and the full debate cycle. When agents agree, the system returns a direct evidence-based "
    "answer. When evidence is insufficient or ambiguous, it transparently reports that state "
    "rather than fabricating confidence."
)

body_para(
    "A further innovation in this work is conflict-type classification: when debate is triggered, "
    "the system first classifies the nature of the disagreement into one of five categories — "
    "FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, or SOURCE. Each category recieves a distinct debate "
    "strategy. For instance, a TEMPORAL conflict triggers a strategy that instructs the proposer "
    "to check the dates of each claim and exclude any claim dated outside the query period, while "
    "a CONTEXTUAL conflict triggers a strategy that checks wheather the competing claims apply to "
    "different populations or platforms (which would dissolve the apparent contradiction rather "
    "than resolve it in favor of one claim)."
)

body_para(
    "The system integrates four independent agents: a Web Agent that searches DuckDuckGo, a "
    "Reference Agent that queries Wikipedia, a Scholarly Agent that queries the Crossref academic "
    "database, and an AI Answer Agent powered by Google Gemini with Search grounding. Evidence "
    "from the three search agents passes through a two-stage normalization pipeline before NLI "
    "comparison, ensuring that claims are clean, query-focused single sentences rather than "
    "raw noisy search snippets."
)

section_heading("1.2  Problem Statement")

body_para(
    "Given a natural language question and N independent retrieval agents, the core research "
    "problem addressed by this work can be stated as follows:"
)

body_para(
    "1. How do we determine — in a principled and computationally efficient way — wheather the "
    "agents' answers reflect genuine conflicting evidence rather than surface-level wording "
    "differences or retrieval noise?"
)

body_para(
    "2. How do we avoid the computational overhead of multi-agent debate when agents agree, while "
    "ensuring debate is triggered reliably when genuine disagreement exists?"
)

body_para(
    "3. When debate is warranted, how do we tailor the resolution strategy to the specific nature "
    "of the conflict to maximise the chance of resolving it correctly?"
)

body_para(
    "4. How do we handle edge cases that generic NLI models miss — such as entity-substitution "
    "conflicts (where one agent silently renames a requested entity) and explicit epistemic "
    "challenges (where one agent states that a fact cannot be verified while another provides an "
    "affirmative answer)?"
)

body_para(
    "The existing literature on multi-agent debate (Section 2.2) does not fully address questions "
    "2 and 3. Prior systems either always debate (incurring unnecessary cost) or use simple "
    "voting schemes (which lose the structured argumentation benefit). Evidence-MAD bridges this "
    "gap by inserting an NLI-based gate between retrieval and debate, and by enriching the debate "
    "with conflict-type-aware strategy injection."
)

section_heading("1.3  Objectives")

body_para("The objectives of this project are as follows:")

body_para(
    "1. To design and implement an evidence-triggered gating mechanism using pairwise NLI that "
    "determines wheather multi-agent debate is warranted for a given query."
)

body_para(
    "2. To develop a five-type conflict taxonomy (FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, SOURCE) "
    "and implement an LLM-based classifier that assigns incoming disagreements to one of these "
    "categories."
)

body_para(
    "3. To implement conflict-type-specific debate strategies that guide the Proposer, Critic, "
    "and Reviser roles in the debate lifecycle."
)

body_para(
    "4. To extend the NLI layer with three deterministic query-aware guards that handle failure "
    "modes known to be problematic for generic NLI models: entity substitution, explicit "
    "epistemic challenge, and target resolution mismatch."
)

body_para(
    "5. To build a complete, deployable system with a FastAPI REST backend, a browser-based "
    "frontend, and support for both offline (fixture) and live operating modes."
)

body_para(
    "6. To evaluate the system through a controlled ablation study comparing six system "
    "configurations and quantifying the contribution of each architectural component."
)

section_heading("1.4  Scope of the Project")

body_para(
    "The scope of this project is limited to open-domain factual question answering in the "
    "English language. The system retrieves information from publicly accessible web sources "
    "(DuckDuckGo, Wikipedia, Crossref) and uses the Google Gemini API for the AI answer agent. "
    "The evaluation is conducted on a controlled dataset of 15 samples covering five conflict "
    "types, which is acknowledged to be small and not statistically representative of all "
    "possible question types. The system is not a commercial product and is not intended for "
    "safety-critical applicatons such as medical diagnosis or legal advice."
)

body_para(
    "The scope explicitly excludes: full-page web content extraction (only search snippet "
    "titles and one-to-two sentence descriptions are used), reinforcement learning or any "
    "form of model training, and cross-lingual question answering. The NLI component supports "
    "two modes — LLM-backed NLI and a local HuggingFace transformer model — but the transformer "
    "model requires approximately 1.4 GB of disk space and is not suitable for serverless "
    "deployment without additional infrastructure."
)

section_heading("1.5  Organization of the Report")

body_para(
    "The remainder of this report is organised as follows. Chapter 2 presents a review of "
    "related work covering multi-agent debate systems, NLI models, evidence retrieval approaches, "
    "and conflict detection techniques, and identifies the specific research gap that this work "
    "addresses. Chapter 3 describes the overall system design and architecture. Chapter 4 "
    "details the agents layer including all four retrieval agents and their fallback mechanisms. "
    "Chapter 5 covers the evidence pipeline from raw retrieval through relevance filtering and "
    "LLM normalization to the aggregation decision. Chapter 6 discusses the NLI detectors and "
    "the three query-aware guards. Chapter 7 describes conflict classification. Chapter 8 "
    "presents the debate lifecycle including the Proposer, Critic, Reviser, and Judge. Chapter 9 "
    "covers the API, frontend, and deployment. Chapter 10 presents the evaluation framework and "
    "results. Chapter 11 concludes the report and outlines future work."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 2 – LITERATURE REVIEW
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(2, "LITERATURE REVIEW")

section_heading("2.1  Introduction")

body_para(
    "This chapter reviews the existing body of literature relevant to the research problem "
    "addressed in this project. The review is organized into four main areas: multi-agent "
    "systems and debate frameworks for LLMs, natural language inference models and their "
    "application to fact verification, evidence retrieval approches for open-domain QA, and "
    "conflict detection and classification in information retrieval. The chapter concludes by "
    "identifying the specific research gap that motivates the design of Evidence-MAD."
)

section_heading("2.2  Multi-Agent Systems and Debate")

body_para(
    "The use of multiple cooperating or competing agents to improve the quality of LLM outputs "
    "has gained significant attention since 2022. Society of Mind (Zhuge et al., 2023) proposed "
    "that complex reasoning tasks could be decomposed and assigned to specialized agents, whose "
    "outputs are then aggregated. AutoGen (Wu et al., 2023) introduced a framework for "
    "orchestrating conversations between multiple LLM-based agents, demonstrating improvements "
    "on coding and reasoning benchmarks. ChatEval (Chan et al., 2023) and similar systems "
    "proposed structured evaluation through multi-agent argument, where agents take on the roles "
    "of examiner and respondent."
)

body_para(
    "The work most directly relevant to this project is Du et al. (2023), who formally "
    "investigated multi-agent debate as a mechanism for improving factual accuracy. Their "
    "experiments on GSM8K and BioASQ showed that three agents debating over two rounds achieved "
    "higher accuracy than any single agent or ensemble approach. Critically, their system always "
    "debates every question — an approach that this project identifies as unnecessary when "
    "agents already agree. Liang et al. (2023) independently proposed a similar framework "
    "focused on reasoning tasks, achieving comparable results."
)

body_para(
    "Wang et al. (2023) studied self-consistency in chain-of-thought reasoning, showing that "
    "sampling multiple reasoning paths and aggregating them improves performance. While not a "
    "debate system per se, self-consistency shares the key insight that independent reasoning "
    "attempts reveal uncertainty. However, self-consistency uses majority voting rather than "
    "structured argumentation and does not distinguish between types of disagreement."
)

body_para(
    "Madaan et al. (2023) proposed Self-Refine, where a single model iteratively improves its "
    "outputs through critique and revision. While architecturally similar to the Propose-"
    "Critique-Revise loop in this project, Self-Refine uses a single model playing all roles "
    "and does not incorporate external evidence retrieval or NLI-based conflict detection. "
    "Shinn et al. (2023) extended this with Reflexion, which adds episodic memory for multi-"
    "step task completion."
)

body_para(
    "A key limitation shared by all the above systems is the absence of an evidence gate. "
    "They all trigger their iterative improvement or debate processes for every query, "
    "regardless of whether the initial responses agree. This means that for simple, "
    "unambiguous factual queries where all agents would naturally agree, these systems "
    "incur unnecessary computational cost. Evidence-MAD directly addresses this by "
    "conditioning debate on a detected disagreement signal."
)

add_table(
    ["System", "Year", "Evidence Gate", "Conflict Types", "Multi-Agent"],
    [
        ["Du et al. (MAD)", "2023", "No", "None", "Yes"],
        ["Liang et al.", "2023", "No", "None", "Yes"],
        ["Self-Refine", "2023", "No", "None", "Single"],
        ["AutoGen", "2023", "No", "None", "Yes"],
        ["ChatEval", "2023", "No", "None", "Yes"],
        ["Evidence-MAD (Ours)", "2025", "Yes (NLI)", "5 types", "Yes"],
    ],
    caption="Table 2.1: Summary of Related Work in Multi-Agent Debate Frameworks"
)

section_heading("2.3  Natural Language Inference")

body_para(
    "Natural Language Inference (NLI), also referred to as recognizing textual entailment (RTE), "
    "is the task of determining the directional relationship between a premise and a hypothesis: "
    "ENTAILMENT (the premise implies the hypothesis), CONTRADICTION (the premise contradicts the "
    "hypothesis), or NEUTRAL (neither) (Dagan et al., 2006; Bowman et al., 2015). The Stanford "
    "Natural Language Inference (SNLI) dataset (Bowman et al., 2015) and the Multi-NLI dataset "
    "(Williams et al., 2018) have become standard benchmarks for evaluating NLI systems."
)

body_para(
    "The introduction of transformer-based models fundamentally changed the NLI landscape. "
    "BERT (Devlin et al., 2019) achieved state-of-the-art results on MNLI by fine-tuning on the "
    "task, and subsequent models like RoBERTa (Liu et al., 2019) further improved performance. "
    "The model used in this project, ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli "
    "(Nie et al., 2020), is fine-tuned on five NLI datasets simultaneously — SNLI, MultiNLI, "
    "FEVER-NLI, and three rounds of Adversarial NLI (ANLI) — making it one of the most robust "
    "publicly available NLI models. The ANLI rounds specifically test adversarial robustness, "
    "which is relevant for handling the tricky entity-substitution cases described in Chapter 6."
)

body_para(
    "FEVER (Thorne et al., 2018) introduced NLI to the fact verification domain, requiring "
    "systems to classify Wikipedia claims as SUPPORTED, REFUTED, or NOT ENOUGH INFO against a "
    "retrieved evidence set. This is closely related to the evidence aggregation problem in "
    "this project, where agent claims must be classified as mutually supporting, contradicting, "
    "or inconclusive. However, FEVER uses a single curated evidence source (Wikipedia) rather "
    "than multiple heterogeneous retrieval agents."
)

body_para(
    "More recently, several works have explored using LLMs directly for NLI rather than "
    "fine-tuned discriminative models. Sanh et al. (2022) showed that instruction-tuned models "
    "like T5 can perform zero-shot NLI with reasonable accuracy. Wei et al. (2022) demonstrated "
    "that chain-of-thought prompting significantly improves LLM performance on reasoning-heavy "
    "NLI tasks. This project supports both approaches — a local transformer model and an "
    "LLM-backed NLI mode — allowing the system to trade off inference cost against deployment "
    "constraints."
)

add_table(
    ["Model", "Training Data", "Approach", "Key Strength"],
    [
        ["BERT-base", "MNLI", "Discriminative", "Fast inference"],
        ["RoBERTa-large", "SNLI+MNLI+FEVER+ANLI", "Discriminative", "High accuracy"],
        ["T5 (zero-shot)", "C4 + instruction", "Generative", "No fine-tune needed"],
        ["GPT-4 (prompted)", "OpenAI pre-training", "Generative", "Handles nuance"],
        ["LLMNLIDetector (Ours)", "Groq endpoint", "Prompted LLM", "Query-aware guards"],
    ],
    caption="Table 2.2: Comparison of NLI Approaches Relevant to This Work"
)

section_heading("2.4  Evidence Retrieval Approaches")

body_para(
    "Open-domain question answering systems broadly adopt one of two retrieval paradigms: "
    "dense retrieval (embedding-based similarity search over a pre-indexed corpus) and sparse "
    "retrieval (keyword-based search over live web or API sources). Dense retrieval approaches "
    "like DPR (Karpukhin et al., 2020) and RAG (Lewis et al., 2020) have become dominant in "
    "academic benchmarks because they allow precise semantic matching against large corpora. "
    "However, they require a pre-indexed vector database and cannot retrieve information "
    "published after the index was built."
)

body_para(
    "Evidence-MAD deliberately uses sparse, live retrieval via public APIs (DuckDuckGo, "
    "Wikipedia, Crossref) rather than a vector database. This choice reflects the project's "
    "focus on real-time, up-to-date information retrieval rather than static corpus search. "
    "The trade-off is that retrieved snippets are noisier and shorter than passages retrieved "
    "from a curated index, which is why the two-stage normalization pipeline (Section 5.3) "
    "is necessary."
)

body_para(
    "WebGPT (Nakano et al., 2021) explored LLM-assisted web browsing for open-domain QA, "
    "demonstrating that real web retrieval can produce better-grounded answers than parametric "
    "knowledge alone. The Perplexity.ai approach and the Google Search-grounded Gemini model "
    "used in this project's AI Answer Agent similarly combine neural language generation with "
    "live search. Gou et al. (2023) proposed CRITIC, where an LLM interactively validates its "
    "own claims using web search, iteratively refining the answer until retrieved evidence "
    "supports it. This is conceptually similar to the evidence normalization step in this "
    "project, where the LLM is asked to produce a claim that is consistent with retrieved "
    "snippets rather than its own parametric knowledge."
)

body_para(
    "CrossRef (Van Eck and Waltman, 2010) and PubMed are the standard sources for scholarly "
    "literature retrieval. The ScholarlyAgent in this project uses the Crossref REST API as its "
    "primary source, with DuckDuckGo as fallback, and is only activated for queries containing "
    "academic vocabulary. This selective routing avoids the overhead of academic search for "
    "general factual queries."
)

section_heading("2.5  Conflict Detection and Classification")

body_para(
    "Conflict detection between multiple information sources has been studied in the context "
    "of knowledge base population (Nakashole and Mitchell, 2014), claim verification (Popat "
    "et al., 2018), and document summarization (Falke et al., 2019). Nakashole and Mitchell "
    "proposed a typology of factual conflicts derived from analyzing conflicting statements "
    "in Freebase, identifying temporal conflicts (different time periods), definitional "
    "conflicts (different definitions of the same concept), and measurement conflicts "
    "(different numerical values). This taxonomy directly influenced the design of the "
    "five-type conflict classification in this project."
)

body_para(
    "Popat et al. (2018) addressed credibility-weighted conflict detection, where the "
    "reliability of sources modulates how seriously their claims are taken. The SOURCE "
    "conflict type in Evidence-MAD partially reflects this concern: when the primary "
    "source of disagreement is a difference in source authority (e.g., a blog post versus "
    "a peer-reviewed paper), the debate strategy specifically instructs agents to evaluate "
    "source provenance and credibility rather than just the content of the claims."
)

body_para(
    "The closest prior work to the conflict classification component of this project is "
    "Schuster et al. (2019), who trained a classifier to distinguish between linguistic "
    "phenomena that cause apparent contradiction (negation, antonymy, temporal reference, "
    "etc.) in NLI datasets. Their work was focused on understanding NLI errors rather than "
    "on improving downstream question answering, but the taxonomy they identified strongly "
    "overlaps with the FACTUAL, TEMPORAL, and CONTEXTUAL categories in this project."
)

body_para(
    "Pan et al. (2023) proposed FactScore, a fine-grained fact verification system that "
    "decomposes long-form LLM-generated text into atomic claims and verifies each one "
    "separately against Wikipedia. While FactScore operates at the claim level rather than "
    "the agent level, the idea of structuring verification around distinct atomic claims "
    "is reflected in the normalized single-sentence claim design of the EvidenceNormalizer "
    "in this project."
)

section_heading("2.6  Research Gap")

body_para(
    "The review above reveals a clear and significant research gap. Existing multi-agent "
    "debate systems (Du et al., 2023; Liang et al., 2023; Chan et al., 2023) consistently "
    "trigger the full debate pipeline for every query, regardless of wheather agents "
    "disagree. This approach incurs unnecessary computational overhead and does not take "
    "advantage of the signal provided by agent agreement. In contrast, NLI-based fact "
    "verification systems (Thorne et al., 2018; Pan et al., 2023) compare claims against "
    "evidence but do not use the NLI signal to gate a downstream debate process."
)

body_para(
    "Furthermore, no existing multi-agent debate framework classifies the type of conflict "
    "before debate and adjusts the debate strategy accordingly. This is a significant "
    "limitation because the resolution strategy that works for a TEMPORAL conflict (check "
    "the dates) is qualitatively different from the strategy that works for a CONTEXTUAL "
    "conflict (check wheather the scopes are different populations) or a SOURCE conflict "
    "(evaluate source authority). A generic debate strategy applied indiscriminately to "
    "all conflict types is likely to produce less accurate resolutions for type-specific "
    "conflicts."
)

body_para(
    "Additionally, no prior work specifically addresses the query-aware NLI guard problem — "
    "the failure mode where generic NLI models return NEUTRAL for claim pairs that are "
    "genuinely contradictory because of entity substitution or explicit epistemic "
    "challenge. This project introduces three deterministic guards that preempt model "
    "inference for these cases, providing a reliable safety net that does not depend on "
    "the quality of the underlying NLI model."
)

body_para(
    "In summary, Evidence-MAD fills the following gaps: (1) evidence-triggered gating to "
    "avoid unnecessary debate; (2) conflict-type classification with type-specific strategies; "
    "and (3) query-aware NLI guards for entity-level conflicts. These three contributions "
    "together constitute the novel technical contribution of this work."
)

page_break()
print("Part 3 (Chapters 1-2) done.")
