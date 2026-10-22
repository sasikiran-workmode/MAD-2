"""
Evidence-MAD Project Report Generator
BCE497J Template Format - Minimum 63 pages
"""

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ─── Page Setup ───────────────────────────────────────────────────────────────
section = doc.sections[0]
section.page_width  = Cm(21.0)
section.page_height = Cm(29.7)
section.left_margin   = Cm(3.81)
section.right_margin  = Cm(2.54)
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)

# ─── Style helpers ────────────────────────────────────────────────────────────
def set_para_fmt(para, size, bold=False, italic=False, underline=False,
                 align=WD_ALIGN_PARAGRAPH.LEFT, space_before=6, space_after=6,
                 line_spacing=None, color=None, all_caps=False, font_name="Times New Roman"):
    para.alignment = align
    pf = para.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    if line_spacing:
        from docx.shared import Pt as _Pt
        pf.line_spacing = _Pt(line_spacing)
    for run in para.runs:
        run.font.name      = font_name
        run.font.size      = Pt(size)
        run.font.bold      = bold
        run.font.italic    = italic
        run.font.underline = underline
        if color:
            run.font.color.rgb = RGBColor(*color)
        if all_caps:
            run.font.all_caps = True

def heading_para(text, size, bold=True, caps=False, underline=False,
                 align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=12):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.underline = underline
    if caps:
        run.font.all_caps = True
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    return p

def body_para(text, size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              space_before=4, space_after=6, first_line_indent=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name   = "Times New Roman"
    run.font.size   = Pt(size)
    run.font.bold   = bold
    run.font.italic = italic
    p.alignment     = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    if first_line_indent:
        p.paragraph_format.first_line_indent = Pt(first_line_indent)
    from docx.shared import Pt as _Pt
    p.paragraph_format.line_spacing = _Pt(18)   # 1.5 line spacing
    return p

def chapter_heading(chap_num, title):
    p = doc.add_paragraph()
    run = p.add_run(f"CHAPTER {chap_num}")
    run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(18); p.paragraph_format.space_after = Pt(6)

    p2 = doc.add_paragraph()
    run2 = p2.add_run(title.upper())
    run2.font.name = "Times New Roman"; run2.font.size = Pt(16); run2.font.bold = True
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.space_before = Pt(0); p2.paragraph_format.space_after = Pt(18)

def section_heading(text):
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.font.name = "Times New Roman"; run.font.size = Pt(14); run.font.bold = False
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(6)

def subsection_heading(text):
    p = doc.add_paragraph()
    run = p.add_run(text.upper())
    run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.bold = True
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)

def page_break():
    doc.add_page_break()

def add_table(headers, rows, caption=None):
    tbl = doc.add_table(rows=1+len(rows), cols=len(headers))
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    hrow = tbl.rows[0]
    for i, h in enumerate(headers):
        cell = hrow.cells[i]
        cell.text = h
        for run in cell.paragraphs[0].runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(11)
            run.font.bold = True
    for ri, row_data in enumerate(rows):
        trow = tbl.rows[ri+1]
        for ci, val in enumerate(row_data):
            cell = trow.cells[ci]
            cell.text = str(val)
            for run in cell.paragraphs[0].runs:
                run.font.name = "Times New Roman"
                run.font.size = Pt(10)
    if caption:
        cp = doc.add_paragraph(caption)
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cp.runs:
            run.font.name = "Times New Roman"; run.font.size = Pt(10); run.font.italic = True
    return tbl

# ══════════════════════════════════════════════════════════════════════════════
# COVER PAGE (Page 1)
# ══════════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
run = p.add_run("A project report on")
run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(72)

p = doc.add_paragraph()
run = p.add_run("MULTI-AGENT DEBATE FRAMEWORK USING EVIDENCE DISAGREEMENT TRIGGERING AND CONFLICT-TYPE CLASSIFICATION")
run.font.name = "Times New Roman"; run.font.size = Pt(20); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(12)

p = doc.add_paragraph()
run = p.add_run("Submitted in partial fulfillment for the award of the degree of")
run.font.name = "Times New Roman"; run.font.size = Pt(14); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("Bachelor of Technology in Computer Science and Engineering (Artificial Intelligence and Machine Learning)")
run.font.name = "Times New Roman"; run.font.size = Pt(22); run.font.bold = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(12)

p = doc.add_paragraph()
run = p.add_run("by")
run.font.name = "Times New Roman"; run.font.size = Pt(14); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("M. REDDY SASI KIRAN (23BAI1188)\nSUHAS KOHEDA (23BAI1148)\nC R SUHAS (23BAI1187)")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(24)

p = doc.add_paragraph()
run = p.add_run("SCHOOL OF COMPUTER SCIENCE AND ENGINEERING")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("VELLORE INSTITUTE OF TECHNOLOGY, CHENNAI")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("November, 2025")
run.font.name = "Times New Roman"; run.font.size = Pt(12)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE (Page 2)
# ══════════════════════════════════════════════════════════════════════════════
p = doc.add_paragraph()
run = p.add_run("A project report on")
run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(60)

