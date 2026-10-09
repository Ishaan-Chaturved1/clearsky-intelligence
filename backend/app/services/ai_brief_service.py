import json
from datetime import datetime, timezone
from typing import List
from app.models.domain import DecisionRecord, DecisionType, Zone
from app.schemas.api_models import AiDailyBriefResponse
from app.core.config import settings
from app.core.logging import logger

try:
    import boto3
except ImportError:
    boto3 = None

class AiBriefService:
    def __init__(self):
        self.enabled = settings.ENABLE_AI_BRIEF
        self.region = settings.AWS_REGION
        self.model_id = settings.BEDROCK_MODEL_ID

    def generate_brief(
        self,
        zones: List[Zone],
        decisions: List[DecisionRecord]
    ) -> AiDailyBriefResponse:
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # Determine candidates
        recommended = [d for d in decisions if d.decision == DecisionType.INTERVENTION_RECOMMENDED]
        discouraged = [d for d in decisions if d.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED]
        advisory = [d for d in decisions if d.decision == DecisionType.ADVISORY_ONLY]

        zone_name_map = {z.zone_id: z.name for z in zones}
        high_priority_zones = [
            f"{zone_name_map.get(d.zone_id, d.zone_id)} (Priority {d.priority or 2})"
            for d in recommended if (d.priority or 0) >= 3
        ]

        # If enabled and boto3 available, try Bedrock invocation
        if self.enabled and boto3 is not None:
            try:
                bedrock = boto3.client("bedrock-runtime", region_name=self.region)
                prompt = (
                    f"Summarize the following smart-city environmental decisions concisely in 2 sentences. "
                    f"Total zones: {len(decisions)}. Recommended: {len(recommended)}. "
                    f"Discouraged: {len(discouraged)}. Advisory: {len(advisory)}. "
                    f"High priority hotspots: {', '.join(high_priority_zones[:3])}. "
                    f"Maintain scientific restraint, do not fabricate numbers."
                )
                payload = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                }
                resp = bedrock.invoke_model(
                    modelId=self.model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(payload)
                )
                body = json.loads(resp["body"].read())
                text = body["content"][0]["text"]
                return AiDailyBriefResponse(
                    generated_at=now_iso,
                    headline="Atmospheric Inversion & Coarse Dust Operational Synthesis",
                    summary_text=text,
                    high_priority_zones=high_priority_zones,
                    cautions_and_disclaimers=[
                        "Water mist spraying does not mitigate fine PM2.5 or combustion soot.",
                        "Recommendations are heuristics based on available station and model estimates."
                    ],
                    provider="Amazon Bedrock"
                )
            except Exception as e:
                logger.warning(f"Bedrock synthesis fallback triggered: {e}")

        # Deterministic Fallback synthesis
        recs_count = len(recommended)
        disc_count = len(discouraged)
        adv_count = len(advisory)

        headline = f"Environmental Overview: {recs_count} Hotspots Identified, {disc_count} Interventions Suppressed"
        
        if recs_count > 0:
            summary_text = (
                f"Evaluation across {len(decisions)} monitored zones indicates {recs_count} targeted candidates "
                f"showing coarse dust dominance (PM10/PM2.5 ratio >= 2.0). Interventions in {disc_count} zones "
                f"are withheld due to elevated humidity, high wind dispersion, or combustion soot characteristics."
            )
        else:
            summary_text = (
                f"Ambient conditions across {len(decisions)} monitored sectors currently do not indicate localized "
                f"coarse fugitive dust dominance. Standard fixed-schedule water dispersal should be suspended to conserve municipal resources."
            )

        return AiDailyBriefResponse(
            generated_at=now_iso,
            headline=headline,
            summary_text=summary_text,
            high_priority_zones=high_priority_zones,
            cautions_and_disclaimers=[
                "Decision support rules are heuristic guides and do not guarantee atmospheric PM2.5 reduction.",
                "Always verify site-specific safety and road traffic before deploying anti-smog equipment."
            ],
            provider="Deterministic Engine Synthesis"
        )
