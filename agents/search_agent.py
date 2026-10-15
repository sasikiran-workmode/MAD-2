"""
Search agent for web-based evidence retrieval.
All HTTP calls are synchronous (httpx.Client inside a context manager).
Parallelism is handled by QueryRouter via ThreadPoolExecutor.
"""
import html
import re
import time
import urllib.parse
from typing import List, Dict, Any, Optional

import httpx
from loguru import logger

from agents.base_agent import BaseAgent, AgentConfig
from evidence.models import Evidence, Source, Claim
from config import settings


class SearchAgentConfig(AgentConfig):
    """Configuration for search agent."""
    max_results: int = 5
    language: str = "en"
    safe_search: bool = True
    provider: str = "duckduckgo"  # duckduckgo | wikipedia | crossref


class SearchAgent(BaseAgent):
    """Agent that retrieves evidence using web search (synchronous)."""

    _PROVIDER_LABEL = {"duckduckgo": "DuckDuckGo", "wikipedia": "Wikipedia", "crossref": "Crossref"}

    def __init__(self, config: Optional[SearchAgentConfig] = None):
        super().__init__(config or SearchAgentConfig())
        self.config: SearchAgentConfig = self.config

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _make_client(self) -> httpx.Client:
        """Create a fresh synchronous HTTP client (use with `with` statement)."""
        return httpx.Client(timeout=max(self.config.timeout, 45.0))

    def _retry_get(self, client: httpx.Client, url: str, **kwargs) -> httpx.Response:
        """GET with up to 3 retries on timeout / 5xx / 429, with exponential backoff."""
        last_exc: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                resp = client.get(url, **kwargs)
                if resp.status_code == 429:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    if attempt < 3:
                        logger.warning(f"Rate limited ({url[:50]}…), waiting {wait}s")
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()
                if resp.status_code in (500, 502, 503, 504):
                    if attempt < 3:
                        time.sleep(2 ** attempt)
                        continue
                    resp.raise_for_status()
                resp.raise_for_status()
                return resp
            except httpx.TimeoutException as e:
                last_exc = e
                if attempt < 3:
                    time.sleep(2 ** attempt)
            except httpx.HTTPStatusError:
                raise
        raise last_exc or httpx.TimeoutException("All retries exhausted")

    # ------------------------------------------------------------------ #
    # Provider implementations — NO cross-provider fallbacks              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _classify_provider_issue(exc: Exception) -> str:
        """Reduce a provider failure to a short human note (rate limit/timeout/…)."""
        status = getattr(getattr(exc, "response", None), "status_code", None)
        text = str(exc).lower()
        if status == 429 or "429" in text or "rate limit" in text or "too many" in text:
            return "rate limit exceeded (429)"
        if isinstance(exc, httpx.TimeoutException) or "timed out" in text or "timeout" in text:
            return "timed out"
        if status == 404 or "404" in text:
            return "not found (404)"
        if status:
            return f"error {status}"
        return "request error"

    @staticmethod
    def _decode_ddg_link(href: str) -> str:
        """Decode a DuckDuckGo redirect link (/l/?uddg=<encoded>) into the real URL."""
        try:
            if "duckduckgo.com/l/" in href or "//duckduckgo.com" in href:
                parsed = urllib.parse.urlparse(href)
                params = urllib.parse.parse_qs(parsed.query)
                uddg = params.get("uddg", [None])[0]
                if uddg:
                    return urllib.parse.unquote(uddg)
        except Exception:
            pass
        return href

    def _duckduckgo_search(self, query: str) -> List[Dict[str, Any]]:
        """DuckDuckGo HTML search — free, no API key required.

        If DuckDuckGo is unavailable (rate limit, timeout, server error),
        an OpenCode model answers instead. Results are presented under the
        DuckDuckGo (web) agent identity with no provider commentary."""
        try:
            with self._make_client() as client:
                resp = self._retry_get(
                    client,
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "evidence-mad/1.0"},
                )
            matches = re.findall(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                resp.text,
                re.I | re.S,
            )
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</a>',
                resp.text,
                re.I | re.S,
            )
        except Exception as exc:
            issue = self._classify_provider_issue(exc)
            logger.debug(f"DuckDuckGo retrieval issue ({issue}): {exc}")
            return self._opencode_web_fallback(query, issue)

        results = []
        for i, (link, title) in enumerate(matches[: self.config.max_results]):
            results.append({
                "title": re.sub(r"<[^>]+>", "", html.unescape(title)).strip(),
                "snippet": re.sub(
                    r"<[^>]+>",
                    "",
                    html.unescape(snippets[i] if i < len(snippets) else title),
                ).strip(),
                "link": self._decode_ddg_link(html.unescape(link)),
            })
        if results:
            return results
        # No result links found (blocked/challenge page) — use the fallback
        return self._opencode_web_fallback(query)

    def _wikipedia_search(self, query: str) -> List[Dict[str, Any]]:
        """Wikipedia free public API — OpenCode fills in whenever Wikipedia
        itself is unavailable (rate limit, timeout, network or parse error).
        Results keep the Wikipedia identity; no provider switch is surfaced."""
        try:
            with self._make_client() as client:
                resp = self._retry_get(
                    client,
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "utf8": 1,
                        "srlimit": self.config.max_results,
                    },
                    headers={"User-Agent": "EvidenceMAD/1.0 research contact@example.com"},
                )
            items = resp.json().get("query", {}).get("search", [])
            results = [
                {
                    "title": item.get("title", ""),
                    "snippet": re.sub(r"<[^>]+>", "", html.unescape(item.get("snippet", ""))).strip(),
                    "link": f"https://en.wikipedia.org/?curid={item.get('pageid', '')}",
                }
                for item in items
            ]
            if results:
                return results
            issue = self._classify_provider_issue(
                RuntimeError("empty result list")
            )
            logger.debug("Wikipedia returned no results")
            return self._opencode_wiki_fallback(query, issue)
        except Exception as exc:
            issue = self._classify_provider_issue(exc)
            logger.debug(f"Wikipedia retrieval issue ({issue}): {exc}")
            return self._opencode_wiki_fallback(query, issue)

    def _crossref_search(self, query: str) -> List[Dict[str, Any]]:
        """Crossref scholarly metadata API with an OpenCode search fallback."""
        try:
            with self._make_client() as client:
                resp = self._retry_get(
                    client,
                    "https://api.crossref.org/works",
                    params={
                        "query.bibliographic": query,
                        "rows": self.config.max_results,
                        "select": "title,URL,container-title,published",
                    },
                    headers={"User-Agent": "EvidenceMAD/1.0 (mailto:research@example.com)"},
                )
            items = resp.json().get("message", {}).get("items", [])
            results = []
            for item in items:
                title = (item.get("title") or ["Untitled"])[0]
                venue = (item.get("container-title") or [""])[0]
                published = item.get("published", {}).get("date-parts", [[""]])[0]
                year = published[0] if published else ""
                results.append({
                    "title": title,
                    "snippet": (
                        f"Scholarly work indexed by Crossref"
                        f"{f' · {venue}' if venue else ''}"
                        f"{f' · {year}' if year else ''}"
                    ),
                    "link": item.get("URL", ""),
                })
            if results:
                return results
            return self._opencode_scholarly_fallback(query, "returned no results")
        except Exception as exc:
            issue = self._classify_provider_issue(exc)
            logger.debug(f"Crossref retrieval issue ({issue}): {exc}")
            return self._opencode_scholarly_fallback(query, issue)

    def _opencode_scholarly_fallback(
        self, query: str, issue: str = "unavailable"
    ) -> List[Dict[str, Any]]:
        """Use OpenCode to retrieve a scholarly source when Crossref fails."""
        from agents.opencode_client import run_opencode

        fallback_note = f"Crossref {issue} — OpenCode fallback used"
        model = settings.opencode_scholarly_model or settings.opencode_model
        prompt = f"""Use websearch to find a relevant scholarly source for this question:
{query}

Use webfetch to read the selected source. Prefer a DOI landing page, arXiv,
or an academic publisher. Answer only from the fetched source; do not use prior
knowledge or another source. Return exactly these three lines:
SCHOLARLY_URL: <the fetched https URL>
TITLE: <the source title>
ANSWER: <a factual 2-3 sentence answer>

If you cannot search and fetch a relevant scholarly source, return exactly:
SCHOLARLY_SOURCE_NOT_RETRIEVED"""
        result = run_opencode(prompt, model, settings.opencode_timeout)
        if result.ok and result.text:
            output = result.text.strip()
            url_match = re.search(r"^SCHOLARLY_URL:\s*(https://[^\s]+)\s*$", output, re.MULTILINE)
            title_match = re.search(r"^TITLE:\s*(.+)$", output, re.MULTILINE)
            answer_match = re.search(r"^ANSWER:\s*(.+)$", output, re.MULTILINE | re.DOTALL)
            if url_match and title_match and answer_match:
                answer = answer_match.group(1).strip()
                sentences = [
                    sentence.strip()
                    for sentence in re.split(r'(?<=[.!?])\s+', answer)
                    if sentence.strip()
                ]
                if sentences:
                    return [
                        {
                            "title": title_match.group(1).strip(),
                            "snippet": sentence,
                            "link": url_match.group(1),
                            "via_fallback": fallback_note,
                        }
                        for sentence in sentences[:self.config.max_results]
                    ]
            logger.debug("OpenCode scholarly fallback did not return a fetched source")
        logger.debug(
            f"OpenCode scholarly fallback failed: {result.error if not result.ok else 'empty'}"
        )
        return []

    def _opencode_wiki_fallback(self, query: str, issue: str = "unavailable") -> List[Dict[str, Any]]:
        """OpenCode Wikipedia-search fallback used when the API is unavailable.

        OpenCode must search and fetch an English Wikipedia article before
        answering. A response without that retrieved article URL is rejected,
        rather than being treated as an answer from model knowledge.
        """
        from agents.opencode_client import run_opencode

        provider_label = self._PROVIDER_LABEL.get(self.config.provider, "Wikipedia")
        fallback_note = f"{provider_label} {issue} — OpenCode fallback used"

        prompt = f"""Use websearch to find the most relevant English Wikipedia article for this question:
{query}

Then use webfetch to read that exact Wikipedia article. Answer only from the
retrieved article; do not use prior knowledge or another source. Return exactly
these two lines:
WIKIPEDIA_URL: <the fetched https://en.wikipedia.org/wiki/... URL>
ANSWER: <a factual 2-3 sentence answer>

If you cannot search and fetch a relevant English Wikipedia article, return
exactly: WIKIPEDIA_NOT_RETRIEVED"""
        result = run_opencode(prompt, settings.opencode_wiki_model, settings.opencode_timeout)
        if result.ok and result.text:
            output = result.text.strip()
            url_match = re.search(
                r"^WIKIPEDIA_URL:\s*(https://en\.wikipedia\.org/wiki/[^\s]+)\s*$",
                output,
                re.MULTILINE,
            )
            answer_match = re.search(r"^ANSWER:\s*(.+)$", output, re.MULTILINE | re.DOTALL)
            if url_match and answer_match:
                answer = answer_match.group(1).strip()
                sentences = [
                    sentence.strip()
                    for sentence in re.split(r'(?<=[.!?])\s+', answer)
                    if sentence.strip()
                ]
                if sentences:
                    return [
                        {
                            "title": f"Wikipedia - {query}" if i == 0 else "Wikipedia (continued)",
                            "snippet": sentence,
                            "link": url_match.group(1),
                            "via_fallback": fallback_note,
                        }
                        for i, sentence in enumerate(sentences[:self.config.max_results])
                    ]
            logger.debug("OpenCode wiki fallback did not return a fetched Wikipedia article")
        # If OpenCode cannot retrieve Wikipedia, report no relevant results.
        logger.debug(f"OpenCode wiki fallback failed: {result.error if not result.ok else 'empty'}")
        return []

    def _opencode_web_fallback(self, query: str, issue: str = "unavailable") -> List[Dict[str, Any]]:
        """OpenCode answer used when DuckDuckGo is unavailable.

        Results keep the plain web-result shape so they appear under the
        DuckDuckGo (web) agent. Each row carries a `via_fallback` note so
        the API/UI can surface a small fallback message.
        """
        from agents.opencode_client import run_opencode

        provider_label = self._PROVIDER_LABEL.get(self.config.provider, "DuckDuckGo")
        fallback_note = f"{provider_label} {issue} — OpenCode fallback used"

        prompt = (
            f"Answer this question factually in 2-4 short sentences, citing the "
            f"source or site where each fact is commonly published. "
            f"Question: {query}"
        )
        result = run_opencode(prompt, settings.opencode_web_model, settings.opencode_timeout)
        if result.ok and result.text:
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', result.text) if s.strip()]
            results = []
            for i, sent in enumerate(sentences[: self.config.max_results]):
                results.append({
                    "title": f"{query.capitalize()}" if i == 0 else "Web (continued)",
                    "snippet": sent,
                    "link": "",
                    "via_fallback": fallback_note,
                })
            if results:
                return results
        logger.debug(f"OpenCode web fallback also failed: {result.error if not result.ok else 'empty'}")
        return []

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Dispatch to the configured provider.

        Every provider fills in via OpenCode on rate limits, timeouts, empty
        results, or network errors, and tags fallback results with `via_fallback`.
        """
        if self.config.provider == "wikipedia":
            return self._wikipedia_search(query)
        if self.config.provider == "crossref":
            return self._crossref_search(query)
        # Default: DuckDuckGo
        return self._duckduckgo_search(query)

    def retrieve(self, query: str) -> Evidence:
        """
        Retrieve evidence for a query using web search.

        Args:
            query: User query (passed verbatim — no suffix)

        Returns:
            Evidence object
        """
        self.logger.info(f"Retrieving evidence for: {query!r}")

        search_results = self.search(query)

        sources = []
        retrieved_texts = []
        for result in search_results:
            source = Source(
                url=result.get("link", ""),
                title=result.get("title", ""),
                snippet=result.get("snippet", ""),
                metadata={"search_query": query},
            )
            sources.append(source)
            retrieved_texts.append(f"{source.title}: {source.snippet}")

        combined_text = "\n\n".join(retrieved_texts)
        claims = self.extract_claims(combined_text, sources)
        answer = self.generate_answer(query, claims, sources)

        fallback_note = next(
            (r.get("via_fallback") for r in search_results if r.get("via_fallback")),
            None,
        )
        metadata = {
            "search_results_count": len(search_results),
            "provider": self.config.provider,
        }
        if fallback_note:
            metadata["opencode_fallback"] = True
            metadata["fallback_detail"] = fallback_note

        return Evidence(
            agent_id=self.agent_id,
            query=query,
            answer=answer,
            claims=claims,
            sources=sources,
            retrieved_text=combined_text,
            metadata=metadata,
        )


# ------------------------------------------------------------------ #
# Concrete agent classes (Task 17 defines routing logic)             #
# ------------------------------------------------------------------ #

class WebAgent(SearchAgent):
    """Primary web agent using DuckDuckGo."""

    def __init__(self):
        config = SearchAgentConfig(
            agent_id="web_agent",
            name="WebAgent",
            description="Primary web search agent (DuckDuckGo)",
            max_results=5,
            provider="duckduckgo",
        )
        super().__init__(config)


class ReferenceAgent(SearchAgent):
    """Reference agent using Wikipedia."""

    def __init__(self):
        config = SearchAgentConfig(
            agent_id="reference_agent",
            name="ReferenceAgent",
            description="Reference search agent (Wikipedia)",
            max_results=5,
            provider="wikipedia",
        )
        super().__init__(config)


class ScholarlyAgent(SearchAgent):
    """Scholarly agent using Crossref."""

    def __init__(self):
        config = SearchAgentConfig(
            agent_id="scholarly_agent",
            name="ScholarlyAgent",
            description="Scholarly search agent (Crossref)",
            max_results=5,
            provider="crossref",
        )
        super().__init__(config)


# Keep legacy names as aliases so existing imports don't break
SearchAgentA = WebAgent
SearchAgentB = ReferenceAgent
SearchAgentC = ScholarlyAgent
