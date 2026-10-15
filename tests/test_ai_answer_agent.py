"""
Tests for the AI Answer Agent.

All tests patch network calls (generate_grounded / run_opencode).
No test touches Gemini or OpenCode for real.
"""
import pytest
from unittest.mock import patch, MagicMock

from agents.ai_answer_agent import AIAnswerAgent, build_prompt, AGENT_ID, _short
from agents.gemini_client import GeminiError
from agents.opencode_client import OpenCodeResult
from evidence.models import (
    AgentEvidence, EvidenceStatus, EvidenceState,
    NormalizedClaim, Source, NLILabel,
)
from evidence.aggregator import EvidenceAggregator
from evidence.disagreement_detector import MockNLIDetector


# ── Helpers ─────────────────────────────────────────────────────────

def make_search_ev(agent_id: str, claim_text: str) -> AgentEvidence:
    """Create a usable AgentEvidence for aggregator tests."""
    src = Source(url=f"https://{agent_id}.example.com", title=agent_id, snippet="test")
    nc = NormalizedClaim(text=claim_text, source=src)
    return AgentEvidence(
        agent_id=agent_id, query="q",
        status=EvidenceStatus.OK, claims=[nc], sources=[src],
    )


def make_failed_ev(agent_id: str) -> AgentEvidence:
    return AgentEvidence(
        agent_id=agent_id, query="q",
        status=EvidenceStatus.RETRIEVAL_FAILED,
        failure_reason="timeout",
    )


# ── Unit tests ──────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_contains_query(self):
        prompt = build_prompt("What is Python?")
        assert "What is Python?" in prompt

    def test_contains_length_limit(self):
        prompt = build_prompt("test")
        assert "three sentences" in prompt.lower()


class TestShort:
    def test_short_text_unchanged(self):
        assert _short("Hello world.") == "Hello world."

    def test_long_text_trimmed(self):
        long = "This is a sentence. " * 50  # way over 600
        result = _short(long, limit=100)
        assert len(result) <= 100
        assert result.endswith(". ")

    def test_no_good_boundary(self):
        long = "x" * 700
        result = _short(long, limit=600)
        assert len(result) == 600


class TestGeminiSuccess:
    """Gemini succeeds: status OK, backend_used=gemini, OpenCode never called."""

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_gemini_success(self, mock_gemini, mock_opencode):
        mock_gemini.return_value = (
            "Python is a programming language.",
            [{'url': 'https://python.org', 'title': 'Python'}],
        )
        agent = AIAnswerAgent()
        ev = agent.get_evidence("What is Python?")

        assert ev.status == EvidenceStatus.OK
        assert ev.agent_id == AGENT_ID
        assert ev.metadata['backend_used'] == 'gemini'
        assert ev.metadata['fallback_occurred'] is False
        assert ev.metadata['grounded'] is True
        assert len(ev.claims) == 1
        assert "programming language" in ev.claims[0].text
        mock_opencode.assert_not_called()

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_gemini_no_grounding(self, mock_gemini, mock_opencode):
        """Gemini returns text but no grounding URLs."""
        mock_gemini.return_value = ("Answer text.", [])
        agent = AIAnswerAgent()
        ev = agent.get_evidence("test")

        assert ev.status == EvidenceStatus.OK
        assert ev.metadata['grounded'] is False
        assert ev.sources[0].url == ''
        mock_opencode.assert_not_called()


class TestGeminiFailOpenCodeFallback:
    """Gemini fails, OpenCode fallback works."""

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_fallback_to_opencode(self, mock_gemini, mock_opencode):
        mock_gemini.side_effect = GeminiError("429 quota exceeded")
        mock_opencode.return_value = OpenCodeResult(True, text="OpenCode answer.")

        agent = AIAnswerAgent()
        ev = agent.get_evidence("test")

        assert ev.status == EvidenceStatus.OK
        assert ev.metadata['backend_used'] == 'opencode_fallback'
        assert ev.metadata['fallback_occurred'] is True
        assert ev.metadata['gemini_error'] == '429 quota exceeded'
        assert ev.sources[0].url == ''  # OpenCode has no URL
        assert "OpenCode answer" in ev.claims[0].text


class TestSamePrompt:
    """Both backends receive the same prompt."""

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_same_prompt_sent(self, mock_gemini, mock_opencode):
        mock_gemini.side_effect = GeminiError("fail")
        mock_opencode.return_value = OpenCodeResult(True, text="answer")

        agent = AIAnswerAgent()
        agent.get_evidence("What is Python?")

        gemini_prompt = mock_gemini.call_args[0][2]  # 3rd positional arg
        opencode_prompt = mock_opencode.call_args[0][0]  # 1st positional arg
        assert gemini_prompt == opencode_prompt
        assert "What is Python?" in gemini_prompt


