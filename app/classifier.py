"""Strataxis Consulting - Client Signal Classifier.

Classifies a free-text client message into one of five operational categories
so that account managers can route it to the right owner automatically.
"""

RULES = {
    "billing_dispute": [
        "invoice", "overcharg", "billing", "payment", "refund",
    ],
    "scope_change": [
        "scope", "additional module", "change request", "extra deliverable",
    ],
    "data_privacy": [
        "pii", "personal data", "gdpr", "dpdp", "consent", "data residency",
    ],
    "timeline_risk": [
        "delay", "slip", "behind schedule", "deadline", "postpone",
    ],
}

FALLBACK_LABEL = "other"
FALLBACK_CONFIDENCE = 0.30


def classify(text: str) -> dict:
    """Return the predicted label and a confidence score for a client message."""
    if not text or not text.strip():
        return {"label": FALLBACK_LABEL, "confidence": FALLBACK_CONFIDENCE}

    lowered = text.lower()
    scores = {}
    for label, keywords in RULES.items():
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits:
            scores[label] = hits

    if not scores:
        return {"label": FALLBACK_LABEL, "confidence": FALLBACK_CONFIDENCE}

    best_label = max(scores, key=scores.get)
    confidence = min(0.50 + (0.20 * scores[best_label]), 0.99)
    return {"label": best_label, "confidence": round(confidence, 2)}
