
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    u_id = request.userId
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 並列リクエストで全データを一括取得
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        h_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/username-history")
        # 限定アイテムの市場価値(RAP)を直接取得
        inv_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&limit=100")
        b_res = await client.get(f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=100")
        g_res = await client.get(f"https://groups.roblox.com/v1/users/{u_id}/groups/roles")

    u_data = u_res.json()
    history = h_res.json().get('data', [])
    inventory = inv_res.json().get('data', [])
    badges = b_res.json().get('data', [])
    groups = g_res.json().get('data', [])

    # --- 𓂀 鑑定ロジック1: 過去名と信頼性 ---
    names = [h['name'] for h in history]
    created_at = u_data.get("created", "2024-01-01T")
    days_old = (datetime.now() - datetime.strptime(created_at[:10], "%Y-%m-%d")).days
    
    # リスクレベル算出 (過去名の多さやバッジ密度から)
    risk_score = "LOW"
    if len(names) > 3 or days_old < 30: risk_score = "HIGH (警告)"
    elif len(names) > 0: risk_score = "MEDIUM"

    # --- 𓂀 鑑定ロジック2: 経済力 (RAP合計) ---
    total_rap = sum(item.get('recentAveragePrice', 0) for item in inventory)
    asset_str = f"{total_rap:,} Robux (時価総額)"

    # --- 𓂀 鑑定ロジック3: 外部連携とサブ垢推論 ---
    # 日本人コミュニティへの所属確認
    pref_db = {"東京": "東京都", "大阪": "大阪府", "神奈川": "神奈川県", "愛知": "愛知県", "福岡": "福岡県"}
    location = "日本国内"
    raw_text = " ".join([b['name'] for b in badges] + [g['group']['name'] for g in groups])
    for k, v in pref_db.items():
        if k in raw_text: location = f"{v}付近" ; break

    return {
        "intel": {
            "target": u_data.get("name"),
            "history": ", ".join(names) if names else "なし",
            "age": f"{round(days_old/365, 1)}年",
            "risk": risk_score,
            "assets": asset_str,
            "location": location,
            "alt_inference": "本垢濃厚" if total_rap > 500 or days_old > 365 else "サブ垢の可能性あり"
        }
    }
