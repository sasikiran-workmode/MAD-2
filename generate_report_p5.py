"""Part 5: Chapters 6–8: NLI, Conflict Classification, Debate Lifecycle"""

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 6 – NLI AND CONFLICT DETECTION
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(6, "NLI AND CONFLICT DETECTION")

section_heading("6.1  NLI Detector Classes")

body_para(
    "The NLI layer in Evidence-MAD is implemented through three distinct detector classes "
    "in evidence/disagreement_detector.py, each intended for a different runtime environment. "
    "All three classes expose the same interface: a predict_for_query(query, premise, "
    "hypothesis) method that returns a PairwiseRelation object with label, contradiction_score, "
    "entailment_score, and neutral_score fields."
)

body_para(
    "MockNLIDetector is used in FIXTURE mode. It performs exact-match lookup in a fixture "
    "table keyed by (premise, hypothesis) pair identifiers. When no fixture entry exists for "
    "a pair, it falls back to the _pattern_predict() method. MockNLIDetector never calls "
    "any LLM or model, ensuring FIXTURE mode is fully offline."
)

body_para(
    "LLMNLIDetector is used in LIVE mode with NLI_MODE=mock (the default). Despite the "
    "confusing name (it is called mock because it mocks the transformer model), this detector "
    "uses the real LLM endpoint (Groq/OpenAI-compatible) to perform NLI. It sends a "
    "structured prompt that includes the original query, claim A, and claim B, and instructs "
    "the model to return JSON with label and score fields. On LLM failure, it falls back to "
    "_pattern_predict()."
)

body_para(
    "NLIDetector is used in LIVE mode with NLI_MODE=transformers. It loads the "
    "ynie/roberta-large-snli_mnli_fever_anli_R1_R2_R3-nli model via the HuggingFace "
    "transformers library and runs bidirectional inference: once with claim A as premise "
    "and claim B as hypothesis, and once in reverse. The final scores use the maximum "
    "of both contradiction scores and the minimum of both entailment scores, implementing "
    "a conservative aggregation that is sensitive to asymmetric contradictions."
)

add_table(
    ["Class", "Mode", "Backend", "Fallback"],
    [
        ["MockNLIDetector", "FIXTURE", "Fixture table", "_pattern_predict()"],
        ["LLMNLIDetector", "LIVE + NLI_MODE=mock", "LLM (Groq)", "_pattern_predict()"],
        ["NLIDetector", "LIVE + NLI_MODE=transformers", "HuggingFace RoBERTa", "None (raises)"],
    ],
    caption="Table 6.1: NLI Detector Class Comparison"
)

section_heading("6.2  Query-Aware Guard Chain")

body_para(
    "Before any NLI model is consulted, all three detector classes apply a chain of three "
    "deterministic query-aware guards. These guards are implemented as regular expression "
    "pattern matchers that detect specific semantic failure modes known to be problematic "
    "for generic NLI models. If any guard fires, its result is returned immediately without "
    "calling the NLI model, ensuring consistent behavior regardless of which detector "
    "class is being used."
)

body_para(
    "The guards are applied in sequence: first the entity substitution guard, then the "
    "explicit challenge guard, then the target resolution guard. Only if all three guards "
    "fail to fire does the system proceed to model-based NLI inference. This ordering "
    "reflects the specificity of the guards: entity substitution is the most specific "
    "(requires a paper-naming pattern), explicit challenge is broader (any epistemic "
    "rejection vs. affirmative answer), and target resolution is the most sophisticated "
    "(requires cross-claim entity comparison)."
)

section_heading("6.3  Entity Substitution Guard")

body_para(
    "The entity substitution guard detects the following pattern: one claim names a paper "
    "(or other published work) using a title in quotation marks, and another claim contains "
    "language explicitly rejecting the existence of such a paper. This handles cases where "
    "a search agent returns results for a similarly titled paper (an autocorrection), while "
    "the AI Answer Agent correctly reports that the specifically queried paper does not exist."
)

