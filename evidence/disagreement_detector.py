"""
NLI-based disagreement detector.
Tasks applied:
  Task 7:  Correct input format ({text, text_pair}); top_k=None; both directions;
           NLIError raised on failure (never returns neutral on crash).
  Task 3:  MockNLIDetector accepts an exact-match fixture lookup dict;
           raises KeyError on unknown pair (no word-overlap heuristic).
"""
import os
from typing import Dict, Any, Optional, List
from loguru import logger
from functools import lru_cache

from evidence.models import NLILabel
from config import settings


# ------------------------------------------------------------------ #
# Public exception                                                     #
# ------------------------------------------------------------------ #

class NLIError(Exception):
    """Raised when NLI inference fails (never silently returns neutral)."""


def _entity_substitution_prediction(
    premise: str, hypothesis: str
) -> Optional[Dict[str, Any]]:
    """Detect a named-work substitution versus an explicit rejection.

    A claim that replaces the queried work with a differently named paper is
    not an agreement with a claim that says the queried paper does not exist.
    Generic NLI models often miss this because both claims can share a date
    correction (for example, that a future year is impossible).
    """
    import re as _re

    def has_rejection(text: str) -> bool:
        return bool(_re.search(
            r"\b(?:no such|does not exist|doesn't exist|no record of|"
            r"cannot find|unable to find)\s+(?:an?\s+|the\s+)?"
            r"(?:paper|article|publication|work)\b",
            text,
            _re.I,
        ))

    def names_a_work(text: str) -> bool:
        return bool(_re.search(
            r"\b(?:paper|article|publication|work)\s+[\"“][^\"”]{3,160}[\"”]",
            text,
            _re.I,
        ))

    if (has_rejection(premise) and names_a_work(hypothesis)) or (
        has_rejection(hypothesis) and names_a_work(premise)
    ):
        return {
            "label": NLILabel.CONTRADICTION,
            "score": 0.91,
            "all_scores": {
                NLILabel.CONTRADICTION: 0.91,
                NLILabel.ENTAILMENT: 0.05,
                NLILabel.NEUTRAL: 0.04,
            },
        }
    return None


def _target_resolution_prediction(
    query: str, premise: str, hypothesis: str
) -> Optional[Dict[str, Any]]:
    """Detect an answer-target conflict that ordinary NLI can flatten away.

    Search agents will sometimes silently autocorrect a misspelled or unknown
    title in the question, while another agent explicitly reports that the
    title as written has no known record.  Both responses can share a true
    date correction, so a generic NLI model may call them compatible.  They
    are nevertheless competing resolutions of the user's target and must
    open the debate gate.

    This intentionally requires all three signals: a queried title, an
    explicit rejection of that queried title, and a different title presented
    as the answer.  That keeps an unrelated nonexistence statement neutral.
    """
    import re as _re

    def normalise(value: str) -> str:
        return " ".join(_re.findall(r"[a-z0-9]+", value.lower()))

    def quoted_titles(text: str) -> set[str]:
        return {
            normalise(match)
            for match in _re.findall(r"[\"“']([^\"”']{3,160})[\"”']", text)
            if len(normalise(match).split()) >= 2
        }

    def rejected_titles(text: str) -> set[str]:
        # Accept quoted and unquoted forms such as
        # "no known paper titled whipro is all u need from 2082".
        matches = _re.findall(
            r"\b(?:no\s+(?:known\s+)?|no\s+such\s+|does not exist\s+as\s+(?:a\s+)?)"
            r"(?:an?\s+|the\s+)?(?:paper|article|publication|work)"
            r"(?:\s+(?:titled|called|named))?\s+"
            r"(?:[\"“'](?P<quoted>[^\"”']{3,160})[\"”']|(?P<plain>[a-z0-9][a-z0-9 '\-]{2,100}?))"
            r"(?=\s+(?:from|in|published|was|is|which|that)\b|[,.;]|$)",
            text,
            flags=_re.I,
        )
        return {
            normalise(quoted or plain)
            for quoted, plain in matches
            if len(normalise(quoted or plain).split()) >= 2
        }

    query_norm = normalise(query)
    rejected = rejected_titles(premise) | rejected_titles(hypothesis)
    # A quoted title is the most reliable indicator that an agent selected a
    # specific work.  Do not reuse rejected titles as positive resolutions.
    positive = (quoted_titles(premise) | quoted_titles(hypothesis)) - rejected

    rejected_query_titles = {
        title for title in rejected
        if query_norm and (title in query_norm or query_norm in title)
    }
    if not rejected_query_titles or not positive:
        return None

    for rejected_title in rejected_query_titles:
        if any(title != rejected_title for title in positive):
            return {
                "label": NLILabel.CONTRADICTION,
                "score": 0.93,
                "all_scores": {
                    NLILabel.CONTRADICTION: 0.93,
                    NLILabel.ENTAILMENT: 0.03,
                    NLILabel.NEUTRAL: 0.04,
                },
            }
    return None


