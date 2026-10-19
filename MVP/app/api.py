from urllib.parse import urlparse
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from app.config import Settings
from app.models import NotificationRow
from app.repository import IdempotencyConflict, NotFound, NotificationRepository
from app.schemas import NotificationIn

def public_row(row: NotificationRow) -> dict:
    return {"notification_id":row.id,"status":row.status,"attempt_count":row.attempt_count,"next_attempt_at":row.next_attempt_at,"last_error_code":row.last_error_code,"created_at":row.created_at,"updated_at":row.updated_at,"delivered_at":row.delivered_at}

def create_app(repo: NotificationRepository, settings: Settings) -> FastAPI:
    app=FastAPI(title="API Notification Service")
    def auth(value: str|None):
        if value != f"Bearer {settings.internal_auth_token}": raise HTTPException(401,"unauthorized")
    def validate_target(target):
        parsed=urlparse(target.url)
        if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username: raise HTTPException(422,"target URL must be HTTP(S) without credentials")
        if settings.host_allowlist() and parsed.hostname.lower() not in settings.host_allowlist(): raise HTTPException(422,"target host is not allowlisted")
        if target.method != "POST": raise HTTPException(422,"only POST is supported")
        if any(k.lower() in {"idempotency-key","x-notification-id"} for k in target.headers): raise HTTPException(422,"system idempotency headers cannot be overridden")
    @app.post("/v1/notifications",status_code=202)
    async def create(payload: NotificationIn, request: Request, authorization: str|None=Header(default=None)):
        auth(authorization);validate_target(payload.target)
        if int(request.headers.get("content-length","0")) > settings.max_request_bytes: raise HTTPException(422,"request too large")
        data=payload.model_dump(mode="json")
        try: row=repo.create(data,settings.max_attempts)
        except IdempotencyConflict: raise HTTPException(409,"idempotency key conflicts with existing request")
        except Exception: raise HTTPException(500,"persistence failure")
        return {"notification_id":row.id,"status":row.status}
    @app.get("/v1/notifications/{notification_id}")
    async def get(notification_id: str, authorization: str|None=Header(default=None)):
        auth(authorization)
        try:return JSONResponse(public_row(repo.get(notification_id)))
        except NotFound:raise HTTPException(404,"not found")
    return app
