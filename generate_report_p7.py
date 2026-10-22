"""Part 7: References (30+) and Appendices"""

# ══════════════════════════════════════════════════════════════════════════════
# REFERENCES
# ══════════════════════════════════════════════════════════════════════════════
heading_para("REFERENCES", 16, bold=True, caps=True, underline=False, align=WD_ALIGN_PARAGRAPH.CENTER)

refs = [
    "[1]. Bowman, S. R., Angeli, G., Potts, C., & Manning, C. D. (2015). A large annotated corpus for learning "
    "natural language inference. Proceedings of the 2015 Conference on Empirical Methods in Natural Language "
    "Processing (EMNLP), 632–642. Association for Computational Linguistics.",

    "[2]. Brown, T., Mann, B., Ryder, N., Subbiah, M., Kaplan, J. D., Dhariwal, P., … Amodei, D. (2020). "
    "Language models are few-shot learners. Advances in Neural Information Processing Systems, 33, 1877–1901.",

    "[3]. Chan, C.-M., Chen, W., Su, Y., Yu, J., Xue, W., Zhang, S., … Liu, Z. (2023). ChatEval: Towards "
    "better LLM-based evaluators through multi-agent debate. arXiv preprint arXiv:2308.07201.",

    "[4]. Dagan, I., Glickman, O., & Magnini, B. (2006). The PASCAL recognising textual entailment challenge. "
    "In Machine Learning Challenges. Lecture Notes in Computer Science, Vol. 3944. Springer, Berlin, Heidelberg, "
    "pp. 177–190.",

    "[5]. Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of deep bidirectional "
    "transformers for language understanding. Proceedings of NAACL-HLT 2019, 4171–4186.",

    "[6]. Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2023). Improving factuality and "
    "reasoning in language models through multiagent debate. arXiv preprint arXiv:2305.14325.",

    "[7]. Falke, T., Ribeiro, L. F. R., Utama, P. A., Dagan, I., & Gurevych, I. (2019). Ranking generated "
    "summaries by correctness: An interesting but challenging application for natural language inference. "
    "Proceedings of ACL 2019, 2214–2220.",

    "[8]. Gou, Z., Shao, Z., Gong, Y., Shen, Y., Yang, Y., Duan, N., & Chen, W. (2023). CRITIC: Large language "
    "models can self-correct with tool-interactive critiquing. arXiv preprint arXiv:2305.11738.",

    "[9]. Ji, Z., Lee, N., Frieske, R., Yu, T., Su, D., Xu, Y., … Fung, P. (2023). Survey of hallucination "
    "in natural language generation. ACM Computing Surveys, 55(12), 1–38.",

    "[10]. Karpukhin, V., Oguz, B., Min, S., Lewis, P., Wu, L., Edunov, S., … Yih, W.-t. (2020). Dense passage "
    "retrieval for open-domain question answering. Proceedings of EMNLP 2020, 6769–6781.",

    "[11]. Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., … Kiela, D. (2020). "
    "Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information "
    "Processing Systems, 33, 9459–9474.",

    "[12]. Liang, T., He, Z., Jiao, W., Wang, X., Wang, Y., Wang, R., … Shi, S. (2023). Encouraging divergent "
    "thinking in large language models through multi-agent debate. arXiv preprint arXiv:2305.19118.",

    "[13]. Liu, Y., Ott, M., Goyal, N., Du, J., Joshi, M., Chen, D., … Stoyanov, V. (2019). RoBERTa: A "
    "robustly optimized BERT pretraining approach. arXiv preprint arXiv:1907.11692.",

    "[14]. Madaan, A., Tandon, N., Gupta, P., Hallinan, S., Gao, L., Wiegreffe, S., … Clark, P. (2023). "
    "Self-Refine: Iterative refinement with self-feedback. Advances in Neural Information Processing "
    "Systems, 36, 46534–46594.",

    "[15]. Nakano, R., Hilton, J., Balwit, A., Wu, J., Ouyang, L., Kim, C., … Schulman, J. (2021). WebGPT: "
    "Browser-assisted question-answering with human feedback. arXiv preprint arXiv:2112.09332.",

    "[16]. Nakashole, N., & Mitchell, T. (2014). Language-aware truth assessment of fact candidates. "
    "Proceedings of ACL 2014, 1009–1019.",

    "[17]. Nie, Y., Williams, A., Dinan, E., Bansal, M., Weston, J., & Kiela, D. (2020). Adversarial NLI: "
    "A new benchmark for natural language understanding. Proceedings of ACL 2020, 4885–4901.",

    "[18]. Pan, S., Luo, L., Wang, Y., Chen, C., Wang, J., & Wu, X. (2023). Unifying large language models "
    "and knowledge graphs: A roadmap. IEEE Transactions on Knowledge and Data Engineering, 36(7), 3580–3599.",

    "[19]. Pan, X., Gao, T., & Chen, D. (2023). FactScore: Fine-grained atomic evaluation of factual precision "
    "in long form text generation. Proceedings of EMNLP 2023, 12076–12100.",

    "[20]. Popat, K., Mukherjee, S., Yates, A., & Weikum, G. (2018). DeClarE: Debunking fake news and false "
    "claims using evidence-aware deep learning. Proceedings of EMNLP 2018, 22–32.",

    "[21]. Sanh, V., Webson, A., Raffel, C., Bach, S., Sutawika, L., Alyafeai, Z., … Rush, A. M. (2022). "
    "Multitask prompted training enables zero-shot task generalization. Proceedings of ICLR 2022.",

    "[22]. Schuster, T., Shah, D., Yeo, Y. J. S., Filizzola, D., Alfonseca, E., & Barzilay, R. (2019). "
    "Towards debiasing fact verification models. Proceedings of EMNLP 2019, 3417–3423.",

    "[23]. Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K. R., & Yao, S. (2023). Reflexion: Language "
    "agents with verbal reinforcement learning. Advances in Neural Information Processing Systems, 36, "
    "8634–8652.",

    "[24]. Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A large-scale "
    "dataset for fact extraction and verification. Proceedings of NAACL 2018, 809–819.",

    "[25]. Touvron, H., Lavril, T., Izacard, G., Martinet, X., Lachaux, M.-A., Lacroix, T., … Lample, G. "
    "(2023). LLaMA: Open and efficient foundation language models. arXiv preprint arXiv:2302.13971.",

    "[26]. Van Eck, N. J., & Waltman, L. (2010). Software survey: VOSviewer, a computer program for "
    "bibliometric mapping. Scientometrics, 84(2), 523–538.",

    "[27]. Wang, X., Wei, J., Schuurmans, D., Le, Q., Chi, E., Narang, S., … Zhou, D. (2023). Self-"
    "consistency improves chain of thought reasoning in language models. Proceedings of ICLR 2023.",

    "[28]. Wei, J., Wang, X., Schuurmans, D., Bosma, M., Xia, F., Chi, E., … Zhou, D. (2022). Chain-of-"
    "thought prompting elicits reasoning in large language models. Advances in Neural Information "
    "Processing Systems, 35, 24824–24837.",

    "[29]. Williams, A., Nangia, N., & Bowman, S. R. (2018). A broad-coverage challenge corpus for sentence "
    "understanding through inference. Proceedings of NAACL 2018, 1112–1122.",

    "[30]. Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., … Wang, C. (2023). AutoGen: Enabling "
    "next-gen LLM applications via multi-agent conversation. arXiv preprint arXiv:2308.08155.",

    "[31]. Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: "
    "Synergizing reasoning and acting in language models. Proceedings of ICLR 2023.",

    "[32]. Zhang, S., Roller, S., Goyal, N., Artetxe, M., Chen, M., Chen, S., … Zettlemoyer, L. (2022). "
    "OPT: Open pre-trained transformer language models. arXiv preprint arXiv:2205.01068.",

    "[33]. Zhuge, M., Liu, H., Faccio, F., Drake, D., Janik, T., Anand, A., … Schmidhuber, J. (2023). "
    "Mindstorms in natural language-based societies of mind. arXiv preprint arXiv:2305.17066.",

    "[34]. Gao, L., Biderman, S., Black, S., Golding, L., Hoppe, T., Foster, C., … Leahy, C. (2020). "
    "The Pile: An 800 GB dataset of diverse text for language modeling. arXiv preprint arXiv:2101.00027.",

    "[35]. Peng, B., Li, C., He, P., Galley, M., & Gao, J. (2023). Instruction tuning with GPT-4. "
    "arXiv preprint arXiv:2304.03277.",
]