def _explicit_challenge_prediction(
    query: str, premise: str, hypothesis: str
) -> Optional[Dict[str, Any]]:
    """Treat an explicit evidence challenge as a material disagreement.

    This is deliberately independent of paper titles, dates, or any other
    domain-specific vocabulary.  When an agent says that the requested fact
    or entity cannot be verified, is unsupported, or does not exist, another
    agent cannot be considered to agree if it supplies an affirmative answer
    to that same question.  A generic NLI model often calls that pair neutral
    because the words differ; for the evidence gate it must be debated.

    Mere corrections ("not 2082; it was 2017") are *not* challenges.  The
    rule requires an epistemic or existence claim such as "no record",
    "cannot verify", or "unsupported", which avoids turning ordinary shared
    corrections into disagreement.
    """
    import re as _re

    challenge_pattern = _re.compile(
        r"\b(?:"
        r"no\s+(?:(?:known|reliable|official|credible)\s+)?"
        r"(?:record|evidence|source|documentation|information|verification|such)\b|"
        r"(?:does not|doesn't|do not|don't)\s+exist\b|"
        r"(?:cannot|can't|unable to|could not|couldn't)\s+"
        r"(?:verify|find|confirm|locate|substantiate)\b|"
        r"\b(?:unverified|unsupported|unsubstantiated|nonexistent|unknown)\b|"
        r"\b(?:not\s+(?:verified|verifiable|supported|documented|confirmed))\b"
        r")",
        _re.I,
    )

    def content_words(text: str) -> set[str]:
        stop = {
            "the", "a", "an", "and", "or", "of", "in", "on", "at", "to",
            "for", "from", "with", "is", "are", "was", "were", "be", "been",
            "what", "when", "where", "who", "why", "how", "does", "do", "did",
        }
        return {
            token for token in _re.findall(r"[a-z0-9]+", text.lower())
            if token not in stop and len(token) > 1
        }

    # Claims have already passed the relevance filter, but require at least
    # one query-topic token as a second guard against a stray disclaimer.
    query_words = content_words(query)

    def is_query_relevant_challenge(text: str) -> bool:
        if not challenge_pattern.search(text):
            return False
        if query_words & content_words(text):
            return True
        # A concise answer may use a deictic reference ("cannot verify it").
        # In an answer slot that pronoun refers to the current query.
        return bool(query_words) and bool(
            _re.search(r"\b(?:it|this|that|the claim|the premise)\b", text, _re.I)
        )

    premise_challenges = is_query_relevant_challenge(premise)
    hypothesis_challenges = is_query_relevant_challenge(hypothesis)
    if premise_challenges == hypothesis_challenges:
        return None

    affirmative = hypothesis if premise_challenges else premise
    # A substantive, non-challenge answer is an affirmative competing claim.
    # Do not fire on an empty or purely apologetic response.
    if len(content_words(affirmative)) < 3:
        return None

    return {
        "label": NLILabel.CONTRADICTION,
        "score": 0.90,
        "all_scores": {
            NLILabel.CONTRADICTION: 0.90,
            NLILabel.ENTAILMENT: 0.04,
            NLILabel.NEUTRAL: 0.06,
        },
    }


# ------------------------------------------------------------------ #
# Real transformer NLI detector                                        #
# ------------------------------------------------------------------ #

