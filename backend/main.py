from fastapi import FastAPI

from backend.routers.audit import router as audit_router

app = FastAPI(title="Bias Audit Framework", version="0.1.0")
app.include_router(audit_router)
