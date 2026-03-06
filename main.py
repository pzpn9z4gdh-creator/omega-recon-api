from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.get("/")
def home():
    return {"status": "OMEGA RECON Online"}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    # ここでRoblox IDを受け取ります
    return {"roblox_id": request.userId, "message": "Analyzing Japanese User..."}
