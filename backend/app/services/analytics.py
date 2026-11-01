import io, json, math
import pandas as pd
from sqlalchemy.orm import Session
from .. import models
class DataAnalyst:
    def inspect_dataset(self,db:Session,dataset_id:str|None=None)->dict:
        q=db.query(models.Dataset)
        ds=q.filter_by(id=dataset_id).first() if dataset_id else q.order_by(models.Dataset.created_at.desc()).first()
        if not ds:return {"dataset":None,"findings":[],"summary":"No dataset uploaded. Upload a CSV to enable data analysis."}
        frame=pd.DataFrame(ds.rows,columns=ds.columns)
        findings=[]
        numeric=frame.select_dtypes(include="number")
        for col in numeric.columns:
            s=numeric[col].dropna()
            if len(s): findings.append({"metric":col,"count":int(s.count()),"sum":float(s.sum()),"mean":float(s.mean()),"min":float(s.min()),"max":float(s.max())})
        categorical=[c for c in frame.columns if c not in numeric.columns]
        for col in categorical[:3]:
            counts=frame[col].astype(str).value_counts().head(8)
            findings.append({"dimension":col,"top_values":{str(k):int(v) for k,v in counts.items()}})
        return {"dataset":{"id":ds.id,"filename":ds.filename,"rows":ds.row_count,"columns":ds.columns},"findings":findings,"summary":f"Analysed {ds.row_count} rows and {len(ds.columns)} columns from {ds.filename}."}
analyst=DataAnalyst()
