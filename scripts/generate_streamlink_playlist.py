#!/usr/bin/env python3
"""
Generate Vavoo Playlist for Streamlink
This script generates a playlist that works with Streamlink, which supports
custom HTTP headers natively - no proxy server needed!

Usage:
    1. Generate playlist: python generate_streamlink_playlist.py
    2. Play with Streamlink: streamlink --player vlc playlist_streamlink.m3u8
    3. Or use the helper script: python play_with_streamlink.py
"""

import os
import sys
import logging
import argparse

# Add the root directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.playlist_generator import PlaylistGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_streamlink_playlist(output_path="playlist_streamlink.m3u8", groups=None):
    """
    Generate a playlist for use with Streamlink.
    
    Streamlink supports custom HTTP headers, so we can include the signature
    directly in the playlist using #EXTVLCOPT directives.
    
    Args:
        output_path: Path to save the playlist
        groups: List of groups to include
    
    Returns:
        True if successful, False otherwise
    """
    if groups is None:
        groups = ["Italy"]
    
    logger.info(f"Generating Streamlink playlist for groups: {groups}")
    
    # Create a PlaylistGenerator instance
    gen = PlaylistGenerator()
    
    # Get fresh signature using the existing method
    logger.info("Fetching authentication signature...")
    sig = gen.get_signature()
    if not sig:
        logger.error("Failed to get authentication signature")
        return False
    
    logger.info(f"Signature obtained: {sig[:30]}...")
    
    # Fetch all channels
    channels = gen.fetch_all_channels(target_groups=groups)
    if not channels:
        logger.error("No channels fetched.")
        return False
    
    logger.info(f"Fetched {len(channels)} channels")
    
    # Process channels manually (same logic as generate_m3u8)
    try:
        logger.info(f"Writing playlist to {output_path}...")
        
        # Load EPGs to populate names
        logger.info("Loading EPG data for name resolution...")
        gen.dm.load_all_epgs()
        
        # Process channels
        processed_channels = []
        logos_dir = os.path.join(os.path.dirname(__file__), "..", "logos")
        
        for ch in channels:
            norm_name = gen._normalize_name(ch['name'])
            
            # BLACKLIST
            if "RAI ITALIA" in norm_name:
                continue
            if "STAR CRIME" in norm_name:
                continue
            if "SKYSHOWTIME 1" in norm_name:
                continue
            if "SKY SPORT FOOTBALL" in norm_name:
                continue
            
            # RENAME (simplified - just use normalized name)
            categories = gen._get_categories(norm_name)
            priority = gen._get_priority(norm_name)
            
            if priority == 9999:
                if "SKY" in norm_name: priority = 200
                elif "DAZN" in norm_name: priority = 210
                elif "PRIMA" in norm_name: priority = 300
            
            # Resolve EPG ID and Logo
            epg_id = EPG_MAP.get(norm_name, "")
            
            # Resolve Clean Name from EPG
            clean_display_name = norm_name
            if epg_id:
                epg_name = gen.dm.get_clean_epg_name(epg_id)
                if epg_name:
                    clean_display_name = epg_name
            
            tvg_id = epg_id if epg_id else norm_name
            tvg_name = tvg_id if tvg_id else clean_display_name
            
            # Check local logo
            logo_path = ch.get('logo', '')
            if epg_id:
                target_fname = f"{epg_id}.png".lower()
                matched_file = None
                for f in os.listdir(logos_dir):
                    if f.lower() == target_fname:
                        matched_file = f
                        break
                if matched_file:
                    logo_path = f"https://raw.githubusercontent.com/mich-de/vavoo-player/master/logos/{matched_file}"
            
            # Duplicate channel into each matching group
            for category in categories:
                ch_copy = ch.copy()
                ch_copy['norm_name'] = norm_name
                ch_copy['group'] = category
                ch_copy['priority'] = priority
                ch_copy['tvg_id'] = tvg_id
                ch_copy['tvg_name'] = tvg_name
                ch_copy['final_logo'] = logo_path
                ch_copy['clean_name'] = clean_display_name
                processed_channels.append(ch_copy)
        
        # Sort
        processed_channels.sort(key=lambda x: (x['priority'], x['group'], x['norm_name']))
        
        if not processed_channels:
            logger.error("No valid channels to write.")
            return False
        
        logger.info(f"Processed {len(processed_channels)} channels")
        
        with open(output_path, "w", encoding="utf-8") as f:
            # Write M3U header
            epg_url = "https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"
            f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
            
            for ch in processed_channels:
                # Write VLC/Streamlink options with signature header
                f.write(f'#EXTVLCOPT:http-user-agent=okhttp/4.11.0\n')
                f.write(f'#EXTVLCOPT:http-header=mediahubmx-signature={sig}\n')
                f.write(f'#EXTVLCOPT:http-reconnect=true\n')
                f.write(f'#EXTVLCOPT:network-caching=3000\n')
                
                # Write channel info
                header = f'#EXTINF:-1 tvg-id="{ch["tvg_id"]}" tvg-name="{ch["clean_name"]}" tvg-logo="{ch["final_logo"]}" channel="{ch["tvg_id"]}" group-title="{ch["group"]}",{ch["clean_name"]}'
                f.write(f"{header}\n")
                f.write(f"{ch['url']}\n")
                
        logger.info(f"Streamlink playlist generated successfully: {output_path}")
        logger.info(f"\nTo play with Streamlink + VLC:")
        logger.info(f"  streamlink --player vlc {output_path}")
        logger.info(f"\nOr use the helper script:")
        logger.info(f"  python play_with_streamlink.py")
        return True
        
    except Exception as e:
        logger.error(f"Error writing playlist: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate Vavoo Playlist for Streamlink (no proxy needed!)")
    parser.add_argument("--output", default="playlist_streamlink.m3u8", help="Output path for the playlist")
    parser.add_argument("--groups", nargs="+", default=["Italy"], help="Groups to include")
    
    args = parser.parse_args()
    
    success = generate_streamlink_playlist(
        output_path=args.output,
        groups=args.groups
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
