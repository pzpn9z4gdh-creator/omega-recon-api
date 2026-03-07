"""
𓂀 roblox-geo-resolver
IP-based geolocation resolver for Roblox users with explicit consent
Version: 2.0.0
License: MIT
"""

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import geoip2.database
import asyncio
from typing import List, Dict, Optional
import logging
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
GEOIP_DB_PATH = os.getenv('GEOIP_DB_PATH', './GeoLite2-City.mmdb')
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', 100))
REQUIRE_CONSENT = os.getenv('REQUIRE_CONSENT', 'true').lower() == 'true'

app = FastAPI(
    title="Roblox Geo Resolver",
    description="IP-based geolocation resolution for Roblox users (requires explicit consent)",
    version="2.0.0",
    contact={
        "name": "Your Name",
        "url": "https://github.com/yourusername/roblox-geo-resolver",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# ==================== Models ====================

class UserLocation(BaseModel):
    """Single user location data"""
    userId: int
    ipAddress: str
    country: Optional[str] = None
    countryCode: Optional[str] = None
    prefecture: Optional[str] = None
    city: Optional[str] = None
    postalCode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracyRadius: Optional[int] = None
    timeZone: Optional[str] = None
    confidence: str = "unknown"
    status: str
    message: Optional[str] = None
    timestamp: str

class BatchAnalysisRequest(BaseModel):
    """Batch analysis request model"""
    users: List[Dict[str, any]] = Field(
        ...,
        description="List of users with userId and ipAddress",
        max_items=MAX_BATCH_SIZE
    )
    consent_token: str = Field(
        ...,
        description="Proof of user consent (required if REQUIRE_CONSENT=true)",
        min_length=10 if REQUIRE_CONSENT else 0
    )
    
    class Config:
        schema_extra = {
            "example": {
                "users": [
                    {"userId": 123456, "ipAddress": "203.0.113.1"},
                    {"userId": 789012, "ipAddress": "198.51.100.2"}
                ],
                "consent_token": "user-consent-hash-2024"
            }
        }

class BatchResponse(BaseModel):
    """Batch analysis response model"""
    success: bool
    timestamp: str
    statistics: Dict[str, int]
    results: List[UserLocation]

class StatusResponse(BaseModel):
    """System status response model"""
    status: str
    database: Dict[str, any]
    config: Dict[str, any]
    version: str
    timestamp: str

# ==================== Services ====================

class GeoResolver:
    """Geolocation resolver service"""
    
    def __init__(self):
        self.db_path = GEOIP_DB_PATH
        self.db_available = False
        self.reader = None
        self._init_database()
    
    def _init_database(self):
        """Initialize GeoIP2 database"""
        try:
            self.reader = geoip2.database.Reader(self.db_path)
            self.db_available = True
            logger.info(f"✅ GeoIP2 database loaded: {self.db_path}")
        except FileNotFoundError:
            logger.error(f"❌ GeoIP2 database not found: {self.db_path}")
            logger.info("📥 Download from: https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GeoIP2 database: {e}")
    
    def _calculate_confidence(self, accuracy_radius: Optional[int]) -> str:
        """Calculate confidence level based on accuracy radius"""
        if not accuracy_radius:
            return "unknown"
        if accuracy_radius < 20:
            return "high"
        elif accuracy_radius < 50:
            return "medium"
        else:
            return "low"
    
    async def resolve(self, user_id: int, ip_address: str) -> UserLocation:
        """
        Resolve location for a single user
        
        Args:
            user_id: Roblox user ID
            ip_address: User's IP address (with consent)
            
        Returns:
            UserLocation object with resolution results
        """
        timestamp = datetime.now(pytz.UTC).isoformat()
        
        # Check database availability
        if not self.db_available:
            return UserLocation(
                userId=user_id,
                ipAddress=ip_address,
                status="error",
                message="GeoIP database not available",
                timestamp=timestamp
            )
        
        # Validate IP address format
        if not self._validate_ip(ip_address):
            return UserLocation(
                userId=user_id,
                ipAddress=ip_address,
                status="error",
                message="Invalid IP address format",
                timestamp=timestamp
            )
        
        try:
            response = self.reader.city(ip_address)
            
            return UserLocation(
                userId=user_id,
                ipAddress=ip_address,
                country=response.country.name,
                countryCode=response.country.iso_code,
                prefecture=response.subdivisions.most_specific.name if response.subdivisions else None,
                city=response.city.name if response.city else None,
                postalCode=response.postal.code,
                latitude=response.location.latitude,
                longitude=response.location.longitude,
                accuracyRadius=response.location.accuracy_radius,
                timeZone=response.location.time_zone,
                confidence=self._calculate_confidence(response.location.accuracy_radius),
                status="resolved",
                timestamp=timestamp
            )
            
        except geoip2.errors.AddressNotFoundError:
            logger.warning(f"IP not found: {ip_address}")
            return UserLocation(
                userId=user_id,
                ipAddress=ip_address,
                status="not_found",
                message="IP address not found in database",
                timestamp=timestamp
            )
        except Exception as e:
            logger.error(f"Resolution error for user {user_id}: {e}")
            return UserLocation(
                userId=user_id,
                ipAddress=ip_address,
                status="error",
                message=str(e),
                timestamp=timestamp
            )
    
    def _validate_ip(self, ip: str) -> bool:
        """Basic IP address validation"""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except:
            return False
    
    async def batch_resolve(self, users: List[Dict]) -> List[UserLocation]:
        """
        Resolve locations for multiple users
        
        Args:
            users: List of dicts with 'userId' and 'ipAddress'
            
        Returns:
            List of UserLocation objects
        """
        tasks = []
        for user in users:
            user_id = user.get('userId')
            ip_address = user.get('ipAddress')
            
            if not user_id or not ip_address:
                logger.warning(f"Skipping invalid user entry: {user}")
                continue
            
            tasks.append(self.resolve(user_id, ip_address))
        
        return await asyncio.gather(*tasks)

# ==================== Initialize Services ====================

resolver = GeoResolver()

# ==================== API Endpoints ====================

@app.post("/api/v1/batch-resolve", response_model=BatchResponse)
async def batch_resolve(request: BatchAnalysisRequest):
    """
    Resolve locations for multiple users in batch
    
    - Requires explicit IP addresses for each user
    - Consent token is required (configurable via REQUIRE_CONSENT)
    - Maximum batch size: {MAX_BATCH_SIZE} users
    """
    # Validate consent if required
    if REQUIRE_CONSENT and (not request.consent_token or len(request.consent_token) < 10):
        raise HTTPException(
            status_code=400,
            detail="Valid consent token is required"
        )
    
    # Validate input
    if not request.users:
        raise HTTPException(
            status_code=400,
            detail="No users provided for analysis"
        )
    
    if len(request.users) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum ({MAX_BATCH_SIZE})"
        )
    
    # Process batch resolution
    results = await resolver.batch_resolve(request.users)
    
    # Calculate statistics
    resolved = sum(1 for r in results if r.status == 'resolved')
    not_found = sum(1 for r in results if r.status == 'not_found')
    errors = sum(1 for r in results if r.status == 'error')
    
    return BatchResponse(
        success=True,
        timestamp=datetime.now(pytz.UTC).isoformat(),
        statistics={
            "total": len(results),
            "resolved": resolved,
            "not_found": not_found,
            "errors": errors
        },
        results=results
    )

@app.get("/api/v1/status", response_model=StatusResponse)
async def get_status():
    """Get system status and configuration"""
    return StatusResponse(
        status="operational" if resolver.db_available else "degraded",
        database={
            "available": resolver.db_available,
            "path": resolver.db_path
        },
        config={
            "max_batch_size": MAX_BATCH_SIZE,
            "require_consent": REQUIRE_CONSENT
        },
        version="2.0.0",
        timestamp=datetime.now(pytz.UTC).isoformat()
    )

@app.get("/api/v1/docs/privacy")
async def privacy_docs():
    """Privacy policy and data handling documentation"""
    return {
        "privacy_policy": {
            "version": "1.0.0",
            "last_updated": "2024-01-01",
            "data_collected": [
                "IP addresses (with explicit consent)",
                "Roblox User IDs"
            ],
            "data_usage": "Geolocation resolution for analytical purposes",
            "data_retention": "No permanent storage of IP addresses",
            "legal_basis": "Explicit user consent (GDPR Article 6)",
            "consent_required": REQUIRE_CONSENT,
            "third_party_services": [
                {
                    "name": "MaxMind GeoIP2",
                    "purpose": "IP geolocation database",
                    "privacy_policy": "https://www.maxmind.com/en/privacy-policy"
                }
            ],
            "contact": "privacy@yourdomain.com"
        }
    }

@app.get("/")
async def root():
    """API root with documentation links"""
    return {
        "name": "Roblox Geo Resolver API",
        "version": "2.0.0",
        "documentation": "/docs",
        "status": "/api/v1/status",
        "privacy": "/api/v1/docs/privacy",
        "repository": "https://github.com/yourusername/roblox-geo-resolver"
    }

# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(pytz.UTC).isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
