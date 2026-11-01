import hashlib,hmac,io,logging,uuid
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from fastapi import FastAPI,Depends,HTTPException,Request,UploadFile,File,Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from pypdf import PdfReader
from docx import Document as DocxDocument
from .core.config import settings
from .db import Base,engine,get_db
from . import models
from .schemas import AnalyzeRequest,AnalyzeResponse,RunSummary
from .agents.graph import execute
from .services.retrieval import knowledge

logging.basicConfig(level=getattr(logging,settings.log_level.upper(),logging.INFO),format="%(asctime)s %(levelname)s %(name)s %(message)s")
log=logging.getLogger("aegis.api"); metrics={"requests":0,"analyses_completed":0,"analyses_failed":0,"documents_ingested":0,"datasets_ingested":0}
@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(bind=engine);settings.uploads_path.mkdir(parents=True,exist_ok=True);yield
app=FastAPI(title="Aegis Enterprise Intelligence API",version="2.0.0",description="Standalone multi-agent enterprise intelligence platform",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,allow_credentials=False,allow_methods=["GET","POST","DELETE"],allow_headers=["Content-Type","X-API-Key"])
@app.middleware("http")
async def guard(request:Request,call_next):
    metrics["requests"]+=1
    if request.method in {"POST","PUT","PATCH"}:
        size=request.headers.get("content-length")
        if size and int(size)>settings.max_request_bytes:
            from starlette.responses import JSONResponse
            return JSONResponse({"detail":"Request too large"},status_code=413)
    if settings.aegis_api_key and request.url.path.startswith("/api/"):
        if not hmac.compare_digest(request.headers.get("x-api-key",""),settings.aegis_api_key):
            from starlette.responses import JSONResponse
            return JSONResponse({"detail":"Unauthorized"},status_code=401)
    response=await call_next(request);response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY","Referrer-Policy":"no-referrer"});return response
@app.get("/health")
def health():return {"status":"ok","service":"aegis","version":"2.0.0"}
@app.get("/ready")
def ready(db:Session=Depends(get_db)):
    try:db.execute(text("SELECT 1"));return {"status":"ready","database":"connected"}
    except Exception as exc:raise HTTPException(503,"Database unavailable") from exc
@app.post("/api/v1/analyze",response_model=AnalyzeResponse)
async def analyze(payload:AnalyzeRequest,db:Session=Depends(get_db)):
    run_id=str(uuid.uuid4());thread_id=payload.thread_id or str(uuid.uuid4())
    try:
        result=await execute(payload.query,payload.include_retrieval,payload.include_analysis,db,payload.dataset_id)
        response={"run_id":run_id,"thread_id":thread_id,"status":"completed","plan":result.get("plan",[]),"findings":result.get("findings",[]),"evidence":result.get("evidence",[]),"verification":result.get("verification",{}),"report":result.get("report",""),"trace":result.get("trace",[]),"warnings":result.get("warnings",[]),"llm_mode":result.get("llm_mode","template")}
        db.add(models.AnalysisRun(id=run_id,thread_id=thread_id,query=payload.query,status="completed",result=response));db.commit();metrics["analyses_completed"]+=1;return response
    except Exception as exc:db.rollback();metrics["analyses_failed"]+=1;log.exception("Run %s failed",run_id);raise HTTPException(500,f"Analysis failed; run_id={run_id}") from exc
@app.get("/api/v1/runs/{run_id}")
def get_run(run_id:str,db:Session=Depends(get_db)):
    row=db.get(models.AnalysisRun,run_id)
    if not row:raise HTTPException(404,"Run not found")
    return row.result
@app.get("/api/v1/runs",response_model=list[RunSummary])
def list_runs(limit:int=20,db:Session=Depends(get_db)):
    if not 1<=limit<=100:raise HTTPException(422,"limit must be between 1 and 100")
    return db.query(models.AnalysisRun).order_by(models.AnalysisRun.created_at.desc()).limit(limit).all()
