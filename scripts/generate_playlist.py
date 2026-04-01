import os
import sys
import logging
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.playlist_generator import PlaylistGenerator

def main():
    parser = argparse.ArgumentParser(description="Generate Vavoo IPTV Playlist")
    parser.add_argument("--output", default="playlist.m3u8", help="Output path for the playlist")
    parser.add_argument("--epg-output", default=None, help="Output path for merged EPG (e.g. epg.xml)")
    parser.add_argument("--groups", nargs="+", default=None, help="Groups to include (default: from config.json)")
    parser.add_argument("--config", default=None, help="Path to config.json (default: src/config.json)")
    parser.add_argument("--catchup", action="store_true", help="Enable catchup/timeshift support in output")
    parser.add_argument("--catchup-days", type=int, default=7, help="Number of catchup days (default: 7)")
    parser.add_argument("--stats", action="store_true", help="Print detailed statistics after generation")
    
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

    success = True

    logging.info(f"Starting playlist generation for groups: {args.groups or 'default'}")
    gen = PlaylistGenerator(config_path=args.config)
    
    if args.catchup:
        gen._catchup_cfg["enabled"] = True
        gen._catchup_cfg["days"] = args.catchup_days
    
    if not gen.generate_m3u8(args.output, groups=args.groups):
        logging.error("Failed to generate playlist.")
        success = False

    if args.epg_output:
        logging.info(f"Starting EPG merge...")
        from src.epg_merger import merge_epg
        if not merge_epg(args.epg_output):
            logging.error("Failed to merge EPG.")
            success = False

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