class NLIDetector:
    """
    Hugging Face transformer NLI detector.
    Uses text/text_pair input format (not the buggy </s> concatenation).
    Runs both directions and takes the stronger contradiction.
    Raises NLIError on any failure — never returns neutral on crash.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        threshold: Optional[float] = None,
    ):
        self.model_name = model_name or settings.nli_model
        self.device = device or settings.nli_device
        # Use explicit None-guard (fixes the `or` bug from Task 2)
        self.threshold = settings.disagreement_threshold if threshold is None else threshold
        self._pipeline = None

    def _load_model(self) -> None:
        if self._pipeline is not None:
            return
        try:
            from transformers import pipeline
            import torch
            logger.info(f"Loading NLI model: {self.model_name} on {self.device}")
            if self.device == "cuda":
                device_id = 0 if torch.cuda.is_available() else -1
            elif self.device == "auto":
                device_id = 0 if torch.cuda.is_available() else -1
            else:
                device_id = -1
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                device=device_id,
                top_k=None,           # replaces deprecated return_all_scores=True
            )
            logger.info("NLI model loaded.")
        except Exception as e:
            raise NLIError(f"Failed to load NLI model {self.model_name}: {e}") from e

    def _run_once(self, premise: str, hypothesis: str) -> Dict[NLILabel, float]:
        """Run NLI in one direction; returns score dict keyed by NLILabel."""
        try:
            results = self._pipeline({"text": premise, "text_pair": hypothesis})
        except Exception as e:
            raise NLIError(f"NLI pipeline failed: {e}") from e

        all_scores: Dict[NLILabel, float] = {}
        for item in results[0]:
            label_str = item["label"].lower()
            if "entail" in label_str:
                all_scores[NLILabel.ENTAILMENT] = item["score"]
            elif "contradict" in label_str:
                all_scores[NLILabel.CONTRADICTION] = item["score"]
            elif "neutral" in label_str:
                all_scores[NLILabel.NEUTRAL] = item["score"]
        if not all_scores:
            raise NLIError("NLI pipeline returned no recognisable labels")
        return all_scores

    def predict(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        """
        Predict NLI with bidirectional check (take stronger contradiction).
        Raises NLIError on failure.
        """
        entity_prediction = _entity_substitution_prediction(premise, hypothesis)
        if entity_prediction:
            return entity_prediction

        self._load_model()
        fwd = self._run_once(premise, hypothesis)
        bwd = self._run_once(hypothesis, premise)
        # Symmetric merge: max contradiction, min entailment (conservative)
        contra = max(
            fwd.get(NLILabel.CONTRADICTION, 0.0),
            bwd.get(NLILabel.CONTRADICTION, 0.0),
        )
        ent = min(
            fwd.get(NLILabel.ENTAILMENT, 1.0),
            bwd.get(NLILabel.ENTAILMENT, 1.0),
        )
        neu = max(
            fwd.get(NLILabel.NEUTRAL, 0.0),
            bwd.get(NLILabel.NEUTRAL, 0.0),
        )
        all_scores = {
            NLILabel.CONTRADICTION: contra,
            NLILabel.ENTAILMENT: ent,
            NLILabel.NEUTRAL: neu,
        }
        best = max(all_scores, key=all_scores.__getitem__)
        return {"label": best, "score": all_scores[best], "all_scores": all_scores}

    def predict_for_query(
        self, query: str, premise: str, hypothesis: str
    ) -> Dict[str, Any]:
        """Classify a pair while preserving the question's named target."""
        challenge_prediction = _explicit_challenge_prediction(query, premise, hypothesis)
        if challenge_prediction:
            return challenge_prediction
        target_prediction = _target_resolution_prediction(query, premise, hypothesis)
        return target_prediction or self.predict(premise, hypothesis)

    def detect_disagreement(self, text_a: str, text_b: str) -> Dict[str, Any]:
        result = self.predict(text_a, text_b)
        contra = result["all_scores"].get(NLILabel.CONTRADICTION, 0.0)
        return {
            "disagreement": contra >= self.threshold,
            "label": result["label"],
            "contradiction_score": contra,
            "entailment_score": result["all_scores"].get(NLILabel.ENTAILMENT, 0.0),
            "neutral_score": result["all_scores"].get(NLILabel.NEUTRAL, 0.0),
            "threshold": self.threshold,
            "all_scores": result["all_scores"],
        }


# ------------------------------------------------------------------ #
# Mock / fixture NLI detector (Task 7 / Task 22)                      #
# ------------------------------------------------------------------ #

