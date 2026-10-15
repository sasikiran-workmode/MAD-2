"""
FastAPI application for the Multi-Agent Debate framework.
Task 4: keeps endpoints async def but calls the sync pipeline
        via run_in_executor so we don't block the server event loop.
"""
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from loguru import logger

from app import solve as sync_solve

app = FastAPI(
    title="Multi-Agent Debate API",
    description="Evidence-triggered debate with conflict classification",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class QueryRequest(BaseModel):
    """Request model for /solve endpoint."""
    query: str = Field(..., description="The question to answer")
    demo_mode: bool = Field(default=False, description="Use fixture/demo mode")


class AgentEvidenceOut(BaseModel):
    """Per-agent evidence in the response."""
    agent_id: str
    status: str
    claim: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    date: Optional[str] = None
    version: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PairwiseOut(BaseModel):
    """NLI pairwise comparison result."""
    agent_a_id: str
    agent_b_id: str
    label: str
    contradiction_score: float
    entailment_score: float


class DebateArgumentOut(BaseModel):
    """Single debate argument."""
    round_number: int
    role: str
    content: str


class QueryResponse(BaseModel):
    """Response model for /solve endpoint."""
    query: str
    answer: str
    reasoning: str
    evidence_state: str
    rationale: str = ''
    debate_triggered: bool
    conflict_type: Optional[str] = None
    conflict: Optional[Dict[str, Any]] = None
    agent_evidence: List[AgentEvidenceOut] = Field(default_factory=list)
    failed_agents: List[Dict[str, str]] = Field(default_factory=list)
    pairwise: List[PairwiseOut] = Field(default_factory=list)
    debate_rounds: List[DebateArgumentOut] = Field(default_factory=list)
    judge: Optional[Dict[str, Any]] = None
    sources: list = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "Multi-Agent Debate API",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/solve", response_model=QueryResponse)
@app.post("/solve", response_model=QueryResponse)
async def solve_query(request: QueryRequest):
    """
    Solve a query using the Multi-Agent Debate system (sync pipeline via threadpool).
    """
    try:
        logger.info(f"API request: {request.query!r}")

        loop = asyncio.get_event_loop()
        trace = await loop.run_in_executor(
            None, lambda: sync_solve(request.query, demo_mode=request.demo_mode)
        )

        if trace.error:
            raise HTTPException(status_code=500, detail=trace.error)

        decision = trace.evidence_decision
        answer_obj = trace.final_answer

        # -- Build per-agent evidence rows --
        agent_rows = []
        for e in trace.agent_evidence:
            c = e.claims[0] if e.claims else None
            agent_rows.append(AgentEvidenceOut(
                agent_id=e.agent_id,
                status=e.status.value,
                claim=c.text if c else None,
                source_title=c.source.title if c else None,
                source_url=c.source.url if c else None,
                date=c.date if c else None,
                version=c.version if c else None,
                failure_reason=e.failure_reason,
                metadata=e.metadata,
            ))

        # -- Build pairwise NLI rows --
        pairs = [
            PairwiseOut(
                agent_a_id=p.agent_a_id,
                agent_b_id=p.agent_b_id,
                label=p.label.value,
                contradiction_score=p.contradiction_score,
                entailment_score=p.entailment_score,
            )
            for p in (decision.pairwise if decision else [])
        ]

        # -- Build debate round rows --
        rounds = []
        if trace.debate_outcome:
            for r in trace.debate_outcome.rounds:
                args = (
                    ([r.proposer_argument] if r.proposer_argument else [])
                    + list(r.critic_arguments)
                    + ([r.reviser_argument] if r.reviser_argument else [])
                )
                rounds += [
                    DebateArgumentOut(
                        round_number=r.round_number, role=a.role, content=a.content,
                    )
                    for a in args
                ]

        # -- Build conflict dict --
        conflict = None
        if trace.conflict:
            k = trace.conflict
            conflict = {
                'type': k.type.value,
                'confidence': k.confidence,
                'explanation': k.explanation,
                'claim_a': k.claim_a.text,
                'claim_b': k.claim_b.text,
                'agent_a_id': k.metadata.get('agent_a_id'),
                'agent_b_id': k.metadata.get('agent_b_id'),
            }

        # -- Build judge dict --
        judge = trace.judge_result.model_dump(mode='json') if trace.judge_result else None

        # -- Build sources list --
        sources_list = []
        if answer_obj and answer_obj.sources:
            for source in answer_obj.sources:
                sources_list.append({"url": source.url, "title": source.title})

        response = QueryResponse(
            query=trace.query,
            answer=answer_obj.answer if answer_obj else "No answer generated",
            reasoning=answer_obj.reasoning if answer_obj else "",
            evidence_state=decision.state.value if decision else "unknown",
            rationale=decision.rationale if decision else '',
            debate_triggered=trace.debate_triggered,
            conflict_type=trace.conflict.type.value if trace.conflict else None,
            conflict=conflict,
            agent_evidence=agent_rows,
            failed_agents=decision.failed_agents if decision else [],
            pairwise=pairs,
            debate_rounds=rounds,
            judge=judge,
            sources=sources_list,
            metrics=trace.metrics,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)