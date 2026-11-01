from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Any
class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=8,max_length=5000)
    thread_id: str|None=Field(default=None,max_length=128)
    include_retrieval: bool=True
    include_analysis: bool=True
    dataset_id: str|None=None
class Evidence(BaseModel):
    text: str
    source: str="unknown"
    score: float|None=None
    metadata: dict[str,Any]=Field(default_factory=dict)
class AnalyzeResponse(BaseModel):
    run_id:str; thread_id:str; status:str; plan:list[str]; findings:list[str]; evidence:list[Evidence]
    verification:dict[str,Any]; report:str; trace:list[dict[str,Any]]; warnings:list[str]=Field(default_factory=list); llm_mode:str="template"
class RunSummary(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:str; thread_id:str; query:str; status:str; created_at:datetime
