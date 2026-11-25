from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from backend.medical_knowledge import search_medical_knowledge, get_sources_citation_list, OFFICIAL_MEDICAL_SOURCES
from backend.auth import get_current_user
from backend.models import User

router = APIRouter(prefix="/api/knowledge", tags=["Medical Knowledge Retrieval"])

@router.get("/search")
def search_knowledge(
    q: str = Query(..., min_length=2, description="Medical query keywords"),
    limit: int = 5,
    current_user: User = Depends(get_current_user)
):
    """
    Search validated clinical guidelines and health topics
    from WHO, NHS, MedlinePlus, ICMR, and NCDC India.
    """
    results = search_medical_knowledge(q, max_results=limit)
    citations = get_sources_citation_list(results)
    
    return {
        "query": q,
        "count": len(results),
        "guidelines": results,
        "citations": citations,
        "supported_organizations": ["WHO", "NHS", "MedlinePlus", "ICMR", "NCDC India"]
    }

@router.get("/all")
def get_all_guidelines(current_user: User = Depends(get_current_user)):
    """Retrieve full catalog of curated official guidelines."""
    return {
        "total": len(OFFICIAL_MEDICAL_SOURCES),
        "sources": OFFICIAL_MEDICAL_SOURCES
    }
