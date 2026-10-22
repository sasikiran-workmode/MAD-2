"""Part 2: Table of Contents, List of Figures, List of Tables, Acronyms"""

# ══════════════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════════════
heading_para("CONTENTS", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

toc_entries = [
    ("DECLARATION", "iii"),
    ("CERTIFICATE", "iv"),
    ("ABSTRACT", "i"),
    ("ACKNOWLEDGEMENT", "ii"),
    ("LIST OF FIGURES", "ix"),
    ("LIST OF TABLES", "xi"),
    ("LIST OF ACRONYMS", "xii"),
    ("CHAPTER 1  INTRODUCTION", ""),
    ("    1.1  Overview and Motivation", "1"),
    ("    1.2  Problem Statement", "3"),
    ("    1.3  Objectives", "5"),
    ("    1.4  Scope of the Project", "6"),
    ("    1.5  Organization of the Report", "7"),
    ("CHAPTER 2  LITERATURE REVIEW", ""),
    ("    2.1  Introduction", "8"),
    ("    2.2  Multi-Agent Systems and Debate", "9"),
    ("    2.3  Natural Language Inference", "12"),
    ("    2.4  Evidence Retrieval Approaches", "14"),
    ("    2.5  Conflict Detection and Classification", "16"),
    ("    2.6  Research Gap", "18"),
    ("CHAPTER 3  SYSTEM DESIGN AND ARCHITECTURE", ""),
    ("    3.1  High-Level Architecture", "20"),
    ("    3.2  Two-Mode Operation", "21"),
    ("    3.3  Component Dependency Map", "22"),
    ("    3.4  Configuration and Environment", "23"),
    ("CHAPTER 4  AGENTS LAYER", ""),
    ("    4.1  Agent Registry and Base Class", "25"),
    ("    4.2  Query Router", "26"),
    ("    4.3  Web Agent", "27"),
    ("    4.4  Reference Agent", "28"),
    ("    4.5  Scholarly Agent", "29"),
    ("    4.6  AI Answer Agent", "30"),
    ("CHAPTER 5  EVIDENCE PIPELINE", ""),
    ("    5.1  Evidence Flow Overview", "32"),
    ("    5.2  Relevance Filter", "33"),
    ("    5.3  LLM Normalization", "34"),
    ("    5.4  Evidence Aggregator", "36"),
    ("CHAPTER 6  NLI AND CONFLICT DETECTION", ""),
    ("    6.1  NLI Detector Classes", "38"),
    ("    6.2  Query-Aware Guard Chain", "39"),
    ("    6.3  Entity Substitution Guard", "40"),
    ("    6.4  Explicit Challenge Guard", "41"),
    ("    6.5  Target Resolution Guard", "42"),
    ("    6.6  Transformer-Based NLI", "43"),
    ("CHAPTER 7  CONFLICT CLASSIFICATION", ""),
    ("    7.1  Conflict Classifier", "44"),
    ("    7.2  Five-Type Taxonomy", "45"),
    ("    7.3  Pattern-Based Fallback", "46"),
    ("CHAPTER 8  DEBATE LIFECYCLE", ""),
    ("    8.1  Debate Manager", "47"),
    ("    8.2  Proposer", "48"),
    ("    8.3  Critic", "49"),
    ("    8.4  Reviser and Early Stopping", "50"),
    ("    8.5  Judge", "51"),
    ("CHAPTER 9  API, FRONTEND AND DEPLOYMENT", ""),
    ("    9.1  FastAPI Application", "53"),
    ("    9.2  Frontend", "54"),
    ("    9.3  Deployment", "55"),
    ("CHAPTER 10  EVALUATION AND RESULTS", ""),
    ("    10.1  Evaluation Framework", "56"),
    ("    10.2  Experimental Results", "57"),
    ("    10.3  Ablation Study", "59"),
    ("CHAPTER 11  CONCLUSION AND FUTURE WORK", "62"),
    ("REFERENCES", "64"),
    ("APPENDICES", "68"),
]

for entry, pg in toc_entries:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(14)
    tab_stops = p.paragraph_format.tab_stops
    run = p.add_run(entry)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    if "CHAPTER" in entry and "    " not in entry:
        run.font.bold = True
    if pg:
        p.add_run("\t" + pg).font.name = "Times New Roman"
        p.runs[-1].font.size = Pt(12)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

p = doc.add_paragraph("iv")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# LIST OF FIGURES
# ══════════════════════════════════════════════════════════════════════════════
heading_para("LIST OF FIGURES", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

figures = [
    ("Figure 1.1", "Overview of the Evidence-MAD Pipeline", "2"),
    ("Figure 1.2", "Evidence Gate Decision Flowchart", "4"),
    ("Figure 3.1", "Top-Level System Architecture", "20"),
    ("Figure 3.2", "RunMode: FIXTURE vs. LIVE", "21"),
    ("Figure 3.3", "Component Dependency Map", "22"),
    ("Figure 4.1", "QueryRouter with ThreadPoolExecutor", "26"),
    ("Figure 4.2", "Web Agent with DuckDuckGo and Fallback", "27"),
    ("Figure 4.3", "AIAnswerAgent Dual-Provider Design", "30"),
    ("Figure 5.1", "Evidence Flow from Retrieval to Normalization", "32"),
    ("Figure 5.2", "Relevance Filter Content-Word Overlap", "33"),
    ("Figure 5.3", "EvidenceAggregator Decision Rule", "36"),
    ("Figure 6.1", "NLI Detector Class Hierarchy", "38"),
    ("Figure 6.2", "Query-Aware Guard Chain Flowchart", "39"),
    ("Figure 7.1", "Conflict Type Taxonomy", "45"),
    ("Figure 8.1", "Debate Lifecycle: Propose-Critique-Revise-Judge", "47"),
    ("Figure 8.2", "Early Stop Conditions", "50"),
    ("Figure 9.1", "FastAPI Endpoint Schema", "53"),
    ("Figure 9.2", "Frontend UI Screenshot (Demo Mode)", "54"),
    ("Figure 10.1", "Key Fact Accuracy Across Systems", "57"),
    ("Figure 10.2", "Debate Trigger Rate Comparison", "58"),
    ("Figure 10.3", "Average LLM Calls Per Query", "59"),
    ("Figure 10.4", "Ablation Study: Component Contribution", "60"),
    ("Figure 10.5", "Conflict Type Distribution in Evaluation", "61"),
]

for fig_id, caption, pg in figures:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(14)
    run = p.add_run(f"{fig_id}  {caption}")
    run.font.name = "Times New Roman"; run.font.size = Pt(12)
    p.add_run(f"\t{pg}").font.name = "Times New Roman"
    p.runs[-1].font.size = Pt(12)

p = doc.add_paragraph("ix")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# LIST OF TABLES
# ══════════════════════════════════════════════════════════════════════════════
heading_para("LIST OF TABLES", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

tables_list = [
    ("Table 2.1", "Summary of Related Work in Multi-Agent Debate", "13"),
    ("Table 2.2", "Comparison of NLI Models", "14"),
    ("Table 3.1", "Configuration Parameters and Defaults", "23"),
    ("Table 4.1", "Search Agent Summary", "25"),
    ("Table 5.1", "EvidenceStatus Values and Meanings", "35"),
    ("Table 6.1", "NLI Detector Class Comparison", "38"),
    ("Table 7.1", "Conflict Type Definitions and Examples", "45"),
    ("Table 8.1", "Debate Stop Reason Summary", "51"),
    ("Table 9.1", "API Response Schema Fields", "53"),
    ("Table 10.1", "Quantitative Evaluation Results Across Systems", "57"),
    ("Table 10.2", "Ablation Study Results", "60"),
    ("Table 10.3", "LLM Call Count by Role", "61"),
]

for tbl_id, caption, pg in tables_list:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(14)
    run = p.add_run(f"{tbl_id}  {caption}")
    run.font.name = "Times New Roman"; run.font.size = Pt(12)
    p.add_run(f"\t{pg}").font.name = "Times New Roman"
    p.runs[-1].font.size = Pt(12)

p = doc.add_paragraph("xi")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# LIST OF ACRONYMS
# ══════════════════════════════════════════════════════════════════════════════
heading_para("LIST OF ACRONYMS", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

acronyms = [
    ("API",   "Application Programming Interface"),
    ("CORS",  "Cross-Origin Resource Sharing"),
    ("CPU",   "Central Processing Unit"),
    ("DDG",   "DuckDuckGo"),
    ("DOI",   "Digital Object Identifier"),
    ("F1",    "Harmonic Mean of Precision and Recall"),
    ("GPU",   "Graphics Processing Unit"),
    ("HTTP",  "Hypertext Transfer Protocol"),
    ("JSON",  "JavaScript Object Notation"),
    ("LLM",   "Large Language Model"),
    ("MAD",   "Multi-Agent Debate"),
    ("NLI",   "Natural Language Inference"),
    ("NLP",   "Natural Language Processing"),
    ("RAG",   "Retrieval Augmented Generation"),
    ("REST",  "Representational State Transfer"),
    ("RoBERTa", "Robustly Optimized BERT Pretraining Approach"),
    ("SNLI",  "Stanford Natural Language Inference"),
    ("URL",   "Uniform Resource Locator"),
    ("VIT",   "Vellore Institute of Technology"),
    ("QA",    "Question Answering"),
    ("ASGI",  "Asynchronous Server Gateway Interface"),
    ("CLI",   "Command Line Interface"),
    ("SDK",   "Software Development Kit"),
    ("TP",    "True Positive"),
    ("FP",    "False Positive"),
    ("TN",    "True Negative"),
    ("FN",    "False Negative"),
]

for abbr, full in acronyms:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(14)
    run = p.add_run(f"{abbr:<16}{full}")
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

p = doc.add_paragraph("xii")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()
print("Part 2 (TOC + lists) done.")