for ref in refs:
    p = doc.add_paragraph()
    run = p.add_run(ref)
    run.font.name = "Times New Roman"; run.font.size = Pt(12)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(18)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX 1 – System Requirements and Installation
# ══════════════════════════════════════════════════════════════════════════════
heading_para("APPENDICES", 16, bold=True, caps=True, underline=False, align=WD_ALIGN_PARAGRAPH.CENTER)

heading_para("Appendix 1: System Requirements and Installation Guide", 14, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT)

body_para(
    "This appendix provides the complete system requirements and step-by-step installation "
    "instructions for running Evidence-MAD locally."
)

subsection_heading("Hardware and Software Requirements")

body_para(
    "Operating System: Linux, macOS, or Windows 10/11. Python: version 3.10 or newer "
    "(required for structural pattern matching syntax). RAM: minimum 4 GB for LLM-backed NLI "
    "mode; minimum 8 GB recommended for transformer NLI mode (RoBERTa-large requires "
    "approximately 3 GB at inference). Disk: minimum 2 GB free (additional 1.4 GB for "
    "HuggingFace model download if NLI_MODE=transformers). Internet access is required "
    "for all live-mode operations."
)

subsection_heading("Installation Steps")

body_para("Step 1: Clone the repository and navigate to the project directory.")

