#!/usr/bin/env python3
"""
Generate Vavoo Playlist with Proxy URLs for VLC
This script generates a playlist that uses proxy URLs instead of direct Vavoo URLs.
The proxy server (server.py) adds the required authentication headers that VLC cannot provide.

Supports both local and remote (GitHub/Render) proxy deployment.
"""

import os
import sys
import base64
import logging
import argparse

# Add the root directory to sys.path to allow imports from src
sys.path.append(os.path.join(os.path.dirname(__file__)))

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

# Default remote proxy URL (update this after deploying to Render)
DEFAULT_REMOTE_PROXY = "https://vavoo-proxy.onrender.com"


def encode_url_for_proxy(url):
    """
    Encode a URL to be used as a channel_id in the proxy endpoint.
    
    Args:
        url: The original Vavoo stream URL
    
    Returns:
        Base64-encoded URL safe for use in path
    """
    return base64.urlsafe_b64encode(url.encode('utf-8')).decode('utf-8')


def generate_proxy_playlist(output_path="playlist_proxy.m3u8", groups=None, proxy_url=None):
    """
    Generate a playlist with proxy URLs instead of direct Vavoo URLs.
    
    Args:
        output_path: Path to save the playlist
        groups: List of groups to include
        proxy_url: Full URL of the proxy server (e.g., http://localhost:5000 or https://vavoo-proxy.onrender.com)
    
    Returns:
        True if successful, False otherwise
    """
    if groups is None:
        groups = ["Italy"]
    
    if proxy_url is None:
        proxy_url = DEFAULT_REMOTE_PROXY
    
    # Remove trailing slash
    proxy_url = proxy_url.rstrip('/')
    
    logger.info(f"Generating proxy playlist for groups: {groups}")
    logger.info(f"Proxy server: {proxy_url}")
    
    # Create a PlaylistGenerator instance
    gen = PlaylistGenerator()
    
    # Fetch all channels
    channels = gen.fetch_all_channels(target_groups=groups)
    if not channels:
        logger.error("No channels fetched.")
        return False
    
    logger.info(f"Fetched {len(channels)} channels")
    
    # Process channels (normalize names, get logos, etc.)
    processed_channels = gen.process_channels(channels)
    if not processed_channels:
        logger.error("No valid channels to write.")
        return False
    
    logger.info(f"Processed {len(processed_channels)} channels")
    
    try:
        logger.info(f"Writing {len(processed_channels)} channels to {output_path}...")
        with open(output_path, "w", encoding="utf-8") as f:
            # Write M3U header
            epg_url = "https://raw.githubusercontent.com/mich-de/vavoo-player/master/epg.xml"
            f.write(f'#EXTM3U x-tvg-url="{epg_url}"\n')
            
            for ch in processed_channels:
                # Encode the original URL for the proxy
                encoded_url = encode_url_for_proxy(ch.url)
                
                # Build the proxy URL
                stream_url = f"{proxy_url}/stream/{encoded_url}"
                
                # Write VLC options for better compatibility
                f.write(f'#EXTVLCOPT:http-user-agent=okhttp/4.11.0\n')
                f.write(f'#EXTVLCOPT:http-reconnect=true\n')
                f.write(f'#EXTVLCOPT:network-caching=3000\n')
                
                # Write channel info
                header = f'#EXTINF:-1 tvg-id="{ch.tvg_id}" tvg-name="{ch.clean_name}" tvg-logo="{ch.logo_override or ch.logo}" channel="{ch.tvg_id}" group-title="{ch.group}",{ch.clean_name}'
                f.write(f"{header}\n")
                f.write(f"{stream_url}\n")
                
        logger.info(f"Proxy playlist generated successfully: {output_path}")
        if "localhost" in proxy_url or "127.0.0.1" in proxy_url:
            logger.info(f"Start the local proxy server with: python server.py")
        else:
            logger.info(f"Using remote proxy: {proxy_url}")
        logger.info(f"Open VLC and load: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing playlist: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate Vavoo Playlist with Proxy URLs for VLC")
    parser.add_argument("--output", default="playlist_proxy.m3u8", help="Output path for the playlist (default: playlist_proxy.m3u8)")
    parser.add_argument("--groups", nargs="+", default=["Italy"], help="Groups to include (default: Italy)")
    parser.add_argument("--proxy-url", default=None, help=f"Proxy server URL (default: {DEFAULT_REMOTE_PROXY})")
    parser.add_argument("--local", action="store_true", help="Use local proxy (http://localhost:5000)")
    
    args = parser.parse_args()
    
    # Determine proxy URL
    proxy_url = args.proxy_url
    if args.local:
        proxy_url = "http://localhost:5000"
    
    success = generate_proxy_playlist(
        output_path=args.output,
        groups=args.groups,
        proxy_url=proxy_url
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
