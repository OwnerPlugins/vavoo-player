#!/usr/bin/env python3
"""
Play Vavoo Streams with Streamlink + VLC
This script makes it easy to play Vavoo streams using Streamlink,
which supports custom HTTP headers that VLC cannot provide.

Usage:
    python play_with_streamlink.py                    # Play from playlist
    python play_with_streamlink.py --channel "RAI 1"  # Play specific channel
    python play_with_streamlink.py --list             # List available channels
"""

import os
import sys
import subprocess
import argparse
import logging

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


def check_streamlink_installed():
    """Check if Streamlink is installed."""
    try:
        result = subprocess.run(
            ["python", "-m", "streamlink", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"Streamlink found: {result.stdout.strip()}")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    logger.error("Streamlink not found!")
    logger.info("Install it with: pip install streamlink")
    return False


def get_channel_url(channel_name, groups=None):
    """
    Get the stream URL for a specific channel.
    
    Args:
        channel_name: Name of the channel to find
        groups: List of groups to search in
    
    Returns:
        Tuple of (url, channel_info) or (None, None) if not found
    """
    if groups is None:
        groups = ["Italy"]
    
    gen = PlaylistGenerator()
    channels = gen.fetch_all_channels(target_groups=groups)
    
    if not channels:
        logger.error("No channels fetched")
        return None, None
    
    # Search for channel (case-insensitive partial match)
    channel_name_upper = channel_name.upper()
    for ch in channels:
        if channel_name_upper in ch['name'].upper():
            return ch['url'], ch
    
    # Try exact match
    for ch in channels:
        if ch['name'].upper() == channel_name_upper:
            return ch['url'], ch
    
    return None, None


def list_channels(groups=None):
    """List all available channels."""
    if groups is None:
        groups = ["Italy"]
    
    logger.info(f"Fetching channels for groups: {groups}")
    gen = PlaylistGenerator()
    channels = gen.fetch_all_channels(target_groups=groups)
    
    if not channels:
        logger.error("No channels found")
        return
    
    print(f"\n{'='*60}")
    print(f"Available Channels ({len(channels)} total)")
    print(f"{'='*60}\n")
    
    for i, ch in enumerate(channels, 1):
        print(f"{i:3d}. {ch['name']}")
    
    print(f"\n{'='*60}")


def play_stream(url, player="vlc"):
    """
    Play a stream URL using Streamlink.
    
    Args:
        url: The stream URL
        player: Player to use (vlc, mpv, etc.)
    """
    # Get fresh signature using PlaylistGenerator
    gen = PlaylistGenerator()
    logger.info("Fetching authentication signature...")
    sig = gen.get_signature()
    if not sig:
        logger.error("Failed to get authentication signature")
        return False
    
    logger.info(f"Signature obtained: {sig[:30]}...")
    
    # Build Streamlink command
    cmd = [
        "python", "-m", "streamlink",
        "--player", player,
        "--http-header", f"mediahubmx-signature={sig}",
        "--http-header", "User-Agent=okhttp/4.11.0",
        "--player-args", "--network-caching=3000",
        url,
        "best"
    ]
    
    logger.info(f"Starting Streamlink with {player}...")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        # Run Streamlink
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlink error: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Playback stopped by user")
        return True


def play_from_playlist(playlist_path="playlist_streamlink.m3u8", player="vlc"):
    """
    Play streams from a playlist file using Streamlink.
    
    Args:
        playlist_path: Path to the M3U8 playlist
        player: Player to use
    """
    if not os.path.exists(playlist_path):
        logger.error(f"Playlist not found: {playlist_path}")
        logger.info(f"Generate it with: python generate_streamlink_playlist.py")
        return False
    
    # Get fresh signature using PlaylistGenerator
    gen = PlaylistGenerator()
    logger.info("Fetching authentication signature...")
    sig = gen.get_signature()
    if not sig:
        logger.error("Failed to get authentication signature")
        return False
    
    # Build Streamlink command for playlist
    cmd = [
        "python", "-m", "streamlink",
        "--player", player,
        "--http-header", f"mediahubmx-signature={sig}",
        "--http-header", "User-Agent=okhttp/4.11.0",
        playlist_path
    ]
    
    logger.info(f"Starting Streamlink with playlist...")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Streamlink error: {e}")
        return False
    except KeyboardInterrupt:
        logger.info("Playback stopped by user")
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Play Vavoo Streams with Streamlink + VLC (no proxy needed!)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python play_with_streamlink.py                    # Play from playlist
  python play_with_streamlink.py --channel "RAI 1"  # Play specific channel
  python play_with_streamlink.py --list             # List channels
  python play_with_streamlink.py --player mpv       # Use mpv instead of VLC
        """
    )
    
    parser.add_argument("--channel", "-c", help="Channel name to play (partial match)")
    parser.add_argument("--playlist", "-p", default="playlist_streamlink.m3u8", help="Playlist file path")
    parser.add_argument("--player", default="vlc", help="Player to use (vlc, mpv, etc.)")
    parser.add_argument("--list", "-l", action="store_true", help="List available channels")
    parser.add_argument("--groups", nargs="+", default=["Italy"], help="Groups to include")
    
    args = parser.parse_args()
    
    # Check Streamlink installation
    if not check_streamlink_installed():
        sys.exit(1)
    
    # List channels mode
    if args.list:
        list_channels(args.groups)
        sys.exit(0)
    
    # Play specific channel
    if args.channel:
        url, ch_info = get_channel_url(args.channel, args.groups)
        if url:
            logger.info(f"Found channel: {ch_info['name']}")
            success = play_stream(url, args.player)
            sys.exit(0 if success else 1)
        else:
            logger.error(f"Channel not found: {args.channel}")
            logger.info("Use --list to see available channels")
            sys.exit(1)
    
    # Play from playlist
    success = play_from_playlist(args.playlist, args.player)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
