"""Research endpoints — the evidence behind every number the product shows."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from api.services import provenance, research_experiments

router = APIRouter(prefix="/research", tags=["research"])


@router.get("/provenance")
def data_and_model_provenance() -> dict:
    """Which dataset trained which model, how big it was, and whether it is real.

    Row counts are read from disk on each request, so this cannot drift away
    from what is actually in the repository.
    """
    return provenance.report()


@router.get("/modules/{module}/results")
def module_research_results(module: int) -> dict:
    """One module's experiments, read from research/results/results.json.

    Powers the "Research results" tab on that module's page: what the module
    was actually measured to do, including the results that went against the
    hypothesis. Never recomputed here — these are the report's own numbers.
    """
    if module not in research_experiments.MODULE_NAMES:
        raise HTTPException(404, "No such module")
    return research_experiments.module_results(module)


@router.get("/figures/{name}")
def research_figure(name: str) -> FileResponse:
    """Serve one experiment figure by exact filename.

    Validated against the set of figures the run actually produced — same
    reasoning as the Module 2 figure route, so this can never become an
    arbitrary path read.
    """
    path = research_experiments.figure_path(name)
    if path is None:
        raise HTTPException(404, "Figure not found")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )
