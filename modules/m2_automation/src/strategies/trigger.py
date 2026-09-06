def trigger_strategy(user_row, event_history, rng) -> dict:
    """Behavioral trigger strategy.
    - Step 0 (event_history is empty): send with triggered=False. No prior
      signal exists yet, so first message is a cold send.
    - Step >= 1: check the most recent event in event_history. Send with
      triggered=True IF the previous message was opened OR clicked.
      Otherwise return send=False (campaign ends for this user).

    This means trigger sends FEWER total messages than fixed under the same
    max_messages cap, because ignored messages terminate the sequence.
    """
    if not event_history:
        return {'send': True, 'triggered': False}
    last = event_history[-1]
    if last['opened'] or last['clicked']:
        return {'send': True, 'triggered': True}
    return {'send': False, 'triggered': False}


OPERATIONAL_COMPLEXITY = 15