class TestBothFail:
    """Both Gemini and OpenCode fail: RETRIEVAL_FAILED, no exception."""

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_both_fail(self, mock_gemini, mock_opencode):
        mock_gemini.side_effect = GeminiError("API key invalid")
        mock_opencode.return_value = OpenCodeResult(False, error="not on PATH")

        agent = AIAnswerAgent()
        ev = agent.get_evidence("test")

        assert ev.status == EvidenceStatus.RETRIEVAL_FAILED
        assert "API key invalid" in ev.failure_reason
        assert "not on PATH" in ev.failure_reason
        assert ev.metadata['backend_used'] == 'none'
        assert ev.metadata['fallback_occurred'] is True

    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_both_fail_no_exception(self, mock_gemini, mock_opencode):
        """Ensure no exception escapes even when both fail."""
        mock_gemini.side_effect = GeminiError("timeout")
        mock_opencode.return_value = OpenCodeResult(False, error="empty output")

        agent = AIAnswerAgent()
        # This must not raise
        ev = agent.get_evidence("test")
        assert ev.agent_id == AGENT_ID


class TestNoGeminiKey:
    """Empty GEMINI_API_KEY goes straight to fallback."""

    @patch('agents.ai_answer_agent.settings')
    @patch('agents.ai_answer_agent.run_opencode')
    @patch('agents.ai_answer_agent.generate_grounded')
    def test_empty_key_fallback(self, mock_gemini, mock_opencode, mock_settings):
        mock_settings.gemini_api_key = ''
        mock_settings.gemini_model = 'gemini-2.5-flash'
        mock_settings.gemini_timeout = 20
        mock_settings.opencode_model = 'test-model'
        mock_settings.opencode_timeout = 45

        mock_gemini.side_effect = GeminiError("GEMINI_API_KEY not set")
        mock_opencode.return_value = OpenCodeResult(True, text="fallback answer")

        agent = AIAnswerAgent()
        ev = agent.get_evidence("test")

        assert ev.status == EvidenceStatus.OK
        assert ev.metadata['backend_used'] == 'opencode_fallback'


class TestUnexpectedCrash:
    """Outer try/except catches all unexpected exceptions."""

    @patch('agents.ai_answer_agent.generate_grounded')
    def test_unexpected_exception(self, mock_gemini):
        mock_gemini.side_effect = RuntimeError("something terrible")

        agent = AIAnswerAgent()
        ev = agent.get_evidence("test")

        assert ev.status == EvidenceStatus.RETRIEVAL_FAILED
        assert 'Unexpected error' in ev.failure_reason
        assert ev.metadata['backend_used'] == 'none'


class TestAggregatorPairCounts:
    """Aggregator pair counts with the AI agent."""

    def test_three_usable_agents_three_pairs(self):
        """3 usable agents (Web, Ref, AI) produce 3 NLI pairs."""
        nli = MockNLIDetector(threshold=0.7)
        agg = EvidenceAggregator(nli_detector=nli)
        evs = [
            make_search_ev("web_agent", "Python is a language."),
            make_search_ev("reference_agent", "Python is a language."),
            make_search_ev("ai_answer_agent", "Python is a language."),
        ]
        decision = agg.decide(evs)
        assert len(decision.pairwise) == 3
        assert len(decision.usable_agents) == 3

    def test_four_usable_agents_six_pairs(self):
        """4 usable agents (Web, Ref, Scholarly, AI) produce 6 NLI pairs."""
        nli = MockNLIDetector(threshold=0.7)
        agg = EvidenceAggregator(nli_detector=nli)
        evs = [
            make_search_ev("web_agent", "Python is a language."),
            make_search_ev("reference_agent", "Python is a language."),
            make_search_ev("scholarly_agent", "Python is a language."),
            make_search_ev("ai_answer_agent", "Python is a language."),
        ]
        decision = agg.decide(evs)
        assert len(decision.pairwise) == 6
        assert len(decision.usable_agents) == 4

    def test_failed_ai_agent_drops_pair_count(self):
        """A failed AI agent leaves 2 usable agents and 1 pair."""
        nli = MockNLIDetector(threshold=0.7)
        agg = EvidenceAggregator(nli_detector=nli)
        evs = [
            make_search_ev("web_agent", "Python is a language."),
            make_search_ev("reference_agent", "Python is a language."),
            make_failed_ev("ai_answer_agent"),
        ]
        decision = agg.decide(evs)
        assert len(decision.pairwise) == 1
        assert len(decision.usable_agents) == 2
        assert any(f['agent_id'] == 'ai_answer_agent' for f in decision.failed_agents)
