import sys
import os

# Add the correct directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "python_iptv"))
from src.playlist_generator import PlaylistGenerator

def verify():
    gen = PlaylistGenerator()
    
    print("Generating playlist...")
    gen.generate_m3u8("playlist.m3u8")
    
    print("Generating EPG...")
    from src.epg_merger import merge_epg
    merge_epg("epg.xml")
    
    print("Verifying EPG file for new IDs...")
    targets = ["Eurosport.1.it", "Eurosport.2.it", "Blaze.it", "DisneyChannel.ch", "Fox.it"]
    with open("epg.xml", "r", encoding="utf-8") as f:
        content = f.read()
        for t in targets:
            if f'channel="{t}"' in content:
                print(f"[OK] {t} found in EPG")
            else:
                print(f"[FAIL] {t} NOT found in EPG")

    print("Verifying playlist for new groups...")
    with open("playlist.m3u8", "r", encoding="utf-8") as f:
        content = f.read()
        if "group-title=\"Sport\"" in content and "group-title=\"Kids\"" in content:
            print("[OK] Groups found in playlist")
        else:
            print("[FAIL] Groups NOT found in playlist")

if __name__ == "__main__":
    verify()
