from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.detection.heuristics import detect


class AnalyzeRequest(BaseModel):
    text: str


app = FastAPI(
    title="CAGE - Context-Aware Guard for LLM Exploits API",
    description="Backend API for prompt injection detection",
    version="1.0.0",
)

# CORS middleware setup to allow request from Vite frontend (localhost:5173 & localhost:3000)
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Basic health check endpoint"""
    return {"status": "ok"}


@app.post("/analyze")
def analyze_prompt(payload: AnalyzeRequest):
    """
    Analyzes prompt text for injection patterns and returns detection verdict.
    """
    result = detect(payload.text)
    return {
        "flagged": result.flagged,
        "score": result.score,
        "attack_type": result.attack_type,
        "matched_patterns": result.matched_patterns,
        "input_text": payload.text,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
