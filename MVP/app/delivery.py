from dataclasses import dataclass
import httpx
from app.models import NotificationRow

@dataclass
class Outcome:
    success: bool=False
    retry: bool=False
    code: str=""
    message: str=""

def classify(status_code: int|None, error: Exception|None) -> Outcome:
    if error:return Outcome(retry=True,code="NETWORK_ERROR",message=str(error))
    if status_code is not None and 200 <= status_code < 300:return Outcome(success=True)
    if status_code in {408,425,429,500,502,503,504}:return Outcome(retry=True,code=f"HTTP_{status_code}",message="temporary supplier failure")
    return Outcome(code=f"HTTP_{status_code}",message="supplier rejected request")

class DeliveryClient:
    def __init__(self, timeout: float=10): self.timeout=timeout
    async def send(self, row: NotificationRow) -> tuple[int|None,Exception|None]:
        headers=dict(row.headers_json or {});headers["Idempotency-Key"]=row.id;headers["X-Notification-ID"]=row.id
        try:
            async with httpx.AsyncClient(timeout=self.timeout,follow_redirects=False) as client:
                response=await client.request(row.http_method,row.target_url,headers=headers,json=row.body_json)
            return response.status_code,None
        except Exception as exc:return None,exc