@app.post("/api/v1/documents")
async def upload_document(file:UploadFile=File(...),db:Session=Depends(get_db)):
    name=(file.filename or "upload").replace("/","_").replace("\\","_")
    raw=await file.read(settings.max_upload_bytes+1)
    if len(raw)>settings.max_upload_bytes:raise HTTPException(413,"File exceeds upload limit")
    ext=name.lower().rsplit(".",1)[-1] if "." in name else ""
    try:
        if ext=="pdf":
            reader=PdfReader(io.BytesIO(raw));content="\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext=="docx":content="\n".join(p.text for p in DocxDocument(io.BytesIO(raw)).paragraphs)
        elif ext in {"txt","md"}:content=raw.decode("utf-8-sig")
        else:raise HTTPException(415,"Supported document types: PDF, DOCX, TXT, MD")
    except HTTPException:raise
    except Exception as exc:raise HTTPException(400,"Could not extract text from this document") from exc
    if not content.strip():raise HTTPException(422,"No extractable text found in document")
    result=knowledge.ingest(db,name,file.content_type or "application/octet-stream",content);metrics["documents_ingested"]+=0 if result["duplicate"] else 1
    return result
@app.get("/api/v1/documents")
def list_documents(db:Session=Depends(get_db)):
    return [{"id":d.id,"filename":d.filename,"chunks":d.chunk_count,"created_at":d.created_at} for d in db.query(models.Document).order_by(models.Document.created_at.desc()).all()]
@app.delete("/api/v1/documents/{document_id}")
def delete_document(document_id:str,db:Session=Depends(get_db)):
    doc=db.get(models.Document,document_id)
    if not doc:raise HTTPException(404,"Document not found")
    db.query(models.DocumentChunk).filter_by(document_id=document_id).delete();db.delete(doc);db.commit();return {"deleted":document_id}
@app.post("/api/v1/datasets")
async def upload_dataset(file:UploadFile=File(...),db:Session=Depends(get_db)):
    name=(file.filename or "dataset.csv").replace("/","_").replace("\\","_")
    if not name.lower().endswith(".csv"):raise HTTPException(415,"Only CSV datasets are supported")
    raw=await file.read(settings.max_upload_bytes+1)
    if len(raw)>settings.max_upload_bytes:raise HTTPException(413,"File exceeds upload limit")
    try:
        frame=pd.read_csv(io.BytesIO(raw))
        if frame.empty:raise ValueError("CSV contains no rows")
        if len(frame)>settings.max_csv_rows:raise ValueError(f"CSV exceeds {settings.max_csv_rows} row limit")
        frame=frame.astype(object).where(pd.notna(frame),None)
        rows=frame.to_dict(orient="records")
        # Normalize NumPy scalar types and reject non-JSON values.
        import json
        rows=json.loads(json.dumps(rows,default=lambda x:float(x) if hasattr(x,"item") else str(x),allow_nan=False))
    except Exception as exc:raise HTTPException(400,f"Invalid CSV: {str(exc)[:180]}") from exc
    digest=hashlib.sha256(raw).hexdigest();existing=db.query(models.Dataset).filter_by(content_hash=digest).first()
    if existing:return {"id":existing.id,"filename":existing.filename,"rows":existing.row_count,"columns":existing.columns,"duplicate":True}
    ds=models.Dataset(id=str(uuid.uuid4()),filename=name,content_hash=digest,columns=[str(c) for c in frame.columns],rows=rows,row_count=len(rows));db.add(ds);db.commit();metrics["datasets_ingested"]+=1
    return {"id":ds.id,"filename":name,"rows":len(rows),"columns":ds.columns,"duplicate":False}
@app.get("/api/v1/datasets")
def list_datasets(db:Session=Depends(get_db)):
    return [{"id":d.id,"filename":d.filename,"rows":d.row_count,"columns":d.columns,"created_at":d.created_at} for d in db.query(models.Dataset).order_by(models.Dataset.created_at.desc()).all()]
@app.delete("/api/v1/datasets/{dataset_id}")
def delete_dataset(dataset_id:str,db:Session=Depends(get_db)):
    ds=db.get(models.Dataset,dataset_id)
    if not ds:raise HTTPException(404,"Dataset not found")
    db.delete(ds);db.commit();return {"deleted":dataset_id}
@app.get("/api/v1/metrics")
def get_metrics():return dict(metrics)