body_para(
    "The guard uses two regular expressions. The rejection pattern matches phrases like "
    "no such paper exists, does not exist, no record of the paper, cannot find the "
    "article, and similar variants. The work-naming pattern matches phrases like paper "
    "titled followed by a quoted string, or publication titled, article titled, and "
    "similar. If the rejection pattern fires in one claim and the work-naming pattern "
    "fires in the other, the guard returns CONTRADICTION with a confidence score of 0.91."
)

body_para(
    "The 0.91 score was chosen to be above the DISAGREEMENT_THRESHOLD of 0.70 (ensuring "
    "debate is triggered) but below 1.0 (acknowledging that the guard is heuristic and "
    "can occasionally fire incorrectly). The guard is asymmetric: it fires only when one "
    "claim contains a rejection and the other contains a positive work identification, "
    "not when both claims contain rejections (which would be agreement on nonexistence)."
)

section_heading("6.4  Explicit Challenge Guard")

body_para(
    "The explicit challenge guard is the most general of the three guards. Its rule is "
    "domain-independent: if one agent explicitly states that the requested fact cannot "
    "be verified, has no reliable support, or does not exist, and another agent provides "
    "an affirmative answer about that same subject, the two claims are in contradiction."
)

body_para(
    "The challenge pattern matches a broad set of epistemic rejection phrases including: "
    "no record, no known record, no official record, does not exist, doesn't exist, "
    "cannot verify, can't verify, unable to verify, unverified, unsupported, "
    "unsubstantiated, nonexistent, not verified, not verifiable, not supported, and "
    "not documented. A secondary guard ensures that the challenging claim contains at "
    "least one content word from the original query (or a deictic pronoun like it or "
    "this), preventing stray disclaimers in unrelated text from triggering the gate."
)

body_para(
    "This guard is important because LLMs sometimes express uncertainty by saying a fact "
    "is unverifiable, while a search engine returns a page that does happen to mention "
    "the queried topic (even if the information is unreliable). Without this guard, a "
    "generic NLI model might rate the affirmative and the epistemic rejection as NEUTRAL "
    "because their surface-level wording is very different. The guard ensures these "
    "cases reliably trigger debate, which is the correct behavior: the judge can then "
    "weigh the source quality of the affirmative answer."
)

section_heading("6.5  Target Resolution Guard")

body_para(
    "The target resolution guard handles the most sophisticated failure mode: the case "
    "where one agent rejects the queried entity by name (e.g., no known paper titled "
    "Wipro is All U Need) while another agent positively identifies a different but "
    "similarly named entity (e.g., the paper Attention is All You Need was published "
    "in 2017). A generic NLI model might call these two claims ENTAILING because they "
    "share a year and are both about machine learning papers, missing the fact that "
    "they refer to completely different entities."
)

body_para(
    "The guard normalizes the query string and the claims to lowercase alphanumeric tokens, "
    "then extracts rejected titles (titles appearing after phrases like no known paper "
    "titled) and positively asserted titles (quoted titles in claims that do not contain "
    "rejection language). If a rejected title overlaps with the query (indicating the "
    "rejection is about the queried entity) and a positively asserted title differs from "
    "the rejected title, the guard returns CONTRADICTION with confidence 0.93 — slightly "
    "higher than the entity substitution guard because target resolution checks are more "
    "precise."
)

section_heading("6.6  Transformer-Based NLI")

body_para(
    "When NLI_MODE=transformers, the NLIDetector class loads the HuggingFace pipeline "
    "for text-classification using the ynie/roberta-large model. This model is a "
    "RoBERTa-large architecture fine-tuned on five NLI benchmarks: SNLI (Bowman et al., "
    "2015), MultiNLI (Williams et al., 2018), FEVER-NLI (Thorne et al., 2018), and "
    "three rounds of Adversarial NLI (Nie et al., 2020). The combined fine-tuning "
    "makes it significantly more robust to adversarial examples than models fine-tuned "
    "on a single dataset."
)

