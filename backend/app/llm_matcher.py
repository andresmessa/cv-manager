import json

import anthropic
from pydantic import BaseModel

MODEL = "claude-sonnet-5"

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


def rank_candidates(job_description: str, candidates: list[dict]) -> MatchAnalysis:
    """Asks Claude to rank candidates against a job description using only their stored skills.

    `candidates` are CV records (must have `id` and a non-empty `skills` list). Names and
    files are deliberately not sent. Raises LLMMatchError on any failure so the caller
    can fall back to keyword matching.
    """
    candidate_payload = [{"id": c["id"], "skills": c["skills"]} for c in candidates]
    user_message = (
        f"<job_description>\n{job_description}\n</job_description>\n\n"
        f"<candidates>\n{json.dumps(candidate_payload, indent=2)}\n</candidates>"
    )

    try:
        response = _get_client().messages.parse(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_format=MatchAnalysis,
        )
    except anthropic.AnthropicError as e:
        raise LLMMatchError(f"Claude API call failed: {e}") from e
    except TypeError as e:
        # The SDK raises TypeError at request time when no credentials are configured.
        raise LLMMatchError(f"Claude API not configured: {e}") from e

    if response.stop_reason in ("refusal", "max_tokens"):
        raise LLMMatchError(f"Claude stopped early (stop_reason={response.stop_reason}).")
    if response.parsed_output is None:
        raise LLMMatchError("Claude returned no parsable output.")

    return _sanitize(response.parsed_output, candidates)


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
