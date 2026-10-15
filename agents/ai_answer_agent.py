"""
AI Answer Agent: Gemini (primary) with OpenCode CLI fallback.

This agent runs on every LIVE-mode query in parallel with the search agents.
It does NOT subclass BaseAgent, does NOT use EvidenceNormalizer, and does NOT
touch llm_client.py (Groq). It returns one AgentEvidence directly.
"""
from loguru import logger

from agents.gemini_client import generate_grounded, GeminiError
from agents.opencode_client import run_opencode
from config import settings
from evidence.models import AgentEvidence, EvidenceStatus, NormalizedClaim, Source


AGENT_ID = 'ai_answer_agent'

PROMPT_TEMPLATE = (
    'Answer the following question accurately in at most three sentences. '
    'Do not invent sources or citations.\n\nQuestion: {query}'
)


def build_prompt(query: str) -> str:
    """Build the prompt sent to both Gemini and OpenCode."""
    return PROMPT_TEMPLATE.format(query=query)


def _short(text: str, limit: int = 600) -> str:
    """
    Trim text to at most `limit` characters, cutting at a sentence boundary.

    The NLI model compares this against one-sentence claims from search agents;
    long answers compare badly. The untrimmed answer is stored in metadata['full_answer'].
    """
    text = ' '.join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind('. '), cut.rfind('? '), cut.rfind('! '))
    return cut[:end + 1] if end > 100 else cut


class AIAnswerAgent:
    """Gemini-then-OpenCode agent returning one AgentEvidence."""

    def get_evidence(self, query: str) -> AgentEvidence:
        """
        Get evidence for a query. Nothing may escape into MADSystem.solve().

        Returns:
            AgentEvidence with status OK or RETRIEVAL_FAILED
        """
        try:
            return self._run(query)
        except Exception as exc:
            logger.error(f'ai_answer_agent crashed: {exc}', exc_info=True)
            return self._failed(
                query, f'Unexpected error: {exc}', {'backend_used': 'none'}
            )

    def _run(self, query: str) -> AgentEvidence:
        prompt = build_prompt(query)
        gemini_error = ''

        # -- Try Gemini first --
        try:
            text, found = generate_grounded(
                settings.gemini_api_key,
                settings.gemini_model,
                prompt,
                settings.gemini_timeout,
            )
            sources = [
                Source(
                    url=s['url'],
                    title=s['title'],
                    snippet='',
                    metadata={'provider': 'gemini_grounding'},
                )
                for s in found
            ]
            if not sources:
                sources = [
                    Source(
                        url='',
                        title=f'Gemini ({settings.gemini_model})',
                        snippet=text[:200],
                        metadata={'provider': 'gemini'},
                    )
                ]
            return self._ok(query, text, sources, {
                'backend_used': 'gemini',
                'fallback_occurred': False,
                'grounded': bool(found),
            })
        except GeminiError as exc:
            gemini_error = str(exc)
            logger.warning(f'Gemini failed, using OpenCode fallback: {gemini_error}')

        # -- Fallback to OpenCode --
        result = run_opencode(prompt, settings.opencode_model, settings.opencode_timeout)
        if result.ok:
            src = Source(
                url='',
                title=f'OpenCode CLI ({settings.opencode_model})',
                snippet=result.text[:200],
                metadata={'provider': 'opencode'},
            )
            return self._ok(query, result.text, [src], {
                'backend_used': 'opencode_fallback',
                'fallback_occurred': True,
                'gemini_error': gemini_error,
            })

        # -- Both failed --
        return self._failed(
            query,
            f'Gemini failed ({gemini_error}); OpenCode failed ({result.error})',
            {
                'backend_used': 'none',
                'fallback_occurred': True,
                'gemini_error': gemini_error,
                'opencode_error': result.error,
            },
        )

    # -- helpers --

    def _ok(self, query, text, sources, meta):
        meta['full_answer'] = text
        claim = NormalizedClaim(text=_short(text), source=sources[0])
        return AgentEvidence(
            agent_id=AGENT_ID,
            query=query,
            status=EvidenceStatus.OK,
            claims=[claim],
            sources=sources,
            raw_results_count=len(sources),
            metadata=meta,
        )

    def _failed(self, query, reason, meta):
        return AgentEvidence(
            agent_id=AGENT_ID,
            query=query,
            status=EvidenceStatus.RETRIEVAL_FAILED,
            failure_reason=reason,
            metadata=meta,
        )