class LLMNLIDetector:
    """
    LLM-based NLI detector for LIVE mode when NLI_MODE=mock but a real LLM is available.
    Asks the LLM whether two claims contradict each other.
    Much more accurate than keyword patterns for arbitrary real-world queries.
    """

    _PROMPT = """You are the strict NLI gate for an evidence-triggered debate.

USER QUESTION: {query}
Claim A: {claim_a}
Claim B: {claim_b}

Determine whether these agents reached the SAME answer to the user's question.
Classify a material difference as CONTRADICTION, even if the claims share one
true detail.  In particular, CONTRADICTION is required when one agent silently
substitutes a different named paper/article/product/person for the queried
entity and another agent says the queried entity as written is unknown,
nonexistent, or unsupported.  This is an entity-resolution conflict, not
agreement.  Do not let a shared date correction hide that conflict.
Likewise, if one agent explicitly says the requested fact cannot be verified,
has no reliable/official support, or does not exist, and the other supplies an
affirmative answer, classify CONTRADICTION.  Do not downgrade that evidence
challenge to NEUTRAL merely because it uses different wording.

Answer with ONLY a JSON object:
{{
  "label": "CONTRADICTION" or "ENTAILMENT" or "NEUTRAL",
  "contradiction_score": 0.0-1.0,
  "entailment_score": 0.0-1.0,
  "neutral_score": 0.0-1.0,
  "reason": "<one sentence>"
}}

Guidelines:
- CONTRADICTION: the claims give different facts, different numbers, opposite statements about the same thing, or different resolutions of the entity the user asked about.
- ENTITY SUBSTITUTION: if one claim names a paper, article, or other entity while
  the other rejects the queried entity as nonexistent, classify CONTRADICTION.
  Do not mark them as entailing merely because both reject a date in the query.
- EVIDENCE CHALLENGE: "cannot verify", "no record", "unsupported", or a similar
  rejection of the requested fact conflicts with another agent's affirmative answer.
- ENTAILMENT: the claims have the same answer target and every material assertion is compatible.
- NEUTRAL: the claims are about different things or neither supports nor contradicts the other"""

    def __init__(self, threshold: float = 0.70, llm_client=None):
        self.threshold = threshold
        self.llm_client = llm_client

    def predict(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        return self.predict_for_query("", premise, hypothesis)

    def predict_for_query(
        self, query: str, premise: str, hypothesis: str
    ) -> Dict[str, Any]:
        entity_prediction = _entity_substitution_prediction(premise, hypothesis)
        if entity_prediction:
            return entity_prediction
        challenge_prediction = _explicit_challenge_prediction(query, premise, hypothesis)
        if challenge_prediction:
            return challenge_prediction
        target_prediction = _target_resolution_prediction(query, premise, hypothesis)
        if target_prediction:
            return target_prediction
        if not self.llm_client:
            # Fallback to simple pattern if no LLM available
            return _pattern_predict(premise, hypothesis)
        try:
            from llm_client import LLMError
            prompt = self._PROMPT.format(
                query=query or "(Question context unavailable)",
                claim_a=premise,
                claim_b=hypothesis,
            )
            result = self.llm_client.chat_json(prompt, role="nli")
            contra = float(result.get("contradiction_score", 0.0))
            ent = float(result.get("entailment_score", 0.0))
            neu = float(result.get("neutral_score", 0.0))
            label_str = result.get("label", "NEUTRAL").upper()
            label = (
                NLILabel.CONTRADICTION if label_str == "CONTRADICTION"
                else NLILabel.ENTAILMENT if label_str == "ENTAILMENT"
                else NLILabel.NEUTRAL
            )
            return {
                "label": label,
                "score": max(contra, ent, neu),
                "all_scores": {
                    NLILabel.CONTRADICTION: contra,
                    NLILabel.ENTAILMENT: ent,
                    NLILabel.NEUTRAL: neu,
                },
            }
        except Exception as e:
            logger.warning(f"LLMNLIDetector failed: {e}; falling back to patterns")
            return _pattern_predict(premise, hypothesis)

    def detect_disagreement(self, text_a: str, text_b: str) -> Dict[str, Any]:
        result = self.predict(text_a, text_b)
        contra = result["all_scores"].get(NLILabel.CONTRADICTION, 0.0)
        return {
            "disagreement": contra >= self.threshold,
            "label": result["label"],
            "contradiction_score": contra,
            "entailment_score": result["all_scores"].get(NLILabel.ENTAILMENT, 0.0),
            "neutral_score": result["all_scores"].get(NLILabel.NEUTRAL, 0.0),
            "threshold": self.threshold,
            "all_scores": result["all_scores"],
        }


def _pattern_predict(premise: str, hypothesis: str) -> Dict[str, Any]:
    """
    Keyword-pattern NLI fallback — used only when no LLM is available.
    Detects contradictions from: different years, different version numbers,
    scope differences (adults/children), and direct negation patterns.
    """
    import re as _re

    p = premise.lower()
    h = hypothesis.lower()

    entity_prediction = _entity_substitution_prediction(premise, hypothesis)
    if entity_prediction:
        return entity_prediction

    # ── 1. Different years anywhere in the two claims ─────────────────
    # Only extract years that are being *asserted*, not years that are
    # being *negated* or *quoted from the user's wrong claim*.
    # Strip: "not in YEAR", "not YEAR", "isn't YEAR", "never in YEAR",
    #        "incorrect ... YEAR", "wrong ... YEAR", "'YEAR'" (quoted).
    def _asserted_years(text: str) -> set:
        """Return years that are positively asserted, not negated/quoted."""
        # Remove "not ..." and similar negation phrases containing a year
        cleaned = _re.sub(
            r"\b(?:not|never|isn't|wasn't|no|incorrect|wrong|rather than|instead of)"
            r"\s+(?:in\s+)?((?:1[0-9]{3}|20[0-9]{2}))\b",
            " ",
            text,
            flags=_re.I,
        )
        # Also remove years that are sandwiched in quotes (e.g. 'in 2012')
        cleaned = _re.sub(r"['\"](?:in\s+)?((?:1[0-9]{3}|20[0-9]{2}))['\"]", " ", cleaned)
        # Also remove "in YYYY" that precede "not" / correction patterns
        # e.g. "released in 2012, not 2017" → keep 2017, drop 2012
        cleaned = _re.sub(
            r"\bin\s+((?:1[0-9]{3}|20[0-9]{2}))\b(?=.*\b(?:not|never|but|rather)\b)",
            " ",
            cleaned,
            flags=_re.I,
        )
        return set(_re.findall(r"\b(1[0-9]{3}|20[0-9]{2})\b", cleaned))

    years_p = _asserted_years(p)
    years_h = _asserted_years(h)
    if years_p and years_h and years_p.isdisjoint(years_h):
        return {
            "label": NLILabel.CONTRADICTION,
            "score": 0.91,
            "all_scores": {NLILabel.CONTRADICTION: 0.91, NLILabel.ENTAILMENT: 0.05, NLILabel.NEUTRAL: 0.04},
        }

    # ── 2. Different version numbers (x.y format) ─────────────────────
    def _versions(text):
        return set(_re.findall(r"\b\d+\.\d+\b", text))

    vers_p = _versions(p)
    vers_h = _versions(h)
    if vers_p and vers_h and vers_p.isdisjoint(vers_h):
        return {
            "label": NLILabel.CONTRADICTION,
            "score": 0.89,
            "all_scores": {NLILabel.CONTRADICTION: 0.89, NLILabel.ENTAILMENT: 0.06, NLILabel.NEUTRAL: 0.05},
        }

    # ── 3. Explicit keyword scope/negation pairs ───────────────────────
    _contra_patterns = [
        ("adults", "children"), ("adult", "child"), ("adults", "paediatric"),
        ("adults", "pediatric"), ("safe", "dangerous"), ("safe", "unsafe"),
        ("effective", "not effective"), ("does not cause", "cause"),
        ("no link", "link"), ("retracted", "claimed"),
        ("secure", "insecure"), ("secure", "vulnerable"),
        ("yes", "no"), ("true", "false"),
        ("increased", "decreased"), ("higher", "lower"),
    ]
    for kw1, kw2 in _contra_patterns:
        if (kw1 in p and kw2 in h) or (kw2 in p and kw1 in h):
            return {
                "label": NLILabel.CONTRADICTION,
                "score": 0.91,
                "all_scores": {NLILabel.CONTRADICTION: 0.91, NLILabel.ENTAILMENT: 0.05, NLILabel.NEUTRAL: 0.04},
            }

    # ── 4. Common content words → entailment ──────────────────────────
    p_words = set(_re.findall(r"\b[a-z0-9]+\b", p))
    h_words = set(_re.findall(r"\b[a-z0-9]+\b", h))
    stop = {"the", "a", "an", "is", "was", "of", "in", "to", "and", "for", "not", "at",
            "s", "it", "its", "be", "are", "has", "have", "that", "this", "or", "by",
            "also", "as", "but", "with", "from", "than", "its", "will"}
    meaningful = (p_words & h_words) - stop
    if len(meaningful) >= 3:
        return {
            "label": NLILabel.ENTAILMENT,
            "score": 0.88,
            "all_scores": {NLILabel.ENTAILMENT: 0.88, NLILabel.CONTRADICTION: 0.04, NLILabel.NEUTRAL: 0.08},
        }

    return {
        "label": NLILabel.NEUTRAL,
        "score": 0.60,
        "all_scores": {NLILabel.NEUTRAL: 0.60, NLILabel.ENTAILMENT: 0.25, NLILabel.CONTRADICTION: 0.15},
    }


class MockNLIDetector:
    """
    NLI detector used in mock/NLI_MODE=mock.
    - With fixtures dict: exact-match lookup for tests (raises KeyError on unknown pair).
    - Without fixtures dict: delegates to _pattern_predict (keyword patterns only).
    This is intentionally simple — it's for tests and FIXTURE mode.
    For real queries in LIVE mode, MADSystem uses LLMNLIDetector instead.
    """

    def __init__(
        self,
        threshold: float = 0.7,
        fixtures: Optional[Dict] = None,
    ):
        self.threshold = threshold
        self._fixtures: Dict = {}
        if fixtures:
            for k, v in fixtures.items():
                norm_key = (k[0].lower().strip(), k[1].lower().strip())
                self._fixtures[norm_key] = v

    def predict(self, premise: str, hypothesis: str) -> Dict[str, Any]:
        if self._fixtures:
            key = (premise.lower().strip(), hypothesis.lower().strip())
            if key not in self._fixtures:
                rev_key = (hypothesis.lower().strip(), premise.lower().strip())
                if rev_key in self._fixtures:
                    entry = self._fixtures[rev_key]
                else:
                    raise KeyError(
                        f"MockNLIDetector: no fixture for pair "
                        f"({premise[:40]!r}, {hypothesis[:40]!r})"
                    )
            else:
                entry = self._fixtures[key]
            return {"label": entry["label"], "score": entry["score"], "all_scores": entry["all_scores"]}

        return _pattern_predict(premise, hypothesis)

    def predict_for_query(
        self, query: str, premise: str, hypothesis: str
    ) -> Dict[str, Any]:
        challenge_prediction = _explicit_challenge_prediction(query, premise, hypothesis)
        if challenge_prediction:
            return challenge_prediction
        target_prediction = _target_resolution_prediction(query, premise, hypothesis)
        return target_prediction or self.predict(premise, hypothesis)

    def detect_disagreement(self, text_a: str, text_b: str) -> Dict[str, Any]:
        result = self.predict(text_a, text_b)
        contra = result["all_scores"].get(NLILabel.CONTRADICTION, 0.0)
        return {
            "disagreement": contra >= self.threshold,
            "label": result["label"],
            "contradiction_score": contra,
            "entailment_score": result["all_scores"].get(NLILabel.ENTAILMENT, 0.0),
            "neutral_score": result["all_scores"].get(NLILabel.NEUTRAL, 0.0),
            "threshold": self.threshold,
            "all_scores": result["all_scores"],
        }


# ------------------------------------------------------------------ #
# Factory                                                              #
# ------------------------------------------------------------------ #

def get_nli_detector():
    """Return MockNLIDetector in mock/demo mode, NLIDetector in transformers mode."""
    if settings.nli_mode == "mock" or settings.demo_mode:
        logger.info("Using MockNLIDetector (mock/demo mode)")
        return MockNLIDetector(threshold=settings.disagreement_threshold)
    logger.info(f"Using NLIDetector (model={settings.nli_model})")
    return NLIDetector(
        model_name=settings.nli_model,
        device=settings.nli_device,
        threshold=settings.disagreement_threshold,
    )
