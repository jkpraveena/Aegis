import httpx, logging
from ..core.config import settings
log=logging.getLogger(__name__)
class LLMService:
    @property
    def enabled(self)->bool: return bool(settings.llm_model and settings.llm_base_url)
    async def complete(self, system:str, user:str, fallback:str)->tuple[str,str,str|None]:
        if not self.enabled: return fallback,"template",None
        url=settings.llm_base_url.rstrip("/")+"/chat/completions"
        headers={"Content-Type":"application/json"}
        if settings.llm_api_key: headers["Authorization"]=f"Bearer {settings.llm_api_key}"
        payload={"model":settings.llm_model,"temperature":0.15,"messages":[{"role":"system","content":system},{"role":"user","content":user}]}
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response=await client.post(url,headers=headers,json=payload); response.raise_for_status(); data=response.json()
            content=data["choices"][0]["message"]["content"].strip()
            if not content: raise ValueError("Empty model response")
            return content,"llm",None
        except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as exc:
            log.warning("LLM request failed; using transparent template fallback: %s",type(exc).__name__)
            return fallback,"template_fallback",f"LLM unavailable ({type(exc).__name__}); deterministic report used."
llm=LLMService()
