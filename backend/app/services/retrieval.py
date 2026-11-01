import hashlib, math, re, uuid, logging
from sqlalchemy.orm import Session
from .. import models
from ..schemas import Evidence
from ..core.config import settings
from .embeddings import embed_texts
log=logging.getLogger(__name__)
TOKEN=re.compile(r"[a-zA-Z0-9_]+")
def tokens(text:str)->list[str]: return [x.lower() for x in TOKEN.findall(text)]
def chunk_text(text:str,size:int=1100,overlap:int=160)->list[str]:
    text=re.sub(r"\s+"," ",text).strip()
    if not text:return []
    out=[]; start=0
    while start<len(text):
        end=min(len(text),start+size); out.append(text[start:end])
        if end==len(text):break
        start=max(end-overlap,start+1)
    return out
class KnowledgeStore:
    def ingest(self,db:Session,filename:str,content_type:str,text:str)->dict:
        digest=hashlib.sha256(text.encode()).hexdigest()
        existing=db.query(models.Document).filter_by(content_hash=digest).first()
        if existing:return {"id":existing.id,"filename":existing.filename,"chunks":existing.chunk_count,"duplicate":True}
        chunks=chunk_text(text)
        vectors=embed_texts(chunks) if settings.embedding_model else [None]*len(chunks)
        doc=models.Document(id=str(uuid.uuid4()),filename=filename,content_type=content_type,content_hash=digest,text=text,chunk_count=len(chunks))
        db.add(doc)
        for i,chunk in enumerate(chunks): db.add(models.DocumentChunk(id=str(uuid.uuid4()),document_id=doc.id,chunk_index=i,text=chunk,embedding=vectors[i] if i<len(vectors) else None))
        db.commit(); return {"id":doc.id,"filename":filename,"chunks":len(chunks),"duplicate":False}
    def search(self,db:Session,query:str,top_k:int|None=None)->list[Evidence]:
        chunks=db.query(models.DocumentChunk).all()
        if not chunks:return []
        q=tokens(query)
        if not q:return []
        docs=[tokens(c.text) for c in chunks]; n=len(docs); avg=sum(map(len,docs))/max(n,1)
        df={t:sum(1 for d in docs if t in set(d)) for t in set(q)}
        scored=[]
        for c,d in zip(chunks,docs):
            score=0.0; freq={t:d.count(t) for t in set(q)}
            for term in set(q):
                if not freq[term]:continue
                idf=math.log(1+(n-df[term]+0.5)/(df[term]+0.5))
                score+=idf*(freq[term]*2.2)/(freq[term]+1.2*(0.25+0.75*len(d)/max(avg,1)))
            if score>0: scored.append((score,c))
        scored.sort(key=lambda x:x[0],reverse=True)
        # Optional dense reranking: when Ollama embeddings are configured and available,
        # combine normalized BM25 and cosine similarity. BM25 remains the reliable fallback.
        query_vector = None
        if settings.embedding_model and any(c.embedding for c in chunks):
            vectors = embed_texts([query])
            query_vector = vectors[0] if vectors else None
        if query_vector:
            def cosine(a, b):
                if not a or not b or len(a) != len(b): return 0.0
                dot=sum(float(x)*float(y) for x,y in zip(a,b))
                na=math.sqrt(sum(float(x)*float(x) for x in a)); nb=math.sqrt(sum(float(y)*float(y) for y in b))
                return dot/(na*nb) if na and nb else 0.0
            bm_max=max((score for score,_ in scored),default=1.0) or 1.0
            dense=[(cosine(query_vector,c.embedding),c) for c in chunks if c.embedding]
            dense_by_id={c.id:score for score,c in dense}
            scored=[(0.65*(score/bm_max)+0.35*max(0.0,dense_by_id.get(c.id,0.0)),c) for score,c in scored]
            scored.sort(key=lambda item:item[0],reverse=True)
            retrieval_mode="hybrid_bm25_embedding"
        else:
            retrieval_mode="bm25"
        docs_by_id={d.id:d for d in db.query(models.Document).all()}
        return [Evidence(text=c.text,source=docs_by_id[c.document_id].filename,score=round(s,4),metadata={"document_id":c.document_id,"chunk_index":c.chunk_index,"retrieval":retrieval_mode}) for s,c in scored[:(top_k or settings.retrieval_top_k)]]
knowledge=KnowledgeStore()
