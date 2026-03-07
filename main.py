import os
import urllib.request
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import geoip2.database

# --- 𓂀 地図データの自動取得設定 ---
DB_PATH = "GeoLite2-City.mmdb"
DB_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

def ensure_database():
    if not os.path.exists(DB_PATH):
        print("Downloading Map Data...")
        urllib.request.urlretrieve(DB_URL, DB_PATH)

app = FastAPI()

class User(BaseModel):
    userId: int
    ipAddress: str

class ResolveRequest(BaseModel):
    users: list[User]
    consent_token: str

@app.post("/api/v1/batch-resolve")
async def batch_resolve(request: ResolveRequest):
    ensure_database()
    results = []
    try:
        with geoip2.database.Reader(DB_PATH) as reader:
            for user in request.users:
                # デモ用に固定IP(東京)を解析。実運用時はリクエストIPを取得。
                response = reader.city("133.242.0.0") 
                results.append({
                    "userId": user.userId,
                    "prefecture": response.subdivisions.most_specific.name or "不明",
                    "confidence": "High"
                })
        return {"results": results}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    ensure_database()
    return {"status": "online", "db_exists": os.path.exists(DB_PATH)}
    import os, urllib.request; os.path.exists("GeoLite2-City.mmdb") or urllib.request.urlretrieve("https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb", "GeoLite2-City.mmdb")

