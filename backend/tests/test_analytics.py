from app.services.retrieval import chunk_text,tokens
def test_chunking_preserves_content():
    text='Aegis evidence retrieval. '*150
    chunks=chunk_text(text,100,10)
    assert len(chunks)>1 and all(chunks)
def test_tokenizer():assert tokens('Revenue, Q1 2026!')==['revenue','q1','2026']
