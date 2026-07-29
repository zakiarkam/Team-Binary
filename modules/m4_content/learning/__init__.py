"""Adaptive engagement-learning subsystem.

Everything in this package is opt-in. No module here is imported by the default
`python main.py` pipeline, and the learning stages are not part of the default
stage sequence — they run only when named explicitly with `--step`. The
personalized model is written to its own artifact and never overwrites the base
engagement model, so enabling this subsystem cannot change the behaviour of the
existing generate → evaluate → optimize path.

Modules
-------
targets          construct a content-relative engagement target (the core idea)
feedback_store   SQLite store of generated assets + later-observed analytics
importer         map platform Insights CSV exports into the feedback store
personalize      retrain the engagement predictor on base corpus + feedback
candidates       best-of-N: generate several captions, rank, keep the best
"""