p = doc.add_paragraph()
run = p.add_run("    git clone <repository_url>\n    cd MAD-2")
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

body_para("Step 2: Create and activate a Python virtual environment.")

p = doc.add_paragraph()
run = p.add_run("    python -m venv venv\n    source venv/bin/activate  # Windows: venv\\Scripts\\Activate.ps1")
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

body_para("Step 3: Install dependencies from the pinned requirements file.")

p = doc.add_paragraph()
run = p.add_run("    pip install --upgrade pip\n    pip install -r requirements.txt")
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

body_para("Step 4: Copy the environment template and fill in API keys.")

p = doc.add_paragraph()
run = p.add_run("    cp .env.example .env\n    # Edit .env and set LLM_API_KEY and GEMINI_API_KEY")
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

body_para("Step 5: Start the system using the provided startup script.")

p = doc.add_paragraph()
run = p.add_run("    chmod +x start_mad.sh\n    ./start_mad.sh")
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

body_para(
    "After startup, the frontend is accessible at http://localhost:3000 and the API "
    "documentation at http://127.0.0.1:8000/docs. To run in offline fixture mode without "
    "any API keys, set DEMO_MODE=true in the .env file before starting."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX 2 – Fixture Dataset Reference
# ══════════════════════════════════════════════════════════════════════════════
heading_para("Appendix 2: Fixture Dataset Reference", 14, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)

body_para(
    "The fixture dataset (data/fixtures.json) contains 10 required test cases that must "
    "be present for the system to start in FIXTURE mode. Each case is referenced by its ID "
    "in unit tests and the CLI demo. Table A2.1 summarizes the required fixture cases."
)

add_table(
    ["Fixture ID", "Query (summary)", "Expected Evidence State", "Conflict Type"],
    [
        ["agree_capital", "Capital of Australia?", "AGREEMENT", "None"],
        ["factual_boiling", "Boiling point of water?", "AGREEMENT", "None"],
        ["temporal_policy", "When was India's NEP introduced?", "DISAGREEMENT", "TEMPORAL"],
        ["version_python", "What version supports feature X?", "DISAGREEMENT", "VERSION"],
        ["contextual_drug", "Is the drug effective?", "DISAGREEMENT", "CONTEXTUAL"],
        ["source_blog_vs_paper", "What does the research say?", "DISAGREEMENT", "SOURCE"],
        ["unrelated_evidence", "Unrelated query", "UNCERTAIN", "None"],
        ["one_agent_fails", "One agent fails", "INSUFFICIENT", "None"],
        ["two_agents_fail", "Two agents fail", "INSUFFICIENT", "None"],
        ["all_agents_fail", "All agents fail", "INSUFFICIENT", "None"],
    ],
    caption="Table A2.1: Required Fixture Cases in data/fixtures.json"
)

body_para(
    "Each fixture case in fixtures.json has the following structure: a unique id string, "
    "a query string (used for exact-match lookup by FixtureStore), an agents dictionary "
    "mapping agent_id to evidence status and claim fields, expected_state, "
    "expected_conflict_type, expected_debate boolean, expected_answer, required_facts "
    "list, and forbidden_facts list. The required_facts and forbidden_facts are token "
    "lists used by the evaluation MetricsCalculator to score answer quality."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX 3 – API Endpoint Reference
# ══════════════════════════════════════════════════════════════════════════════
heading_para("Appendix 3: API Endpoint Reference", 14, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)

body_para(
    "This appendix documents all REST API endpoints exposed by the Evidence-MAD FastAPI "
    "server running on port 8000."
)

subsection_heading("GET /")

body_para(
    "Returns basic system information. Response body: {\"name\": \"Evidence-MAD API\", "
    "\"version\": \"2.0.0\", \"status\": \"running\"}. No authentication required."
)

subsection_heading("GET /health")

body_para(
    "Health check endpoint. Returns HTTP 200 with body {\"status\": \"healthy\"} if the "
    "server is running. Used by load balancers and monitoring tools."
)

subsection_heading("POST /api/solve")

body_para(
    "Main query endpoint. Accepts a JSON body with two fields: query (string, required) "
    "and demo_mode (boolean, optional, defaults to false). Returns the full solve result "
    "as described in Table 9.1. Typical response time: 2–3 seconds for AGREEMENT queries "
    "in live mode; 4–8 seconds for DISAGREEMENT queries with full debate; sub-second for "
    "all queries in FIXTURE mode."
)

body_para("Example request (fixture mode):")

p = doc.add_paragraph()
run = p.add_run(
    '    curl -X POST http://127.0.0.1:8000/api/solve \\\n'
    '      -H "Content-Type: application/json" \\\n'
    '      -d \'{"query":"When was India\'s National Education Policy introduced?","demo_mode":true}\''
)
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

subsection_heading("POST /solve")

body_para(
    "Alias of POST /api/solve. Maintained for backward compatibility with clients that "
    "used the earlier v1 API path. Identical behavior and response format."
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX 4 – Test Suite Reference
# ══════════════════════════════════════════════════════════════════════════════
heading_para("Appendix 4: Test Suite Reference", 14, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)

body_para(
    "The test suite consists of 12 pytest test files covering all major system components. "
    "Tests can be run with the following commands:"
)

p = doc.add_paragraph()
run = p.add_run(
    "    pytest -q                              # all tests\n"
    "    pytest -q -m 'not slow'               # skip network/slow tests\n"
    "    pytest --cov=. --cov-report=term -q   # with coverage\n"
    "    python -m compileall -q .             # syntax check only"
)
run.font.name = "Courier New"; run.font.size = Pt(10)
p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(4)

add_table(
    ["Test File", "Coverage"],
    [
        ["tests/test_evidence.py", "NormalizedClaim, MockNLI, EvidenceAggregator, comparator"],
        ["tests/test_debate.py", "Proposer, Critic, Reviser, DebateManager, Judge"],
        ["tests/test_conflict.py", "ConflictClassifier rule-based path, all 5 types"],
        ["tests/test_conflict_types.py", "Extended conflict type classification scenarios"],
        ["tests/test_search_fallbacks.py", "Wikipedia 429 → OpenCode; DDG redirect decoding"],
        ["tests/test_ai_answer_agent.py", "AIAnswerAgent Gemini success, fail→OpenCode, entity prompt"],
        ["tests/test_baselines.py", "Evaluation system baseline checks"],
        ["tests/test_aggregator.py", "Aggregator rules, entity-resolution, challenge guards"],
        ["tests/test_relevance.py", "Relevance filter in EvidenceNormalizer"],
        ["tests/test_llm_failure.py", "LLM error propagation through pipeline stages"],
        ["tests/test_retrieval_failure.py", "Agent retrieval failure handling"],
        ["tests/test_event_loop.py", "Event loop and async compatibility"],
    ],
    caption="Table A4.1: Test File Coverage Summary"
)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# APPENDIX 5 – Pydantic Data Models Reference
# ══════════════════════════════════════════════════════════════════════════════
heading_para("Appendix 5: Pydantic Data Models Reference", 14, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT)

body_para(
    "All Pydantic models used in the system are defined in evidence/models.py. This "
    "appendix provides a reference for the key models, their fields, and their types."
)

subsection_heading("Core Enums")

body_para(
    "ConflictType: FACTUAL, TEMPORAL, VERSION, CONTEXTUAL, SOURCE, UNKNOWN. "
    "NLILabel: ENTAILMENT, CONTRADICTION, NEUTRAL. "
    "EvidenceStatus: OK, NO_RELEVANT_RESULTS, RETRIEVAL_FAILED. "
    "EvidenceState: AGREEMENT, DISAGREEMENT, UNCERTAIN, INSUFFICIENT. "
    "ComponentStatus: LLM_SUCCESS, FALLBACK, FAILED."
)

subsection_heading("NormalizedClaim")

body_para(
    "Fields: text (str, one-sentence answer), source (Source), date (Optional[str], year), "
    "version (Optional[str]), scope (Optional[str], population/platform). The text field "
    "is the primary input to NLI comparison. The date, version, and scope fields feed "
    "the NLI pattern detector and the Proposer's metadata enrichment."
)

subsection_heading("AgentEvidence")

body_para(
    "Fields: agent_id (str), query (str), status (EvidenceStatus), failure_reason "
    "(Optional[str]), claims (List[NormalizedClaim], usually 0 or 1), sources "
    "(List[Source]), raw_results_count (int), filtered_out_count (int), metadata "
    "(Dict). The is_usable property returns True only when status is OK and claims "
    "is non-empty."
)

subsection_heading("JudgeResult")

body_para(
    "Fields: winner (str, candidate_1 or candidate_2), reason (str), evidence_score "
    "(float 0–1), reasoning_score (float 0–1), source_score (float 0–1), confidence "
    "(float 0–1), scores (Dict). candidate_1 always corresponds to claim_a from the "
    "top_conflict pair identified by the EvidenceAggregator."
)

subsection_heading("FinalAnswer")

body_para(
    "Fields: query (str), answer (str), reasoning (str), evidence_state (EvidenceState), "
    "sources (List[Source]), debate_triggered (bool), conflict (Optional[Conflict]), "
    "debate_outcome (Optional[DebateOutcome]), judge_result (Optional[JudgeResult]), "
    "independent_agents_agreeing (int), source_count (int)."
)

doc.add_paragraph()

# ── Final page number placeholder ────────────────────────────────────────────
p = doc.add_paragraph("— End of Report —")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.italic = True

# ══════════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════════
output_path = "/home/sasi-boss/Desktop/MAD-2/Evidence_MAD_Project_Report.docx"
doc.save(output_path)
print(f"\nReport saved to: {output_path}")

print("Part 7 (References + Appendices + Save) done.")
