"""Research endpoints — the evidence behind every number the product shows."""

from __future__ import annotations

from fastapi import APIRouter

from api.services import provenance

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/provenance")
def data_and_model_provenance() -> dict:
    """Which dataset trained which model, how big it was, and whether it is real.

    Row counts are read from disk on each request, so this cannot drift away
    from what is actually in the repository.
    """
    return provenance.report()
