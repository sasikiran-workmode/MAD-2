"""
test_search_fallbacks.py — OpenCode fallbacks for the search agents.

Covers:
  - Wikipedia 429 (rate limit) → OpenCode retrieves a Wikipedia article,
    results keep the Wikipedia identity (title/link), and no provider-switch
    commentary.
  - DuckDuckGo 429 (rate limit) → OpenCode answers, results keep the plain
    web shape, and no provider-switch commentary.
  - DuckDuckGo redirect links are decoded into real URLs.
"""
import httpx
import pytest
from unittest.mock import patch

from agents.search_agent import ReferenceAgent, WebAgent, SearchAgent


def _rate_limited_client() -> httpx.Client:
    """Context-managed client whose GETs always fail with 429."""
    class _FakeResponse:
        status_code = 429

        def raise_for_status(self):
            request = httpx.Request("GET", "https://unit.test/")
            response = httpx.Response(429, request=request)
            raise httpx.HTTPStatusError(
                "429 Too Many Requests", request=request, response=response
            )

        def json(self):
            return {}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, *args, **kwargs):
            return _FakeResponse()

    return _Client()


def _sentece_results(agent_answer):  # noqa: D401 - helper naming mirrors agent code
    return agent_answer


@pytest.fixture()
def mock_opencode():
    """Patch run_opencode to return a canned answer."""
    with patch("agents.opencode_client.run_opencode") as m:
        m.return_value.ok = True
        m.return_value.text = (
            "WIKIPEDIA_URL: https://en.wikipedia.org/wiki/Canberra\n"
            "ANSWER: Canberra is the capital city of Australia. "
            "It is located in the Australian Capital Territory."
        )
        m.return_value.error = ""
        yield m


class TestWikipediaOpenCodeFallback:
    def test_rate_limited_wikipedia_uses_wikipedia_identity(self, mock_opencode):
        agent = ReferenceAgent()
        agent._make_client = _rate_limited_client

        results = agent.search("What is the capital of Australia?")

        assert results, "fallback should produce results"
        assert all(r["title"].startswith("Wikipedia") for r in results)
        assert all(r["link"].startswith("https://en.wikipedia.org/") for r in results)
        text_blob = " ".join(r["snippet"] for r in results).lower()
        assert "opencode" not in text_blob
        assert "rate limit" not in text_blob
        assert "mimo" not in text_blob
        assert "space-bunny" not in text_blob

    def test_no_provider_commentary_in_failure_reason_path(self, mock_opencode):
        """When OpenCode returns nothing, agent still hides the switch."""
        agent = ReferenceAgent()
        agent._make_client = _rate_limited_client
        mock_opencode.return_value.ok = False
        mock_opencode.return_value.error = "model unreachable"

        results = agent.search("What is the boiling point of water?")
        assert results == []

    def test_rejects_an_answer_without_a_fetched_wikipedia_url(self, mock_opencode):
        agent = ReferenceAgent()
        agent._make_client = _rate_limited_client
        mock_opencode.return_value.text = "Canberra is the capital city of Australia."

        assert agent.search("What is the capital of Australia?") == []


class TestDuckDuckGoOpenCodeFallback:
    def test_rate_limited_duckduckgo_silent_fallback(self, mock_opencode):
        agent = WebAgent()
        agent._make_client = _rate_limited_client

        results = agent.search("What is the capital of Australia?")

        assert results, "fallback should produce results"
        text_blob = " ".join(
            (r["title"] + " " + r["snippet"]) for r in results
        ).lower()
        assert "opencode" not in text_blob
        assert "rate limit" not in text_blob
        assert "duck duck go rate limit" not in text_blob
        assert "space-bunny" not in text_blob

    def test_fallback_uses_web_model(self, mock_opencode):
        agent = WebAgent()
        agent._make_client = _rate_limited_client
        agent.search("What is the capital of Australia?")
        # space-bunny-free is passed via settings.opencode_web_model
        model = mock_opencode.call_args[0][1]
        assert model.endswith("space-bunny-free")


class TestDuckDuckGoLinkDecoding:
    def test_redirect_link_decoded(self):
        from urllib.parse import quote

        href = f"https://duckduckgo.com/l/?uddg={quote('https://example.com/wiki/France', safe='')}&rut=abc"
        decoded = SearchAgent._decode_ddg_link(href)
        assert decoded == "https://example.com/wiki/France"

    def test_plain_link_unchanged(self):
        url = "https://example.com/article"
        assert SearchAgent._decode_ddg_link(url) == url
