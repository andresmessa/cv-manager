import json

import anthropic
from pydantic import BaseModel

MODEL = "claude-sonnet-5"

# Claude Sonnet 5 list prices (USD per million tokens); update if MODEL changes.
INPUT_USD_PER_MTOK = 2.00
OUTPUT_USD_PER_MTOK = 10.00

# Output-token heuristic for estimate_tokens (thinking + JSON). Calibrated on 6 candidates:
# real calls used 1.1k (one-line JD) to 3.7k (long, many-skill JD) output tokens.
OUTPUT_BASE_LOW, OUTPUT_PER_CANDIDATE_LOW = 200, 120
OUTPUT_BASE_HIGH, OUTPUT_PER_CANDIDATE_HIGH = 1500, 450

SYSTEM_PROMPT = """You are an experienced recruiter for quality engineering and manufacturing \
quality roles (QA/QC, supplier quality, auditing, inspection, continuous improvement).

You will receive a job description written as free text, and a list of candidates. Each \
candidate is identified only by an id and the list of skills already confirmed for them.

1. Read the job description and identify the concrete skills, certifications, standards, \
tools and methodologies it requires. Use short, canonical names (e.g. "ISO 9001", \
"Statistical Process Control (SPC)"). Where a required skill matches a skill name that \
appears in the candidates' lists, reuse that exact name.
2. Score every candidate from 0 to 100 on how well their listed skills cover the job's \
requirements. Base the score only on the listed skills; do not assume skills that are not \
listed. Give partial credit for closely related skills (e.g. Control Charts toward SPC, \
IATF 16949 toward ISO 9001 experience), and weigh core requirements above nice-to-haves.
3. For each candidate return:
   - matched_skills: skills copied verbatim from that candidate's own list that are relevant \
to the job.
   - missing_skills: required skills (from step 1) the candidate does not cover.
   - reasoning: one or two sentences explaining the score.

Include every candidate id exactly once."""


class CandidateRanking(BaseModel):
    candidate_id: str
    fit_score: int
    matched_skills: list[str]
    missing_skills: list[str]
    reasoning: str


class MatchAnalysis(BaseModel):
    required_skills: list[str]
    rankings: list[CandidateRanking]


class LLMMatchError(Exception):
    pass


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=120.0)
    return _client


def _request_params(job_description: str, candidates: list[dict]) -> dict:
    """The request shared by rank_candidates and estimate_tokens, so the estimate matches the real call."""
    candidate_payload = [{"id": c["id"], "skills": c["skills"]} for c in candidates]
    user_message = (
        f"<job_description>\n{job_description}\n</job_description>\n\n"
        f"<candidates>\n{json.dumps(candidate_payload, indent=2)}\n</candidates>"
    )
    return {
        "model": MODEL,
        "thinking": {"type": "adaptive"},
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
        "output_format": MatchAnalysis,
    }


def _call(fn, *args, **kwargs):
    """Runs an SDK call, normalising every failure to LLMMatchError."""
    try:
        return fn(*args, **kwargs)
    except anthropic.AnthropicError as e:
        raise LLMMatchError(f"Claude API call failed: {e}") from e
    except TypeError as e:
        # The SDK raises TypeError at request time when no credentials are configured.
        raise LLMMatchError(f"Claude API not configured: {e}") from e


def rank_candidates(job_description: str, candidates: list[dict]) -> tuple[MatchAnalysis, dict]:
    """Asks Claude to rank candidates against a job description using only their stored skills.

    `candidates` are CV records (must have `id` and a non-empty `skills` list). Names and
    files are deliberately not sent. Returns (analysis, actual token usage). Raises
    LLMMatchError on any failure so the caller can fall back to keyword matching.
    """
    response = _call(
        _get_client().messages.parse,
        max_tokens=16000,
        **_request_params(job_description, candidates),
    )

    if response.stop_reason in ("refusal", "max_tokens"):
        raise LLMMatchError(f"Claude stopped early (stop_reason={response.stop_reason}).")
    if response.parsed_output is None:
        raise LLMMatchError("Claude returned no parsable output.")

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cost_usd": _cost(response.usage.input_tokens, response.usage.output_tokens),
    }
    return _sanitize(response.parsed_output, candidates), usage


def estimate_tokens(job_description: str, candidates: list[dict]) -> dict:
    """Previews a rank_candidates call without running it.

    Input tokens are exact (the free count_tokens endpoint, same request). Output tokens
    can't be known in advance — adaptive thinking and reasoning length vary — so they
    are a heuristic range scaled by candidate count.
    """
    counted = _call(_get_client().messages.count_tokens, **_request_params(job_description, candidates))
    n = len(candidates)
    output_low = OUTPUT_BASE_LOW + OUTPUT_PER_CANDIDATE_LOW * n
    output_high = OUTPUT_BASE_HIGH + OUTPUT_PER_CANDIDATE_HIGH * n
    return {
        "model": MODEL,
        "candidate_count": n,
        "input_tokens": counted.input_tokens,
        "output_tokens_low": output_low,
        "output_tokens_high": output_high,
        "cost_usd_low": _cost(counted.input_tokens, output_low),
        "cost_usd_high": _cost(counted.input_tokens, output_high),
    }


def _cost(input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens * INPUT_USD_PER_MTOK / 1_000_000 + output_tokens * OUTPUT_USD_PER_MTOK / 1_000_000,
        4,
    )


def _sanitize(analysis: MatchAnalysis, candidates: list[dict]) -> MatchAnalysis:
    """Keeps the model's output consistent with the stored data."""
    by_id = {c["id"]: c for c in candidates}
    seen: set[str] = set()
    rankings: list[CandidateRanking] = []

    for ranking in analysis.rankings:
        record = by_id.get(ranking.candidate_id)
        if record is None or ranking.candidate_id in seen:
            continue
        seen.add(ranking.candidate_id)
        stored = set(record["skills"])
        rankings.append(
            CandidateRanking(
                candidate_id=ranking.candidate_id,
                fit_score=max(0, min(100, ranking.fit_score)),
                matched_skills=[s for s in dict.fromkeys(ranking.matched_skills) if s in stored],
                missing_skills=list(dict.fromkeys(ranking.missing_skills)),
                reasoning=ranking.reasoning.strip(),
            )
        )

    for candidate_id in by_id.keys() - seen:
        rankings.append(
            CandidateRanking(
                candidate_id=candidate_id,
                fit_score=0,
                matched_skills=[],
                missing_skills=[],
                reasoning="Not assessed.",
            )
        )

    return MatchAnalysis(required_skills=list(dict.fromkeys(analysis.required_skills)), rankings=rankings)