p = doc.add_paragraph()
run = p.add_run("MULTI-AGENT DEBATE FRAMEWORK USING EVIDENCE DISAGREEMENT TRIGGERING AND CONFLICT-TYPE CLASSIFICATION")
run.font.name = "Times New Roman"; run.font.size = Pt(20); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(12); p.paragraph_format.space_after = Pt(12)

p = doc.add_paragraph()
run = p.add_run("Submitted in partial fulfillment for the award of the degree of")
run.font.name = "Times New Roman"; run.font.size = Pt(14); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("Bachelor of Technology in Computer Science and Engineering (Artificial Intelligence and Machine Learning)")
run.font.name = "Times New Roman"; run.font.size = Pt(22); run.font.bold = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(12)

p = doc.add_paragraph()
run = p.add_run("by")
run.font.name = "Times New Roman"; run.font.size = Pt(14); run.font.italic = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("M. REDDY SASI KIRAN (23BAI1188)\nSUHAS KOHEDA (23BAI1148)\nC R SUHAS (23BAI1187)")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(24)

p = doc.add_paragraph()
run = p.add_run("SCHOOL OF COMPUTER SCIENCE AND ENGINEERING")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("VELLORE INSTITUTE OF TECHNOLOGY, CHENNAI")
run.font.name = "Times New Roman"; run.font.size = Pt(16); run.font.bold = True; run.font.all_caps = True
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph()
run = p.add_run("November, 2025")
run.font.name = "Times New Roman"; run.font.size = Pt(12)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.paragraph_format.space_before = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# DECLARATION PAGE
# ══════════════════════════════════════════════════════════════════════════════
heading_para("DECLARATION", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

body_para(
    "I hereby declare that the thesis entitled \"Multi-Agent Debate Framework Using Evidence "
    "Disagreement Triggering and Conflict-Type Classification\" submitted by M. Reddy Sasi Kiran "
    "(23BAI1188), for the award of the degree of Bachelor of Technology in Computer Science and "
    "Engineering (Artificial Intelligence and Machine Learning), Vellore Institute of Technology, "
    "Chennai is a record of bonafide work carried out by me under the supervision of the project "
    "guide. I further declare that the work reported in this thesis has not been submitted and will "
    "not be submitted, either in part or in full, for the award of any other degree or diploma in "
    "this institute or any other institute or university."
)

doc.add_paragraph()
body_para("Place: Chennai")
body_para("Date:")
doc.add_paragraph()

p = doc.add_paragraph()
run = p.add_run("Signature of the Candidate")
run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.bold = True
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

body_para("M. Reddy Sasi Kiran (23BAI1188)")
body_para("School of Computer Science and Engineering")

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# CERTIFICATE PAGE
# ══════════════════════════════════════════════════════════════════════════════
heading_para("CERTIFICATE", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

body_para(
    "This is to certify that the report entitled \"Multi-Agent Debate Framework Using Evidence "
    "Disagreement Triggering and Conflict-Type Classification\" is prepared and submitted by "
    "M. Reddy Sasi Kiran (23BAI1188), Suhas Koheda (23BAI1148), and C R Suhas (23BAI1187) to "
    "Vellore Institute of Technology, Chennai, in partial fulfillment of the requirement for the "
    "award of the degree of Bachelor of Technology in Computer Science and Engineering "
    "(Artificial Intelligence and Machine Learning) is a bonafide record carried out under my "
    "guidance. The project fulfills the requirements as per the regulations of this University and "
    "in my opinion meets the necessary standards for submission. The contents of this report have "
    "not been submitted and will not be submitted either in part or in full, for the award of any "
    "other degree or diploma and the same is certified."
)

doc.add_paragraph()
body_para("Signature of the Guide: ____________________")
body_para("Name: Dr. / Prof.")
body_para("Date:")
doc.add_paragraph()
body_para("Signature of the Examiner: ____________________          Signature of the Examiner: ____________________")
body_para("Name:                                                                  Name:")
body_para("Date:                                                                   Date:")
doc.add_paragraph()
body_para("Approved by the Head of Department,")
body_para("(Computer Science and Engineering — Artificial Intelligence and Machine Learning)")
body_para("Name: (HoD Name)")
body_para("Date:")
body_para("(Seal of School of Computer Science and Engineering)")

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# ABSTRACT
# ══════════════════════════════════════════════════════════════════════════════
heading_para("ABSTRACT", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

body_para(
    "Large language models (LLMs) have shown remarkable ability in answering factual questions, "
    "yet they still stuggle with hallucination, temporal inconsistencies and version-level errors "
    "that reduce reliability in high-stakes applicatons. Multi-agent debate frameworks have been "
    "proposed as a mitigation stratergy where multiple independent agents argue their positions "
    "and a judge selects the best answer. However, existing multi-agent debate systems debate "
    "every query regardless of wheather the agents actually disagree, resulting in unnecessary "
    "computational overhead and increased latency with no meaningful benefit."
)

body_para(
    "This report presents Evidence-MAD, an evidence-triggered, conflict-type-aware multi-agent "
    "debate framework that adresses these limitations through two novel contributions. First, an "
    "evidence gate based on pairwise Natural Language Inference (NLI) comparisons determines "
    "wheather agents genuinely disagree before triggering debate; queries where agents agree are "
    "answered directly without debate overhead. Second, when disagreement is detected, a conflict "
    "classifier categorises the nature of the conflict into one of five types: FACTUAL, TEMPORAL, "
    "VERSION, CONTEXTUAL, or SOURCE. Each conflict type receives a distinct debate strategy that "
    "guides the proposer, critic, and reviser agents to focus on the most relevant resolution "
    "dimension."
)

body_para(
    "The system uses three independent retrieval agents — a web search agent (DuckDuckGo), a "
    "reference agent (Wikipedia), and a scholarly agent (Crossref) — alongside an AI answer agent "
    "powered by Google Gemini with Search grounding. Evidence from all agents is normalized "
    "through a two-stage pipeline: a content-word relevance filter followed by LLM-based claim "
    "normalization. Three query-aware NLI guards preempt model inference for specific failure "
    "patterns that generic NLI models often miss, including entity substitution conflicts, "
    "explicit epistemic challenges, and target-resolution mismatches."
)

body_para(
    "An ablation study compares the proposed system against five configurations: Single LLM "
    "(no retrieval or debate), Standard MAD (always debates), No Gate (ablation removing the "
    "evidence gate), No Typed Strategy (ablation using generic debate prompts), and No Relevance "
    "Filter (ablation removing the relevance filter). Evaluation on a controlled dataset "
    "demonstrates that the evidence gate successfully eliminates false-positive debates while "
    "maintaining accuracy, and conflict-type-specific strategies improve resolution quality for "
    "temporal, version, and contextual conflicts. The system is deployed as a FastAPI REST "
    "service with a browser-based frontend, supports both offline fixture mode and live mode, "
    "and is optionally deployable to Vercel serverless infrastructure."
)

body_para(
    "Keywords: Multi-agent debate, evidence gating, Natural Language Inference, conflict-type "
    "classification, hallucination mitigation, large language models, information retrieval."
)

# roman numeral page marker
p = doc.add_paragraph("i")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()

# ══════════════════════════════════════════════════════════════════════════════
# ACKNOWLEDGEMENT
# ══════════════════════════════════════════════════════════════════════════════
heading_para("ACKNOWLEDGEMENT", 14, bold=True, caps=False, underline=True, align=WD_ALIGN_PARAGRAPH.CENTER)

body_para(
    "It is my pleasure to express with deep sense of gratitude to my project guide, School of "
    "Computer Science and Engineering, Vellore Institute of Technology, Chennai, for the constant "
    "guidance, continual encouragement, and understanding throughout this project. The association "
    "has not been confined to academics alone but has been a great opportunity to work with an "
    "intellectual and expert in the field of artificial intelligence and machine learning."
)

body_para(
    "It is with gratitude that I would like to extend my thanks to the visionary leader "
    "Dr. G. Viswanathan, Honorable Chancellor, Mr. Sankar Viswanathan, Dr. Sekar Viswanathan, "
    "Dr. G V Selvam, Vice Presidents, Dr. Sandhya Pentareddy, Executive Director, "
    "Ms. Kadhambari S. Viswanathan, Assistant Vice-President, Dr. V. S. Kanchana Bhaaskaran, "
    "Vice-Chancellor, Dr. T. Thyagarajan, Pro-Vice Chancellor, VIT Chennai and "
    "Dr. P. K. Manoharan, Additional Registrar for providing an exceptional working environment "
    "and inspiring all of us during the tenure of the course."
)

body_para(
    "Special mention to Dr. Viswanathan V, Dean, Dr. Nithyanandam P, Associate Dean, "
    "Dr. Suganya G, Associate Dean, Dr. Sweetlin Hemalatha C, Associate Dean, School of "
    "Computer Science and Engineering, Vellore Institute of Technology, Chennai for spending "
    "their valuable time and efforts in sharing knowledge and for helping in every aspect of "
    "this academic journey."
)

body_para(
    "In jubilant state, I express ingeniously my whole-hearted thanks to the Head of the "
    "Department, B.Tech. Computer Science and Engineering (Artificial Intelligence and Machine "
    "Learning) and the Project Coordinators for their valuable support and encouragement to take "
    "up and complete the thesis. My sincere thanks to all the faculties and staffs at Vellore "
    "Institute of Technology, Chennai who helped acquire the requisite knowledge."
)

body_para(
    "I would like to thank my parents for their unwavering support throughout this journey. "
    "It is indeed a pleasure to thank my friends and teammates Suhas Koheda and C R Suhas who "
    "encouraged me and collaborated effectively to take up and complete this project."
)

doc.add_paragraph()
body_para("Place: Chennai")
body_para("Date:")
doc.add_paragraph()

p = doc.add_paragraph()
run = p.add_run("M. Reddy Sasi Kiran")
run.font.name = "Times New Roman"; run.font.size = Pt(12); run.font.bold = True
p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

p = doc.add_paragraph("ii")
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in p.runs:
    run.font.name = "Times New Roman"; run.font.size = Pt(12)

page_break()

print("Part 1 (front matter) done.")
