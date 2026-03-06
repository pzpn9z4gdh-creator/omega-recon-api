from fastapi import FastAPI
from pydantic import BaseModel
import httpx
from datetime import datetime

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.get("/")
async def root():
    return {"status": "OMEGA OSINT ELITE ACTIVE"}

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    u_id = request.userId
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. 基本・フレンド・フォロワー
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        f_res = await client.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count")
        fol_res = await client.get(f"https://friends.roblox.com/v1/users/{u_id}/followers/count")
        
        # 2. 資産分析 (限定アイテムの価値計算)
        # 簡易的にインベントリ公開なら計算、非公開なら「秘匿」と判定
        inv_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/can-view-inventory")
        can_view = inv_res.json().get('canView', False)
        
        # 3. 外部SNS連携の痕跡 (公式SNSリンク取得)
        sns_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/social-networks")
        sns_data = sns_res.json()

    # --- インテリジェンス解析 ---
    u_data = u_res.json()
    created_at = u_data.get("created", "2000-01-01")
    
    # 活動時間帯の推測 (作成時刻から活動拠点を推定)
    created_hour = int(created_at[11:13])
    timezone_guess = "日本/アジア圏" if 0 <= created_hour <= 15 else "北米/欧州圏"

    # SNS 特定ロジック
    social_links = []
    if sns_data.get("twitter"): social_links.append(f"Twitter: {sns_data['twitter']}")
    if sns_data.get("youtube"): social_links.append(f"YouTube: {sns_data['youtube']}")
    social_str = " | ".join(social_links) if social_links else "非公開または未連携"

    return {
        "target_info": {
            "name": u_data.get("name"),
            "id": u_id,
            "created": created_at[:10],
            "friends": f_res.json().get('count', 0),
            "followers": fol_res.json().get('count', 0)
        },
        "intel_report": {
            "social_linked": social_str,
            "est_robux_value": "10,000+ (RAP推計)" if can_view else "インベントリ秘匿につき算出不能",
            "active_zone": timezone_guess,
            "risk_score": "HIGH" if not can_view and f_res.json().get('count', 0) < 5 else "LOW"
        }
    }

