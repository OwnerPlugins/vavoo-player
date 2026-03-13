import sys
import os

# Add the correct directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "python_iptv"))
from src.playlist_generator import PlaylistGenerator

def list_dazn():
    gen = PlaylistGenerator()
    channels = gen.fetch_all_channels(["Italy", "Vavoo"]) # Check Vavoo group too
    dazn_ch = [c for c in channels if "DAZN" in c['name'].upper()]
    
    print(f"Found {len(dazn_ch)} DAZN channels:")
    for ch in dazn_ch:
        print(f" - Name: '{ch['name']}' | URL: {ch['url']} | Group: {ch['group']}")

if __name__ == "__main__":
    list_dazn()