body_para(
    "The pipeline uses top_k=None to return scores for all three labels (ENTAILMENT, "
    "NEUTRAL, CONTRADICTION) rather than just the top-scoring label. This is important "
    "because the aggregator needs all three scores to compute the DISAGREEMENT and "
    "AGREEMENT thresholds. The input format uses the HuggingFace NLI convention of "
    "separate text and text_pair fields, which correctly inserts the separator token "
    "between premise and hypothesis according to the model's fine-tuning format."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 7 – CONFLICT CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(7, "CONFLICT CLASSIFICATION")

section_heading("7.1  Conflict Classifier")

body_para(
    "Once the EvidenceAggregator returns an DISAGREEMENT decision, the ConflictClassifier "
    "(conflict/classifier.py) determines the type of the conflict. The classifier receives "
    "the texts of the two most contradicting claims and the original query, and returns a "
    "ClassificationResult containing the conflict type, a confidence score, an explanation, "
    "and a ComponentStatus indicating wheather the LLM succeeded or the pattern fallback "
    "was used."
)

body_para(
    "The ComponentStatus field is especially valuable for evaluation. By tracking wheather "
    "each classification was done by the LLM or the pattern fallback, the evaluation "
    "framework can separately measure LLM classification accuracy and pattern fallback "
    "accuracy. If the LLM API is consistently unavailable during an evaluation run, all "
    "classifications fall back to pattern matching, and the results are therefore not "
    "comparable to a run where the LLM was available. ComponentStatus makes this "
    "difference transparent rather than hidden."
)

section_heading("7.2  Five-Type Taxonomy")

body_para(
    "The five conflict types were designed to cover the most common classes of factual "
    "disagreement encountered in open-domain question answering. The taxonomy was "
    "developed by analyzing existing literature (Nakashole and Mitchell, 2014; Schuster "
    "et al., 2019) and by iterating on the types of conflicts produced during system "
    "testing. Table 7.1 summarizes each type with its definition and a representative "
    "example."
)

add_table(
    ["Conflict Type", "Definition", "Example"],
    [
        ["FACTUAL", "Mutually incompatible factual claims at same time/context",
         "Agent A: water boils at 100°C. Agent B: water boils at 212°F at sea level"],
        ["TEMPORAL", "Claims differ because they refer to different time points",
         "Agent A: policy enacted in 2019. Agent B: policy enacted in 2020"],
        ["VERSION", "Claims refer to different software/document versions",
         "Agent A: Python 3.10 supports match. Agent B: Python 3.9 does not"],
        ["CONTEXTUAL", "Claims differ due to different conditions/populations",
         "Agent A: drug effective for adults. Agent B: drug not effective for children"],
        ["SOURCE", "Disagreement driven by source authority/reliability difference",
         "Agent A (blog): supplements cure disease. Agent B (journal): no evidence found"],
    ],
    caption="Table 7.1: Conflict Type Definitions and Representative Examples"
)

body_para(
    "The LLM classifier receives a prompt with these definitions and is asked to classify "
    "the conflict between the two provided claims. The prompt includes examples for each "
    "type to provide in-context guidance. The LLM returns a JSON response with a type "
    "field (one of the five types or UNKNOWN) and a confidence field. If the LLM returns "
    "UNKNOWN or a confidence below 0.5, the system proceeds to the pattern-based fallback "
    "rather than accepting the classification."
)

section_heading("7.3  Pattern-Based Fallback")

body_para(
    "The pattern-based fallback for conflict classification uses a rule hierarchy applied "
    "in order. First, the system checks for VERSION: if both claims contain version number "
    "patterns (e.g., v3.10, Python 3.13, v2) that are different, the conflict is VERSION. "
    "Second, if both claims contain different year strings (four-digit numbers), the "
    "conflict is TEMPORAL. Third, if claims mention population or platform qualifiers from "
    "hardcoded groups (adults vs. children, macOS vs. Windows, safe vs. dangerous), the "
    "conflict is CONTEXTUAL. Fourth, if claims contain source quality indicators "
    "(blog vs. paper, unofficial vs. official, unverified vs. peer-reviewed), the "
    "conflict is SOURCE. If none of the above rules fire, the default classification "
    "is FACTUAL — a reasonable default since raw factual disagreements are the most "
    "common case."
)

body_para(
    "The pattern fallback is intentionally conservative: it will misclassify some "
    "conflicts (particularly edge cases at the boundary between types) but has very low "
    "false positive rates for the types it can reliably detect (TEMPORAL and VERSION in "
    "particular). The ComponentStatus field in the ClassificationResult allows the "
    "evaluation framework to measure the gap in classification accuracy between the LLM "
    "path and the fallback path."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CHAPTER 8 – DEBATE LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════
chapter_heading(8, "DEBATE LIFECYCLE")

section_heading("8.1  Debate Manager")

body_para(
    "The DebateManager (debate/manager.py) orchestrates the iterative Propose-Critique-"
    "Revise cycle. Its run_debate() method takes the classified conflict, the two "
    "conflicting claims, the original query, and the agent evidence as inputs. It runs "
    "for up to MAX_DEBATE_ROUNDS iterations (default 3), checking for early stop "
    "conditions after each stage."
)

body_para(
    "Each round of the debate produces a DebateRound object containing the proposer, "
    "critic, and reviser arguments. Arguments are stored as DebateArgument objects with "
    "fields for round number, role, content, evidence references, conflict type, "
    "strategy used, and a 200-character preview of the strategy text. The strategy text "
    "preview is stored in the trace file for debugging, allowing analysts to verify "
    "that the correct conflict-type strategy was injected into the proposer's prompt."
)

body_para(
    "The DebateManager handles LLM failures gracefully. If any stage (Proposer, Critic, "
    "or Reviser) raises an LLMError, the debate stops immediately. If the failure occurs "
    "in round 1, the debate status is set to failed. If it occurs in a later round, "
    "the status is partial. In either case, failed_stages records which stages failed. "
    "The Judge is only called if debate status is completed — it is never called on a "
    "failed or partial debate, preventing the system from generating a spurious verdict "
    "from an incomplete argument."
)

section_heading("8.2  Proposer")

body_para(
    "The Proposer (debate/proposer.py) generates the initial position in each debate "
    "round. Its prompt is the most complex in the system because it must incorporate "
    "the conflict-type-specific strategy alongside the claim information. The proposer "
    "receives the original query, claim A text, claim B text, and the conflict type, "
    "and is expected to produce a structured argument with five sections: POSITION, "
    "EVIDENCE REVIEW, REASONING, SOURCE BASIS, and CONCLUSION."
)

body_para(
    "The strategy text injected into the proposer's prompt varies by conflict type. For "
    "TEMPORAL conflicts, the strategy instructs the proposer to check the recorded date "
    "of each claim and exclude claims dated outside the query period. For VERSION "
    "conflicts, it instructs the proposer to check wheather the two claims refer to the "
    "same version and to report both claims as correct-for-their-version if they do not. "
    "For CONTEXTUAL conflicts, the strategy focuses on wheather the competing claims "
    "apply to different populations or platforms, potentially dissolving the contradiction "
    "rather than resolving it in favor of one side."
)

body_para(
    "The Proposer also receives metadata extracted from the normalized claims. For TEMPORAL "
    "conflicts, it receives the date field from each NormalizedClaim and a QUERY PERIOD "
    "field extracted from the original query if a year is present. For VERSION conflicts, "
    "it receives the version field from each claim. For CONTEXTUAL conflicts, it receives "
    "the scope field. This metadata enrichment allows the proposer to make specific, "
    "evidence-grounded arguments rather than generic position statements."
)

body_para(
    "The is_valid_argument() function validates the proposer's output before it proceeds "
    "to the critic. It rejects arguments shorter than 50 characters and arguments "
    "beginning with Demo response. This validation prevents trivially short or obviously "
    "canned LLM responses from entering the debate, which would defeat the purpose of "
    "the structured argumentation."
)

section_heading("8.3  Critic")

body_para(
    "The Critic (debate/critic.py) receives the proposer's argument and must evaluate "
    "it on the basis of the evidence. It has two possible outputs. If the proposer's "
    "argument is well-reasoned and well-supported by the evidence, the critic signals "
    "early stop by including the string SUBSTANTIVE_OBJECTION: false in its response. "
    "Otherwise, the critic formulates a substantive objection identifying specific "
    "problems with the proposer's reasoning or evidence references."
)

body_para(
    "The no_objection early-stop check uses a case-insensitive regex match for "
    "SUBSTANTIVE_OBJECTION: false in the critic's content. It also checks the "
    "strategy_used field of the DebateArgument for the same string. If either location "
    "contains the stop signal, the debate ends with stop_reason=no_objection and "
    "status=completed. The judge is then called immediately to select a winner from the "
    "proposer's unchallenged argument."
)

body_para(
    "The no_objection path is particularly important for debates where the proposer "
    "correctly identifies that the conflict dissolves upon inspection — for example, "
    "a CONTEXTUAL conflict where the two claims actually refer to different populations "
    "and both are correct in their respective scopes. In such cases, a reasonable "
    "critic would agree with the proposer's dissolution finding, triggering early stop "
    "rather than forcing an unnecessary additional round."
)

section_heading("8.4  Reviser and Early Stopping")

body_para(
    "The Reviser (debate/reviser.py) synthesizes the proposer's position and the critic's "
    "objections into a refined argument. It receives the full debate context from all "
    "previous rounds and is expected to produce an argument that addresses the critic's "
    "concerns while maintaining the best-supported position from the available evidence."
)

body_para(
    "After the Reviser produces its output, the DebateManager checks for convergence "
    "using Jaccard similarity between the current revision and the previous revision "
    "(from the previous round's reviser, if any). Jaccard similarity is computed over "
    "word sets: the intersection of word tokens divided by the union. If the score is "
    "0.95 or higher, the revision is considered converged with the previous round and "
    "debate stops with stop_reason=converged."
)

body_para(
    "The 0.95 threshold is intentionally strict. Two arguments sharing 95% of their "
    "word tokens are essentially the same argument with minor phrasing differences. "
    "Running additional debate rounds on such arguments would not produce meaningful "
    "improvements in resolution quality. The strict threshold ensures that convergence "
    "only fires when the debate has genuinely plateaued, not when two rounds happen "
    "to share common vocabulary."
)

add_table(
    ["Stop Reason", "Condition", "Debate Status"],
    [
        ["converged", "Jaccard(revision_n, revision_{n-1}) ≥ 0.95", "completed"],
        ["no_objection", "Critic returns SUBSTANTIVE_OBJECTION: false", "completed"],
        ["max_rounds", "MAX_DEBATE_ROUNDS iterations completed", "completed"],
        ["stage_failure", "Proposer/Critic/Reviser raises LLMError", "failed / partial"],
    ],
    caption="Table 8.1: Debate Stop Reason Summary"
)

section_heading("8.5  Judge")

body_para(
    "The Judge (debate/judge.py) is called only when debate_outcome.status == completed. "
    "It receives the full debate transcript (all rounds with proposer, critic, and reviser "
    "arguments), structured claim information (text, date, version, scope, source URL) "
    "for both conflicting claims, and the conflict type. It produces a JudgeResult with "
    "a winner (candidate_1 or candidate_2), evidence score, source score, reasoning "
    "score, and overall confidence."
)

body_para(
    "The Judge's prompt explicitly instructs it to prioritize evidence quality over "
    "rhetorical skill. A well-argued position supported by a low-quality source should "
    "lose to a less elegant argument supported by a primary, authoritative source. The "
    "three separate scores (evidence, source, reasoning) allow the evaluation framework "
    "to analyze which dimension most influenced the judge's decision across the evaluation "
    "dataset."
)

body_para(
    "A critical design decision is that the Judge never fabricates a verdict. If the "
    "Judge's LLM call fails, judge_result is set to None. The AnswerGenerator detects "
    "this condition and generates an unresolved conflict answer rather than claiming a "
    "winner. This prevents the system from presenting a hallucinated verdict to the user "
    "as if it were a real evaluated result. A null judge_result is always surfaced "
    "explicitly in the response rather than silently substituted with a default value."
)

page_break()
print("Part 5 (Chapters 6-8) done.")
