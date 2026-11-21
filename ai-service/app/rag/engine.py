import os
import re
import numpy as np
import google.generativeai as genai
from app.core.config import settings
from app.core.database import save_document_chunks, get_document_chunks, load_financial_data
from app.core.heuristic_engine import local_heuristic_engine
from app.reconciliation.engine import run_3way_reconciliation

STOPWORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd",
    'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers',
    'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
    'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if',
    'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
    'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out',
    'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why',
    'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
    'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should',
    "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't",
    'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't",
    'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't",
    'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"
])

def extract_text_from_md(file_path: str) -> str:
    """Reads content of a markdown (.md) file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading Markdown {file_path}: {e}")
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts text content from a PDF (.pdf) file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- PAGE {i+1} ---\n{page_text}"
        return text
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
        return ""

def split_text_into_chunks(text: str, chunk_size=800, overlap=150) -> list:
    """Splits text into chunks of character length chunk_size with overlap."""
    if not text:
        return []
        
    text = re.sub(r'\s+', ' ', text).strip()
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind('.', start + chunk_size - 100, end)
            if boundary != -1:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text) or end == len(text):
            break
    return chunks

_embedding_disabled_warning_shown = False
_EMBEDDING_CACHE = {}

def get_gemini_embedding(text: str, api_key: str, model="models/text-embedding-004"):
    """Computes embedding vector for a string using Google Gemini embedding API with memoization."""
    global _embedding_disabled_warning_shown, _EMBEDDING_CACHE
    if not api_key:
        return None
        
    cache_key = (hash(text), api_key[:10], model)
    if cache_key in _EMBEDDING_CACHE:
        return _EMBEDDING_CACHE[cache_key]
        
    try:
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_document"
        )
        emb = result.get('embedding')
        if emb:
            _EMBEDDING_CACHE[cache_key] = emb
        return emb
    except Exception as e:
        if model == "models/text-embedding-004":
            try:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=text,
                    task_type="retrieval_document"
                )
                emb = result.get('embedding')
                if emb:
                    _EMBEDDING_CACHE[cache_key] = emb
                return emb
            except Exception as e2:
                if not _embedding_disabled_warning_shown:
                    print(f"Gemini Embedding Error: {e2}. Storing empty vectors.")
                    _embedding_disabled_warning_shown = True
        else:
            if not _embedding_disabled_warning_shown:
                print(f"Gemini Embedding Error: {e}. Storing empty vectors.")
                _embedding_disabled_warning_shown = True
        return None

def find_documents_dir():
    """Locates the documents/ folder across local and container filesystem layouts."""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "documents"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "documents"),
        os.path.join(os.getcwd(), "documents"),
        "/app/documents"
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

def build_document_index(api_key: str = None, force_reindex=False) -> int:
    """Scans documents/ folder, parses md/pdf files, generates embeddings, and saves to database."""
    docs_dir = find_documents_dir()
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir, exist_ok=True)
        return 0
        
    files = [f for f in os.listdir(docs_dir) if f.endswith(('.md', '.pdf'))]
    if not files:
        return 0
        
    existing_chunks = get_document_chunks()
    indexed_files = set(c['file_name'] for c in existing_chunks)
    total_saved = 0
    
    for filename in files:
        if filename in indexed_files and not force_reindex:
            continue
            
        file_path = os.path.join(docs_dir, filename)
        if filename.endswith('.md'):
            text = extract_text_from_md(file_path)
        elif filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            continue
            
        if not text.strip():
            continue
            
        text_chunks = split_text_into_chunks(text)
        db_chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            enriched_text = f"[{filename}] {chunk_text}"
            embedding = None
            if api_key:
                embedding = get_gemini_embedding(enriched_text, api_key)
                
            db_chunks.append({
                'chunk_index': idx,
                'text_content': enriched_text,
                'embedding': embedding or []
            })
            
        save_document_chunks(filename, db_chunks)
        total_saved += len(db_chunks)
        
    return total_saved

def retrieve_relevant_context_with_sources(query: str, api_key: str = None, top_n=3, merchant_id=None) -> list:
    """Retrieves top_n document chunks matching the query with their metadata. Employs semantic or keyword search."""
    chunks = get_document_chunks()
    if not chunks:
        build_document_index(api_key)
        chunks = get_document_chunks()
        if not chunks:
            return []
            
    # Tenant RAG Isolation
    if merchant_id:
        filtered = []
        for c in chunks:
            fname = c.get('file_name', '')
            if "_data_" in fname or fname.startswith(("07_", "08_", "09_")):
                if merchant_id in fname:
                    filtered.append(c)
            else:
                filtered.append(c)
        chunks = filtered
        
    query_lower = query.lower()
    id_tokens = set(re.findall(r'\b(?:pay|order|txn|tx|ref)_[a-zA-Z0-9_]+\b|\bpay_[a-zA-Z0-9_]+\b', query_lower))
    for word in re.findall(r'\b[a-zA-Z0-9_-]+\b', query_lower):
        if (any(c.isdigit() for c in word) and len(word) >= 6) or word.startswith(('pay_', 'order_', 'txn_', 'ref_')):
            id_tokens.add(word)
            id_tokens.add(word.replace('-', '_'))

    has_embeddings = any(c.get('embedding') and len(c['embedding']) > 0 for c in chunks)
    
    if api_key and has_embeddings:
        query_emb = get_gemini_embedding(query, api_key, model="models/text-embedding-004")
        if query_emb:
            similarities = []
            for chunk in chunks:
                chunk_emb = chunk.get('embedding')
                boost = 0.0
                chunk_text_lower = chunk.get('text_content', '').lower()
                for id_tok in id_tokens:
                    if id_tok in chunk_text_lower:
                        boost += 100.0
                        
                if not chunk_emb:
                    similarities.append((-1.0 + boost, chunk))
                    continue
                    
                dot_product = np.dot(query_emb, chunk_emb)
                norm_q = np.linalg.norm(query_emb)
                norm_c = np.linalg.norm(chunk_emb)
                similarity = dot_product / (norm_q * norm_c) if (norm_q * norm_c) > 0 else 0
                similarities.append((similarity + boost, chunk))
                
            similarities.sort(key=lambda x: x[0], reverse=True)
            results = []
            for score, chunk in similarities[:top_n]:
                if score > 0.1 or score > 10.0:
                    c_copy = chunk.copy()
                    c_copy['score'] = float(score)
                    results.append(c_copy)
            if results:
                return results

    # Fallback to local keyword search
    def tokenize(text):
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in STOPWORDS]
        
    query_tokens = tokenize(query)
    if not query_tokens:
        results = []
        for c in chunks[:top_n]:
            c_copy = c.copy()
            c_copy['score'] = 0.5
            results.append(c_copy)
        return results
        
    scored_chunks = []
    for chunk in chunks:
        chunk_text = chunk.get('text_content', '')
        chunk_tokens = tokenize(chunk_text)
        boost = 0.0
        chunk_text_lower = chunk_text.lower()
        for id_tok in id_tokens:
            if id_tok in chunk_text_lower:
                boost += 100.0
                
        score = 0
        for token in query_tokens:
            count = chunk_tokens.count(token)
            if count > 0:
                score += (1 + np.log(count)) / (1 + np.log(len(chunk_tokens) + 1))
                
        scored_chunks.append((score + boost, chunk))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, chunk in scored_chunks[:top_n]:
        if score > 0:
            c_copy = chunk.copy()
            c_copy['score'] = float(score) / 10.0 if score < 10.0 else float(score)
            results.append(c_copy)
    return results

def query_financial_assistant(query: str, merchant_id: str = None, store_id: str = None) -> tuple:
    """Main orchestrator for AI Financial Intelligence queries.
    1. Loads scoped financial datasets and runs 3-way reconciliation metrics.
    2. Retrieves top relevant document chunks with tenant isolation.
    3. If GEMINI_API_KEY is available, generates conversational answer via Google Gemini.
    4. If Gemini is unavailable, falls back to deterministic heuristic engine.
    Returns (answer: str, sources: list).
    """
    api_key = settings.GEMINI_API_KEY
    
    # 1. Run reconciliation for live metrics context
    metrics, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation(merchant_id=merchant_id, store_id=store_id)
    
    # 2. Retrieve document context
    sources = retrieve_relevant_context_with_sources(query, api_key=api_key, top_n=3, merchant_id=merchant_id)
    
    # 3. Check for Gemini execution
    if api_key and api_key.strip():
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            
            context_blocks = "\n\n---\n\n".join([s.get('text_content', '') for s in sources])
            
            prompt = f"""You are the senior AI Finance Controller assisting digital commerce finance teams.
