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
    async with httpx.AsyncClient(timeout=25.0) as client:
        # 1. ユーザー基本情報（作成日特定用）
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        # 2. バッジ（本垢判定の最重要データ）
        b_res = await client.get(f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=100")
        # 3. グループ（居住地特定用）
        g_res = await client.get(f"https://groups.roblox.com/v1/users/{u_id}/groups/roles")

    u_data = u_res.json()
    badges = b_res.json().get('data', [])
    groups = g_res.json().get('data', [])

    # --- 1. アカウント鑑定ロジック ---
    created_at = u_data.get("created", "2026-01-01T00:00:00Z")
    created_date = datetime.strptime(created_at[:10], "%Y-%m-%d")
    days_old = (datetime.now() - created_date).days
    
    # 判定スコア計算
    score = 0
    if days_old > 365: score += 40 # 1年以上経過
    if len(badges) > 20: score += 30 # バッジ保有数
    if len(groups) > 3: score += 30 # グループ所属数
    
    account_type = f"本垢 (信頼度{score}%)" if score >= 60 else f"サブ垢/捨て垢 (信頼度{100-score}%)"

    # --- 2. 居住地・資産の強制特定 ---
    pref_db = {"東京": "東京都", "大阪": "大阪府", "神奈川": "神奈川県", "愛知": "愛知県", "福岡": "福岡県"}
    location = "日本国内（特定中）"
    raw_text = " ".join([b['name'] for b in badges] + [g['group']['name'] for g in groups])
    for k, v in pref_db.items():
        if k in raw_text:
            location = f"{v}付近"
            break

    est_robux = (len(badges) * 450) + (len(groups) * 200)

    return {
        "target_info": {"name": u_data.get("name")},
        "osint_intel": {
            "location": location,
            "robux_asset": f"約 {est_robux:,} Robux",
            "account_type": account_type,
            "years_active": f"{round(days_old/365, 1)} 年"
        }
    }
