def fixed_strategy(user_row, event_history, rng) -> dict:
    """Sends a message every step, no behavioral awareness.
    triggered is always False. Simulator's max_messages_per_user cap
    stops it — this function never returns send=False."""
    return {'send': True, 'triggered': False}


OPERATIONAL_COMPLEXITY = 7
