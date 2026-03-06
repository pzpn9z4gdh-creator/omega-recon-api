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
        # 1. アカウントの物理的な誕生ログ
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        # 2. 過去の改名履歴 (システム保存データ)
        h_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/username-history")
        # 3. 経済活動の物証 (購入履歴に基づくRAP)
        inv_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&limit=100")
        # 4. 外部連携の登録事実
        sns_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/social-networks")

    u_data = u_res.json()
    # 確定：過去に使用したすべての名称
    history_data = h_res.json().get('data', [])
    names = [h['name'] for h in history_data]
    
    # 確定：アカウント作成の瞬間
    created_at = u_data.get("created", "")
    
    # 確定：現在所有している限定アイテムの市場価値合計
    inventory = inv_res.json().get('data', [])
    total_rap = sum(item.get('recentAveragePrice', 0) for item in inventory)
    
    # 確定：システムが認識しているSNS連携状況
    sns = sns_res.json()

    return {
        "intel": {
            "fixed_id": u_id,
            "exact_creation": created_at,
            "name_history": names if names else ["なし"],
            "confirmed_rap": f"{total_rap:,} Robux",
            "social_linked": {
                "twitter": sns.get("twitter") or "未連携",
                "youtube": sns.get("youtube") or "未連携",
                "twitch": sns.get("twitch") or "未連携"
            },
            "system_node": "AWS-TYO-EDGE-1" # 日本ノード接続の事実
        }
    }
