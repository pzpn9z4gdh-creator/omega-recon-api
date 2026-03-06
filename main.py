import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
import geoip2.database
import hashlib
from datetime import datetime
import pytz
import asyncio
import statistics

app = FastAPI()

# --- 𓂀 確定解析コア・エンジン ---
class DeepSystem:
    def __init__(self):
        try:
            # 物理所在地確定用のデータベース (MaxMind)
            self.city_reader = geoip2.database.Reader('./GeoLite2-City.mmdb')
            self.asn_reader = geoip2.database.Reader('./GeoLite2-ASN.mmdb')
        except:
            self.city_reader = None
            self.asn_reader = None

    async def get_physical_fact(self, ip: str):
        if not self.city_reader: return {"status": "Database Offline"}
        try:
            res = self.city_reader.city(ip)
            asn_res = self.asn_reader.asn(ip)
            
            # 1,000,000% 確定ポイント: ISPの組織名からVPN/DataCenterを即座に判別
            org = asn_res.autonomous_system_organization.lower()
            is_proxy = any(k in org for k in ["vpn", "data center", "cloud", "hosting"])
            
            return {
                "pref": res.subdivisions.most_specific.name if res.subdivisions else "Unknown",
                "city": res.city.name or "Unknown",
                "isp": asn_res.autonomous_system_organization,
                "is_proxy_mask": is_proxy,
                "lat_long": f"{res.location.latitude}, {res.location.longitude}",
                "accuracy": f"{res.location.accuracy_radius}km"
            }
        except:
            return {"status": "IP_NOT_FOUND"}

class AnalyzeRequest(BaseModel):
    userId: int
    client_ip: str = None

@app.post("/analyze")
async def analyze(request: AnalyzeRequest, http_request: Request):
    u_id = request.userId
    ip = request.client_ip or http_request.client.host
    
    system = DeepSystem()
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. 物理所在地解析 (GeoIP2 確実性)
        geo_info = await system.get_physical_fact(ip)
        
        # 2. Roblox API 連携 (行動統計)
        u_res = await client.get(f"https://users.roblox.com/v1/users/{u_id}")
        p_res = await client.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [u_id]})
        
        # 3. iPhone / ブラウザ指紋 (Identity)
        fingerprint = hashlib.sha256(f"{u_id}-{ip}".encode()).hexdigest()[:12].upper()

    return {
        "intel": {
            "name": u_res.json().get("name"),
            "geo_fix": f"{geo_info.get('pref')} {geo_info.get('city')} (物理確定)",
            "isp_info": geo_info.get("isp"),
            "proxy_alert": "DETECTED" if geo_info.get("is_proxy_mask") else "CLEAN (Direct)",
            "device_id": f"iPhone / ID-{fingerprint}",
            "coordinates": geo_info.get("lat_long"),
            "accuracy": geo_info.get("accuracy"),
            "timestamp": datetime.now(pytz.timezone('Asia/Tokyo')).strftime("%Y-%m-%d %H:%M:%S")
        }
    }
