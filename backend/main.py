from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.ingestion.router import router as ingestion_router

app = FastAPI(title="MedRoBERTa PII Redaction API")

# Allow CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion_router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "PII Redaction Service is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
