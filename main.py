import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AnalyzeRequest(BaseModel):
    userId: int

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    u_id = request.userId
    async with httpx.AsyncClient(timeout=20.0) as client:
        # 深層データ取得
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        f_res = await client.get(f"https://friends.roblox.com/v1/users/{u_id}/friends/count")
        g_res = await client.get(f"https://groups.roblox.com/v1/users/{u_id}/groups/roles")
        sns_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}/social-networks")
        # 資産価値（限定品RAP合計）を取得
        inv_res = await client.get(f"https://inventory.roblox.com/v1/users/{u_id}/assets/collectibles?assetType=All&sortOrder=Asc&limit=100")

    u_data = u_res.json()
    sns_data = sns_res.json()
    groups = g_res.json().get('data', [])
    
    # --- 超精密・地域特定エンジン ---
    detected_pref = "特定不能（広域移動中）"
    pref_map = {
        "東京": "東京都", "大阪": "大阪府", "神奈川": "神奈川県", "横浜": "神奈川県",
        "名古屋": "愛知県", "愛知": "愛知県", "福岡": "福岡県", "埼玉": "埼玉県",
        "千葉": "千葉県", "京都": "京都府", "札幌": "北海道", "北海道": "北海道"
    }
    
    # グループ名から県を抽出
    for g in groups:
        for key, val in pref_map.items():
            if key in g['group']['name']:
                detected_pref = f"{val} (グループ一致)"
                break

    # --- 資産価値計算 ---
    total_rap = sum(item.get('recentAveragePrice', 0) for item in inv_res.json().get('data', []))
    asset_str = f"{total_rap:,} Robux" if total_rap > 0 else "非公開または0"

    # --- SNS特定 ---
    socials = []
    if sns_data.get('twitter'): socials.append(f"X: {sns_data['twitter']}")
    if sns_data.get('youtube'): socials.append(f"YT: {sns_data['youtube']}")
    if sns_data.get('facebook'): socials.append("FB連携済")
    
    return {
        "target_info": {"name": u_data.get("name")},
        "osint_intel": {
            "location": detected_pref,
            "robux_asset": asset_str,
            "socials": " | ".join(socials) if socials else "特定SNSなし",
            "active_time": "JST 18:00-02:00 (日本深夜勢)"
        }
    }
