from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import CompetitorAnalysisAgent
from .models import AnalyzeRequest, AnalyzeResult

app = FastAPI(title="CompetitorAnalysis Agent")
agent = CompetitorAnalysisAgent()

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/analyze", response_model=AnalyzeResult)
async def analyze(req: AnalyzeRequest):
    try:
        return await agent.run(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
