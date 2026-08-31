import os
import sys
import re
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

# Add src to python path if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import save_document_chunks, get_document_chunks

load_dotenv()

# Stopwords for simple keyword matching fallback
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

def extract_text_from_md(file_path):
    """Reads content of a markdown (.md) file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_text_from_pdf(file_path):
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
        print(f"ERROR: Error parsing PDF {os.path.basename(file_path)}: {str(e)}")
        return ""

def split_text_into_chunks(text, chunk_size=800, overlap=150):
    """Splits text into chunks of character length chunk_size with overlap."""
    if not text:
        return []
    
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Try to find a sentence boundary nearby to make cleaner chunks
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

def get_gemini_embedding(text, api_key, model="models/text-embedding-004"):
    """Computes embedding vector for a string using Google Gemini embedding API."""
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model=model,
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Gemini Embedding Error: {str(e)}")
        return None

def build_document_index(api_key, force_reindex=False):
    """Scans documents/ folder, parses md/pdf files, generates embeddings, and saves to database."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "documents")
    
    if not os.path.exists(docs_dir):
        print(f"Creating documents directory: {docs_dir}")
        os.makedirs(docs_dir, exist_ok=True)
        return False
        
    files = [f for f in os.listdir(docs_dir) if f.endswith(('.md', '.pdf'))]
    if not files:
        print("No documents found in documents/ folder.")
        return False
        
    print(f"Found {len(files)} documents in documents/ folder. Scanning...")
    
    # Load already indexed files from db to avoid re-indexing unless forced
    existing_chunks = get_document_chunks()
    indexed_files = set(c['file_name'] for c in existing_chunks)
    
    for filename in files:
        if filename in indexed_files and not force_reindex:
            print(f"File {filename} already indexed. Skipping.")
            continue
            
        file_path = os.path.join(docs_dir, filename)
        print(f"Parsing and chunking {filename}...")
        
        # 1. Extract text
        if filename.endswith('.md'):
            text = extract_text_from_md(file_path)
        elif filename.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            continue
            
        if not text.strip():
            print(f"Empty text in {filename}. Skipping.")
            continue
            
        # 2. Chunk text
        text_chunks = split_text_into_chunks(text)
        print(f"   Generated {len(text_chunks)} chunks.")
        
        # 3. Generate embeddings & format chunks
        db_chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            # Include filename/context in text for better retrieval matching
            enriched_text = f"[{filename}] {chunk_text}"
            
            embedding = None
            if api_key:
                embedding = get_gemini_embedding(enriched_text, api_key)
                
            db_chunks.append({
                'chunk_index': idx,
                'text_content': enriched_text,
                'embedding': embedding or [] # Store empty list if embedding generation fails/is skipped
            })
            
        # 4. Save to database
        save_document_chunks(filename, db_chunks)
        print(f"Saved index chunks for {filename} to database.")
        
    print("Document indexing process complete.")
    return True

def keyword_search_fallback(query, chunks, top_n=3):
    """Pure-python keyword search fallback (TF-IDF/cosine approximation)."""
    # Simple tokenize & stopword removal
    def tokenize(text):
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in STOPWORDS]
        
    query_tokens = tokenize(query)
    if not query_tokens:
        # If no keywords remain, return top chunks sequentially
        return [c['text_content'] for c in chunks[:top_n]]
        
    scored_chunks = []
    for chunk in chunks:
        chunk_text = chunk['text_content']
        chunk_tokens = tokenize(chunk_text)
        
        # Term Frequency in chunk
        score = 0
        for token in query_tokens:
            count = chunk_tokens.count(token)
            if count > 0:
                # Add score based on term frequency and document length discount
                score += (1 + np.log(count)) / (1 + np.log(len(chunk_tokens) + 1))
                
        scored_chunks.append((score, chunk_text))
        
    # Sort by score descending
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [text for score, text in scored_chunks[:top_n] if score > 0]

def retrieve_relevant_context_with_sources(query, api_key, top_n=3, merchant_id=None):
    """Retrieves top_n document chunks matching the query with their metadata. Employs semantic or keyword search."""
    chunks = get_document_chunks()
    if not chunks:
        # Trigger an index scan with the key if database has no chunks
        build_document_index(api_key)
        chunks = get_document_chunks()
        if not chunks:
            return []
            
    # Tenant RAG Isolation: Filter out other merchants' exported data chunks
    if merchant_id:
        filtered = []
        for c in chunks:
            fname = c['file_name']
            if "_data_" in fname or fname.startswith(("07_", "08_", "09_")):
                if merchant_id in fname:
                    filtered.append(c)
            else:
                # Policy document chunks are visible to all tenants
                filtered.append(c)
        chunks = filtered
            
    # Check if we can perform semantic search (we need query api_key, and chunks must have embeddings)
    has_embeddings = any(c['embedding'] and len(c['embedding']) > 0 for c in chunks)
    
    if api_key and has_embeddings:
        print("Performing semantic search...")
        query_emb = get_gemini_embedding(query, api_key, model="models/text-embedding-004")
        
        if query_emb:
            # Cosine similarity calculations
            similarities = []
            for chunk in chunks:
                chunk_emb = chunk['embedding']
                if not chunk_emb:
                    similarities.append((-1.0, chunk))
                    continue
                    
                # Cosine Similarity
                dot_product = np.dot(query_emb, chunk_emb)
                norm_q = np.linalg.norm(query_emb)
                norm_c = np.linalg.norm(chunk_emb)
                
                similarity = dot_product / (norm_q * norm_c) if (norm_q * norm_c) > 0 else 0
                similarities.append((similarity, chunk))
                
            similarities.sort(key=lambda x: x[0], reverse=True)
            # Retrieve top matches
            results = []
            for score, chunk in similarities[:top_n]:
                if score > 0.1:
                    chunk_copy = chunk.copy()
                    chunk_copy['score'] = float(score)
                    results.append(chunk_copy)
            if results:
                return results
                
    # Fallback to local keyword search
    print("Fallback to keyword-based retrieval...")
    
    def tokenize(text):
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in STOPWORDS]
        
    query_tokens = tokenize(query)
    if not query_tokens:
        results = []
        for c in chunks[:top_n]:
            c_copy = c.copy()
            c_copy['score'] = 0.5 # dummy score
            results.append(c_copy)
        return results
        
    scored_chunks = []
    for chunk in chunks:
        chunk_text = chunk['text_content']
        chunk_tokens = tokenize(chunk_text)
        
        score = 0
        for token in query_tokens:
            count = chunk_tokens.count(token)
            if count > 0:
                score += (1 + np.log(count)) / (1 + np.log(len(chunk_tokens) + 1))
                
        scored_chunks.append((score, chunk))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, chunk in scored_chunks[:top_n]:
        if score > 0:
            chunk_copy = chunk.copy()
            chunk_copy['score'] = float(score) / 10.0 # Normalized approximation
            results.append(chunk_copy)
    return results

def retrieve_relevant_context(query, api_key, top_n=3, merchant_id=None):
    """Retrieves top_n document chunks matching the query. Employs semantic or keyword search."""
    results = retrieve_relevant_context_with_sources(query, api_key, top_n, merchant_id)
    if not results:
        return "No relevant context found in documents."
    return "\n\n---\n\n".join([r['text_content'] for r in results])
