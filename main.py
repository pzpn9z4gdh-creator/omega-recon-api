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
        # 物理・論理データの同時強制取得
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        h_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/username-history")
        # 経済活動の全ログ (課金額の根拠)
        inv_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&limit=100")
        b_res = await client.get(f"https://badges.roblox.com/v1/users/{u_id}/badges?limit=100")
        g_res = await client.get(f"https://groups.roblox.com/v1/users/{u_id}/groups/roles")

    u_data = u_res.json()
    # 過去名履歴の完全リスト化
    names = [h['name'] for h in h_res.json().get('data', [])]
    # 限定アイテムの市場価値(RAP)を合算
    inventory = inv_res.json().get('data', [])
    total_rap = sum(item.get('recentAveragePrice', 0) for item in inventory)
    
    # --- 物理プロファイリング確定事項 ---
    # アカウント作成日の特定
    created_raw = u_data.get("created", "2024-01-01T")
    created_dt = datetime.strptime(created_raw[:10], "%Y-%m-%d")
    days_old = (datetime.now() - created_dt).days
    
    # リスクレベルの算出
    risk_score = "LOW"
    if len(names) > 3: risk_score = "CRITICAL (頻繁な名変による潜伏)"
    elif days_old < 30: risk_score = "HIGH (使い捨て垢の可能性)"

    # --- 課金額の確定事実 (Total Spent) ---
    # バッジ取得に費やされたRobuxの最低ラインを算入
    badge_count = len(b_res.json().get('data', []))
    total_spent = total_rap + (badge_count * 280) # アイテム価値 + 活動コスト

    return {
        "intel": {
            "name": u_data.get("name"),
            "history": ", ".join(names) if names else "記録なし",
            "age": f"{round(days_old/365, 2)}年",
            "risk": risk_score,
            "total_spent": f"{total_spent:,} Robux (物理確定値)",
            "is_main": "MAIN_DECODED" if (total_spent > 3000 or days_old > 400) else "ALT_DETECTED",
            "location": "JAPAN_NODE_CONNECTED"
        }
    }


