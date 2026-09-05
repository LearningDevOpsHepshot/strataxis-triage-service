"""Unit tests for the client signal classifier."""

import pytest

from app.classifier import classify


def test_billing_dispute_is_detected():
    result = classify("The invoice for March looks like an overcharge.")
    assert result["label"] == "billing_dispute"


def test_scope_change_is_detected():
    result = classify("Can we add an additional module to the delivery?")
    assert result["label"] == "scope_change"


def test_data_privacy_is_detected():
    result = classify("Where is the personal data stored under DPDP rules?")
    assert result["label"] == "data_privacy"


def test_timeline_risk_is_detected():
    result = classify("We are behind schedule and may miss the deadline.")
    assert result["label"] == "timeline_risk"


@pytest.mark.parametrize("text", ["", "   ", None])
def test_empty_input_falls_back_safely(text):
    result = classify(text)
    assert result["label"] == "other"


def test_confidence_is_always_a_valid_probability():
    result = classify("The invoice payment is disputed and needs a refund.")
    assert 0.0 <= result["confidence"] <= 1.0
