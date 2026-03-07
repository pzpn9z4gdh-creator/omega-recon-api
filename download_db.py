#!/usr/bin/env python3
"""
GeoIP2 Database Downloader for Roblox Geo Resolver
Downloads the latest GeoLite2-City.mmdb database from a reliable mirror
"""

import urllib.request
import os
import sys
import hashlib
from pathlib import Path

# Database URLs (multiple mirrors for reliability)
DATABASE_URLS = [
    "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb",
    "https://git.io/GeoLite2-City.mmdb",
    "https://cdn.jsdelivr.net/gh/P3TERX/GeoLite.mmdb@download/GeoLite2-City.mmdb"
]

DATABASE_FILENAME = "GeoLite2-City.mmdb"
EXPECTED_SIZE = 70_000_000  # ~70MB (approximate)

class DownloadProgress:
    """Progress reporter for downloads"""
    
    def __init__(self):
        self.last_percent = 0
    
    def report(self, block_count, block_size, total_size):
        """Report download progress"""
        if total_size > 0:
            downloaded = block_count * block_size
            percent = int(downloaded * 100 / total_size)
            
            if percent >= self.last_percent + 5:  # Report every 5%
                self.last_percent = percent
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total_size / (1024 * 1024)
                bar = '█' * (percent // 5) + '░' * (20 - percent // 5)
                sys.stdout.write(f"\r📥 Downloading: [{bar}] {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)")
                sys.stdout.flush()
            
            if percent >= 100:
                sys.stdout.write("\n")

def verify_database(filename: str) -> bool:
    """
    Verify the downloaded database file
    
    Args:
        filename: Path to the database file
        
    Returns:
        True if file exists and has reasonable size
    """
    if not os.path.exists(filename):
        return False
    
    file_size = os.path.getsize(filename)
    if file_size < 10_000_000:  # Less than 10MB is suspicious
        print(f"❌ Database file too small ({file_size / 1024 / 1024:.1f} MB)")
        return False
    
    print(f"✅ Database file size: {file_size / 1024 / 1024:.1f} MB")
    return True

def download_database(url: str, filename: str) -> bool:
    """
    Download database from specified URL
    
    Args:
        url: Source URL
        filename: Output filename
        
    Returns:
        True if download successful
    """
    try:
        print(f"🌐 Downloading from: {url}")
        progress = DownloadProgress()
        
        # Download with progress reporting
        urllib.request.urlretrieve(
            url, 
            filename, 
            reporthook=progress.report
        )
        
        return True
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        return False

def main():
    """Main download function"""
    print("=" * 50)
    print("🌍 GeoIP2 Database Downloader")
    print("=" * 50)
    
    # Check if database already exists
    if os.path.exists(DATABASE_FILENAME):
        file_size = os.path.getsize(DATABASE_FILENAME) / 1024 / 1024
        response = input(f"📁 Database already exists ({file_size:.1f} MB). Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("✅ Using existing database")
            return
    
    # Try each URL until success
    success = False
    for i, url in enumerate(DATABASE_URLS, 1):
        print(f"\n🔄 Attempt {i}/{len(DATABASE_URLS)}")
        
        if download_database(url, DATABASE_FILENAME):
            if verify_database(DATABASE_FILENAME):
                success = True
                break
        else:
            # Remove partial download if any
            if os.path.exists(DATABASE_FILENAME):
                os.remove(DATABASE_FILENAME)
    
    if success:
        print("\n" + "=" * 50)
        print("✅ SUCCESS: Database downloaded and verified!")
        print(f"📁 File: {DATABASE_FILENAME}")
        print(f"📦 Size: {os.path.getsize(DATABASE_FILENAME) / 1024 / 1024:.1f} MB")
        print("=" * 50)
        
        # Create a .gitignore entry for the database
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            if DATABASE_FILENAME not in content:
                with open(gitignore, 'a') as f:
                    f.write(f"\n# GeoIP Database\n{DATABASE_FILENAME}\n")
                print("📝 Added database to .gitignore")
    else:
        print("\n" + "=" * 50)
        print("❌ FAILED: Could not download database from any mirror")
        print("\nPlease download manually from:")
        print("https://dev.maxmind.com/geoip/geolite2-free-geolocation-data")
        print("=" * 50)
        sys.exit(1)

if __name__ == "__main__":
    main()
