#!/usr/bin/env python3
"""
Play Vavoo Streams with mpv Player
Uses the generated playlist file which already contains authenticated URLs.

Usage:
    python play_with_mpv.py --channel "RAI 1"
    python play_with_mpv.py --list
    python play_with_mpv.py  # Play from playlist file
"""

import os
import sys
import subprocess
import argparse
import logging
import re

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

# mpv path - can be customized
MPV_PATH = r"C:\Users\mdeangelis\Downloads\mpv-x86_64\mpv.exe"

# Playlist file path
PLAYLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "playlist.m3u8")


def check_mpv_installed():
    """Check if mpv is installed."""
    # First try the custom path
    if os.path.exists(MPV_PATH):
        logger.info(f"mpv found at: {MPV_PATH}")
        return True
    
    # Then try system PATH
    try:
        result = subprocess.run(
            ["mpv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"mpv found in PATH: {result.stdout.split(chr(10))[0]}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    logger.error("mpv not found!")
    logger.info(f"Expected at: {MPV_PATH}")
    logger.info("Or download from: https://mpv.io/installation/")
    return False


def get_mpv_command():
    """Get the mpv command (custom path or system)."""
    if os.path.exists(MPV_PATH):
        return MPV_PATH
    return "mpv"


def parse_playlist(playlist_path):
    """
    Parse M3U8 playlist and return list of channels with their URLs.
    
    Returns:
        List of dicts with 'name', 'url', 'group', 'tvg_id' keys
    """
    channels = []
    
    if not os.path.exists(playlist_path):
        logger.error(f"Playlist not found: {playlist_path}")
        logger.info("Generate it with: python generate_playlist.py")
        return channels
    
    with open(playlist_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for #EXTINF lines
        if line.startswith('#EXTINF:'):
            # Parse channel info
            match = re.search(r'tvg-id="([^"]*)"', line)
            tvg_id = match.group(1) if match else ""
            
            match = re.search(r'group-title="([^"]*)"', line)
            group = match.group(1) if match else ""
            
            # Get channel name (after the last comma)
            name = line.split(',')[-1].strip()
            
            # Next line should be the URL
            i += 1
            if i < len(lines):
                url = lines[i].strip()
                if url and not url.startswith('#'):
                    channels.append({
                        'name': name,
                        'url': url,
                        'group': group,
                        'tvg_id': tvg_id
                    })
        i += 1
    
    return channels


def list_channels(playlist_path=None):
    """List all available channels from playlist."""
    if playlist_path is None:
        playlist_path = PLAYLIST_PATH
    
    channels = parse_playlist(playlist_path)
    
    if not channels:
        logger.error("No channels found in playlist")
        return
    
    print(f"\n{'='*60}")
    print(f"Available Channels ({len(channels)} total)")
    print(f"{'='*60}\n")
    
    for i, ch in enumerate(channels, 1):
        print(f"{i:3d}. {ch['name']} [{ch['group']}]")
    
    print(f"\n{'='*60}")


def find_channel(channel_name, playlist_path=None):
    """
    Find a channel by name (partial match).
    
    Returns:
        Dict with channel info or None if not found
    """
    if playlist_path is None:
        playlist_path = PLAYLIST_PATH
    
    channels = parse_playlist(playlist_path)
    
    channel_name_upper = channel_name.upper()
    
    # Try exact match first
    for ch in channels:
        if ch['name'].upper() == channel_name_upper:
            return ch
    
    # Try partial match
    for ch in channels:
        if channel_name_upper in ch['name'].upper():
            return ch
    
    return None


def play_url(url, channel_name="Unknown"):
    """
    Play a URL using mpv.
    
    Args:
        url: The stream URL (already authenticated)
        channel_name: Name of the channel (for display)
    """
    mpv_cmd = get_mpv_command()
    cmd = [
        mpv_cmd,
        "--http-header-fields",
        "User-Agent: okhttp/4.11.0",
        "--cache=yes",
        "--demuxer-max-bytes=50MiB",
        "--demuxer-readahead-secs=30",
        url
    ]
    
    logger.info(f"Starting mpv...")
    logger.info(f"Channel: {channel_name}")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"mpv error: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Playback stopped by user")
        return True


def play_channel(channel_name, playlist_path=None):
    """
    Play a channel by name.
    
    Args:
        channel_name: Name of the channel to play
        playlist_path: Path to playlist file
    """
    ch = find_channel(channel_name, playlist_path)
    if not ch:
        logger.error(f"Channel not found: {channel_name}")
        logger.info("Use --list to see available channels")
        return False
    
    return play_url(ch['url'], ch['name'])


def play_playlist(playlist_path=None):
    """
    Play entire playlist with mpv.
    
    Args:
        playlist_path: Path to playlist file
    """
    if playlist_path is None:
        playlist_path = PLAYLIST_PATH
    
    if not os.path.exists(playlist_path):
        logger.error(f"Playlist not found: {playlist_path}")
        logger.info("Generate it with: python generate_playlist.py")
        return False
    
    mpv_cmd = get_mpv_command()
    cmd = [
        mpv_cmd,
        "--playlist",
        playlist_path,
        "--cache=yes",
        "--demuxer-max-bytes=50MiB",
        "--demuxer-readahead-secs=30"
    ]
    
    logger.info(f"Starting mpv with playlist...")
    logger.info(f"Playlist: {playlist_path}")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"mpv error: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Playback stopped by user")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Play Vavoo Streams with mpv (uses pre-generated playlist)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python play_with_mpv.py --channel "RAI 1"     # Play RAI 1
  python play_with_mpv.py --channel "CANALE 5"  # Play Canale 5
  python play_with_mpv.py --list                # List all channels
  python play_with_mpv.py                       # Play entire playlist
        """
    )
    
    parser.add_argument("--channel", "-c", help="Channel name to play (partial match)")
    parser.add_argument("--list", "-l", action="store_true", help="List available channels")
    parser.add_argument("--playlist", "-p", default=None, help="Path to playlist file")
    
    args = parser.parse_args()
    
    # Check mpv installation
    if not check_mpv_installed():
        sys.exit(1)
    
    # List channels mode
    if args.list:
        list_channels(args.playlist)
        sys.exit(0)
    
    # Play specific channel
    if args.channel:
        success = play_channel(args.channel, args.playlist)
        sys.exit(0 if success else 1)
    
    # Play entire playlist
    success = play_playlist(args.playlist)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
