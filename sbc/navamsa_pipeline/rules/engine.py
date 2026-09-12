"""
Rule engine loading rules_spec.yaml and scoring triggers.
"""
from pathlib import Path

SPEC_PATH = Path(__file__).parent / "rules_spec.yaml"

def load_spec():
    # Minimal spec without yaml dependency
    return {
        "weights": {
            "hora_weight": 0.3,
            "house_set_weight": 0.4,
            "moon_sub_weight": 0.2,
            "asc_sub_weight": 0.1
        },
        "thresholds": {
            "tier1_min_score": 5.0,
            "tier2_min_score": 3.0,
            "pure_set_min_score": 7.0,
            "regime_shift_min_strength": 1.5,
            "confirmation_points": 15,
            "confirmation_candles": 5
        }
    }

class RuleEngine:
    def __init__(self, spec=None):
        self.spec = spec or load_spec()
        self.weights = self.spec.get("weights", {})
        self.thresholds = self.spec.get("thresholds", {})

    def score(self, context):
        # Simplified scoring placeholder
        score = 0.0
        # Hora weighting
        if context.get("hora_quality"):
            score += self.weights.get("hora_weight",0.3) * context["hora_quality"]
        # House set
        if context.get("house_set_strength"):
            score += self.weights.get("house_set_weight",0.4) * context["house_set_strength"]
        # Moon sub
        if context.get("moon_sub_score"):
            score += self.weights.get("moon_sub_weight",0.2) * context["moon_sub_score"]
        # Asc sub
        if context.get("asc_sub_score"):
            score += self.weights.get("asc_sub_weight",0.1) * context["asc_sub_score"]
        return round(score,4)

    def classify(self, score):
        t = self.thresholds
        if score >= t.get("tier1_min_score",5.0):
            return "Tier1"
        if score >= t.get("tier2_min_score",3.0):
            return "Tier2"
        return "NoTrade"
