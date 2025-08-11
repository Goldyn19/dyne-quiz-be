# your_app/game_logic.py
from django.utils import timezone


def calculate_score(time_remaining, max_time=30, base_points=100):
    """
    Calculate score based on response time
    - Faster answers get more points
    - Linear scaling from 50% to 100% of base points
    """
    if time_remaining <= 0:
        return 0

    # Ensure we don't give more than base_points
    time_ratio = min(time_remaining / max_time, 1.0)

    # Give at least 50% points for correct answers
    min_score = base_points * 0.5
    score_range = base_points - min_score

    return int(min_score + (score_range * time_ratio))
