"""Rule-based fraud scoring. Pure functions -> easy to unit test."""

HIGH_RISK_COUNTRIES = {"KP", "IR", "SY", "MM", "AF"}
FLAG_THRESHOLD = 50


def score_transaction(amount, country, hour_utc, recent_count):
    """Return (score 0-100, list of reasons). recent_count = txns on the account in the last 10 min."""
    score, reasons = 0, []
    amount = float(amount)

    if amount >= 10000:
        score += 50
        reasons.append("very large amount")
    elif amount >= 5000:
        score += 25
        reasons.append("large amount")

    if country.upper() in HIGH_RISK_COUNTRIES:
        score += 35
        reasons.append("high-risk country")

    if recent_count >= 3:
        score += 30
        reasons.append("rapid repeated transactions")

    if 0 <= hour_utc < 5:
        score += 10
        reasons.append("unusual hour")

    return min(score, 100), reasons


def is_flagged(score):
    return score >= FLAG_THRESHOLD
