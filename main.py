from fastapi import FastAPI
from pydantic import BaseModel
import httpx

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.get("/")
def home():
    return {"status": "OMEGA OSINT System Active"}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    u_id = request.userId
    async with httpx.AsyncClient() as client:
        # 基本情報 & 作成日
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        u_data = u_res.json()
        
        # 名前履歴 (過去の名前)
        h_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/username-history")
        h_data = h_res.json()
        past_names = [name['name'] for name in h_data.get('data', [])]

        # 資産分析 (簡易)
        i_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?limit=10")
        i_data = i_res.json()
        value = sum([item.get('recentAveragePrice', 0) for item in i_data.get('data', [])])

    return {
        "name": u_data.get("name"),
        "past_names": past_names,
        "created": u_data.get("created"),
        "value": f"{value} Robux",
        "risk": "HIGH" if len(past_names) > 0 else "LOW"
    }

