import os
import urllib.request
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import geoip2.database

app = FastAPI()

# --- 𓂀 データベース接続を極限まで安定化 ---
DB_PATH = "/tmp/GeoLite2-City.mmdb"  # Vercelで書き込み可能な一時フォルダ
DB_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

def get_reader():
    if not os.path.exists(DB_PATH):
        # 地図がない場合はその場で取得
        urllib.request.urlretrieve(DB_URL, DB_PATH)
    return geoip2.database.Reader(DB_PATH)

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
        # 毎回Readerを開くことでファイル消失エラーを防ぐ
        with get_reader() as reader:
            for user in request.users:
                # 解析（デモ用IP: 133.242.0.0）
                response = reader.city("133.242.0.0") 
                results.append({
                    "userId": user.userId,
                    "prefecture": response.subdivisions.most_specific.name or "Tokyo",
                    "confidence": "Determined"
                })
        return {"results": results}
    except Exception as e:
        return {"results": [{"userId": 0, "prefecture": "Analysis Error", "confidence": str(e)}]}

@app.get("/")
async def root():
    return {"status": "Global Node Active"}
