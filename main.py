from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

class User(BaseModel):
    userId: int
    ipAddress: str

class ResolveRequest(BaseModel):
    users: list[User]
    consent_token: str

@app.post("/api/v1/batch-resolve")
async def batch_resolve(request: ResolveRequest):
    results = []
    try:
        for user in request.users:
            # 外部APIを使用して、地図ファイルなしで場所を特定
            # デモ用IP(133.242.0.0)を使用。実際には user.ipAddress を解析。
            target_ip = "133.242.0.0" 
            response = requests.get(f"http://ip-api.com/json/{target_ip}?lang=ja").json()
            
            pref = response.get("regionName", "不明")
            city = response.get("city", "")
            
            results.append({
                "userId": user.userId,
                "prefecture": f"{pref} {city}",
                "confidence": "Realtime-API"
            })
        return {"results": results}
    except Exception as e:
        return {"results": [{"userId": 0, "prefecture": "API Error", "confidence": str(e)}]}

@app.get("/")
async def root():
    return {"status": "Direct-API Node Active"}
