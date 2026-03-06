import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import math

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    u_id = request.userId
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 多角的データ収集
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        b_res = await client.get(f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=100")
        g_res = await client.get(f"https://groups.roblox.com/v1/users/{u_id}/groups/roles")
        f_res = await client.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count")

    u_data = u_res.json()
    badges = b_res.json().get('data', [])
    groups = g_res.json().get('data', [])
    friend_count = f_res.json().get('count', 0)

    # --- 𓂀 アカウント鑑定スコアリング (アルゴリズム) ---
    score = 0
    # 1. アカウントの年齢 (長生きなほど本垢)
    created_at = u_data.get("created", "2024-01-01T00:00:00Z")
    created_date = datetime.strptime(created_at[:10], "%Y-%m-%d")
    days_old = (datetime.now() - created_date).days
    
    if days_old > 730: score += 40  # 2年以上
    elif days_old > 365: score += 25 # 1年以上
    elif days_old > 90: score += 10  # 3ヶ月以上

    # 2. 活動密度 (バッジ数)
    badge_count = len(badges)
    if badge_count > 50: score += 30
    elif badge_count > 10: score += 15

    # 3. コミュニティ所属 (グループ数)
    if len(groups) > 5: score += 20
    elif len(groups) > 1: score += 10

    # 4. 人間関係 (フレンド数)
    if friend_count > 50: score += 10

    # 最終判定
    if score >= 70:
        result = f"本垢確定 (信頼度{score}%)"
    elif score >= 40:
        result = f"本垢の可能性高 (信頼度{score}%)"
    else:
        result = f"サブ垢/捨て垢濃厚 (信頼度{100-score}%)"

    # --- 𓂀 居住地・資産の強制特定 ---
    pref_db = {"東京": "東京都", "大阪": "大阪府", "神奈川": "神奈川県", "愛知": "愛知県", "福岡": "福岡県", "千葉": "千葉県", "埼玉": "埼玉県"}
    location = "日本国内（特定済み）"
    raw_text = " ".join([b['name'] for b in badges] + [g['group']['name'] for g in groups])
    for k, v in pref_db.items():
        if k in raw_text:
            location = f"{v}付近"
            break

    est_robux = (badge_count * 480) + (len(groups) * 350) + (friend_count * 5)

    return {
        "osint_intel": {
            "account_type": result,
            "location": location,
            "robux_asset": f"約 {est_robux:,} Robux",
            "years_active": f"活動歴 {round(days_old/365, 1)}年"
        }
    }
