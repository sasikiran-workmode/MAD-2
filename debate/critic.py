"""
Critic agent for the debate module.
Task 13: No more except→_demo_* fallback; LLMError propagates.
"""
from typing import List, Optional
from loguru import logger

from evidence.models import AgentEvidence, ConflictType, DebateArgument
from llm_client import LLMClient, LLMError


class Critic:
    """
    Critiques proposals by identifying logical weaknesses,
    unsupported claims, and reasoning gaps.
    LLMError propagates — no silent fallback.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None, run_mode: str = "live"):
        self.llm_client = llm_client
        self.run_mode = run_mode

    def critique(
        self,
        query: str,
        proposal: DebateArgument,
        evidence_list: List[AgentEvidence],
        conflict_type: ConflictType,
        top_conflict: dict,
        round_number: int,
    ) -> List[DebateArgument]:
        """
        Generate critiques of a proposal.

        Returns:
            List of critique DebateArguments

        Raises:
            LLMError: if LLM call fails
        """
        if self.run_mode == "fixture" or not self.llm_client:
            return self._fixture_critique(query, proposal, conflict_type, round_number)

        return self._llm_critique(
            query, proposal, evidence_list, conflict_type, top_conflict, round_number
        )

    def _llm_critique(
        self,
        query: str,
        proposal: DebateArgument,
        evidence_list: List[AgentEvidence],
        conflict_type: ConflictType,
        top_conflict: dict,
        round_number: int,
    ) -> List[DebateArgument]:
        """Generate critiques using LLM. Raises LLMError on failure."""
        claim_a = top_conflict.get("claim_a")
        claim_b = top_conflict.get("claim_b")
        claim_a_text = claim_a.text if claim_a else "Claim A"
        claim_b_text = claim_b.text if claim_b else "Claim B"
        agent_a_id = top_conflict.get("agent_a_id", "agent_a")
        agent_b_id = top_conflict.get("agent_b_id", "agent_b")

        prompt = f"""You are a critical analyst in a structured debate.

QUESTION: {query}
CONFLICT TYPE: {conflict_type.value}

ORIGINAL CLAIMS:
- {agent_a_id}: {claim_a_text}
- {agent_b_id}: {claim_b_text}

PROPOSAL TO CRITIQUE:
{proposal.content}

Return plain text only. Do not use Markdown, # characters, bullets, asterisks,
or tables. Use exactly this structure:

CRITIQUE 1
ISSUE
<one specific weakness or "No substantive weakness found">
WHY IT MATTERS
<brief explanation>
IMPROVEMENT
<specific improvement>

CRITIQUE 2
ISSUE
<a different specific weakness or "No substantive weakness found">
WHY IT MATTERS
<brief explanation>
IMPROVEMENT
<specific improvement>

SUBSTANTIVE_OBJECTION: true or false"""

        response = self.llm_client.chat(prompt, role="critic")

        # Extract substantive_objection flag
        import re
        sub_obj = True  # default assume yes
        sub_match = re.search(r"SUBSTANTIVE_OBJECTION:\s*(true|false)", response, re.I)
        if sub_match:
            sub_obj = sub_match.group(1).lower() == "true"

        # Keep the display content clean while preserving the objection flag in metadata.
        display_response = re.sub(
            r"\n?SUBSTANTIVE_OBJECTION:\s*(true|false)\s*$", "", response,
            flags=re.I,
        ).strip()
        parts = re.split(r"^\s*CRITIQUE\s+2\s*:?[ \t]*\n?", display_response, maxsplit=1, flags=re.I | re.M)
        content_1 = re.sub(
            r"^\s*CRITIQUE\s+1\s*:?[ \t]*\n?", "", parts[0], flags=re.I
        ).strip()
        content_2 = parts[1].strip() if len(parts) == 2 else "No second critique was returned."

        return [
            DebateArgument(
                round_number=round_number,
                role="critic",
                agent_id="critic_1",
                content=content_1,
                evidence_refs=[agent_a_id],
                conflict_type=conflict_type,
                strategy_used="critique" + ("_substantive" if sub_obj else "_no_objection"),
            ),
            DebateArgument(
                round_number=round_number,
                role="critic",
                agent_id="critic_2",
                content=content_2,
                evidence_refs=[agent_b_id],
                conflict_type=conflict_type,
                strategy_used="critique",
            ),
        ]

    def _fixture_critique(
        self,
        query: str,
        proposal: DebateArgument,
        conflict_type: ConflictType,
        round_number: int,
    ) -> List[DebateArgument]:
        """Realistic critiques for FIXTURE mode."""
        if conflict_type == ConflictType.TEMPORAL:
            c1 = (
                f"Critique 1 (Round {round_number}): The proposal correctly identifies the temporal gap "
                f"but does not weigh source authority. The more recent official source (2020) "
                f"reflects current policy, while the 1986 reference describes a superseded framework. "
                f"The proposal should explicitly state which is the operative answer."
            )
            c2 = (
                f"Critique 2 (Round {round_number}): The proposal omits that both dates may be correct "
                f"— 1986 was a real policy, 2020 is the current one. "
                f"The answer depends entirely on whether the query asks about the original or current policy."
            )
        elif conflict_type == ConflictType.VERSION:
            c1 = (
                f"Critique 1 (Round {round_number}): The proposal identifies the version mismatch "
                f"but does not confirm whether both sources are accurate for their stated versions. "
                f"Version 3.13 and 3.14 are distinct releases — both claims can be simultaneously correct."
            )
            c2 = (
                f"Critique 2 (Round {round_number}): The proposal should clarify that the query asked "
                f"specifically about 3.13. Source B's information about 3.14 is technically accurate "
                f"but out of scope for this query."
            )
        elif conflict_type == ConflictType.CONTEXTUAL:
            c1 = (
                f"Critique 1 (Round {round_number}): The proposal acknowledges scope differences "
                f"but does not explicitly state the conditions. "
                f"The answer should specify: safe for adults (18+), contraindicated for children."
            )
            c2 = (
                f"Critique 2 (Round {round_number}): The proposal could strengthen the argument "
                f"by citing the specific mechanism — e.g. Reye's syndrome risk in children — "
                f"rather than treating this as a simple disagreement."
            )
        else:
            c1 = (
                f"Critique 1 (Round {round_number}): The proposal identifies the conflict "
                f"but does not evaluate source credibility. "
                f"Peer-reviewed sources should be weighted higher than informal publications."
            )
            c2 = (
                f"Critique 2 (Round {round_number}): The proposal lacks a concrete resolution. "
                f"It should recommend the claim supported by the highest-authority source "
                f"while acknowledging the conflicting claim exists."
            )
        return [
            DebateArgument(
                round_number=round_number, role="critic", agent_id="critic_1",
                content=c1, conflict_type=conflict_type, strategy_used="critique_substantive",
            ),
            DebateArgument(
                round_number=round_number, role="critic", agent_id="critic_2",
                content=c2, conflict_type=conflict_type, strategy_used="critique_substantive",
            ),
        ]