You have access to live 3-way reconciliation audit metrics and policy documents.

### Live Financial Metrics:
- Total Payments Processed: {metrics.get('total_payments_processed', 0)}
- Auto-Match Accuracy: {metrics.get('auto_match_accuracy_pct', 0.0)}%
- Gross Collections: INR {metrics.get('gross_collections_inr', 0.0):,.2f}
- Refunds Processed: INR {metrics.get('refunds_inr', 0.0):,.2f}
- Fees + GST: INR {metrics.get('fees_gst_inr', 0.0):,.2f}
- Settled to Bank: INR {metrics.get('settled_to_bank_inr', 0.0):,.2f}
- Expected Next 2 Days: INR {metrics.get('expected_next_2_days_inr', 0.0):,.2f}

### Retrieved Context & Policy Excerpts:
{context_blocks if context_blocks else "No specific policy document excerpt retrieved."}

### User Question:
{query}

Provide a clear, professional, concise, and mathematically accurate financial response. If citing specific exceptions, explain the root cause and recommended resolution.
"""
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text, sources
        except Exception as e:
            print(f"Gemini generation failed: {e}. Falling back to heuristic engine.")
            
    # 4. Fallback to Heuristic Engine
    answer = local_heuristic_engine(query, metrics=metrics, df_tx=df_tx, df_unmatched=df_unmatched, bank_excs=bank_excs)
    return answer, sources
