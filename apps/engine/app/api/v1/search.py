from typing import List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import SessionAuth
from app.infrastructure.fts.fts_manager import FTSManager
from app.modules.identity.phone_normalizer import PhoneNormalizer

router = APIRouter(prefix="/search", tags=["Global Search"], dependencies=[SessionAuth])

class SearchResultItem(BaseModel):
    entity_id: str
    entity_type: str
    title: str
    snippet: str
    rank: float

@router.get("", response_model=List[SearchResultItem])
def search_global(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200)):
    # If the user queried a phone number, normalize first to match indexed E.164 tokens
    norm_phone = PhoneNormalizer.normalize_single(q)
    query_str = norm_phone if norm_phone else q
    
    results = FTSManager.search(query=query_str, limit=limit)
    return [
        SearchResultItem(
            entity_id=r["entity_id"],
            entity_type=r["entity_type"],
            title=r["title"],
            snippet=r["snippet"],
            rank=r["rank"]
        )
        for r in results
    ]
