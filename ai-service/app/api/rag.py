from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.security import verify_internal_secret
from app.core.config import settings
from app.rag.engine import query_financial_assistant, build_document_index

router = APIRouter(dependencies=[Depends(verify_internal_secret)])

class AIQueryRequest(BaseModel):
    query: str
    merchant_id: Optional[str] = None
    store_id: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None

class AIIndexRequest(BaseModel):
    force_reindex: bool = False

@router.post("/ai/query")
def process_ai_query(payload: AIQueryRequest):
    """Processes financial query using Gemini RAG with semantic search and fallback heuristic engine."""
    answer, sources = query_financial_assistant(
        query=payload.query,
        merchant_id=payload.merchant_id,
        store_id=payload.store_id
    )
    
    clean_sources = []
    for s in sources:
        clean_sources.append({
            'file_name': s.get('file_name', ''),
            'chunk_index': s.get('chunk_index', 0),
            'text_content': s.get('text_content', ''),
            'score': s.get('score', 0.0)
        })
        
    return {
        "success": True,
        "answer": answer,
        "sources": clean_sources
    }

@router.post("/ai/index")
def trigger_document_indexing(payload: AIIndexRequest):
    """Triggers parsing and indexing of documents/ folder into PostgreSQL vector store."""
    count = build_document_index(api_key=settings.GEMINI_API_KEY, force_reindex=payload.force_reindex)
    return {
        "success": True,
        "indexed_chunks": count
    }
