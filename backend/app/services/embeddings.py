import httpx, logging
from ..core.config import settings
log=logging.getLogger(__name__)
def embed_texts(texts:list[str])->list[list[float]|None]:
    if not settings.embedding_model:return [None for _ in texts]
    out=[]
    try:
        with httpx.Client(timeout=20) as client:
            for text in texts:
                r=client.post(settings.embedding_url,json={"model":settings.embedding_model,"prompt":text}); r.raise_for_status(); out.append(r.json().get("embedding"))
        return out
    except Exception as exc:
        log.info("Embedding provider unavailable; BM25 remains active: %s",type(exc).__name__)
        return [None for _ in texts]
