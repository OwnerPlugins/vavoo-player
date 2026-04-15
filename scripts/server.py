#!/usr/bin/env python3
"""
Vavoo Proxy Server for VLC
This server proxies Vavoo streams and adds the required authentication headers
that VLC cannot provide natively (but Kodi can through addons).
"""

import os
import sys
import time
import logging
import requests
import urllib3
from flask import Flask, Response, request, stream_with_context
from threading import Lock

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add parent dir to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.data_manager import DataManager

# --- CONSTANTS ---
USER_AGENT = "okhttp/4.11.0"
API_BASE = "https://www.vavoo.tv/api"
VAOO_URL = "https://vavoo.to/mediahubmx-catalog.json"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("vavoo_proxy.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Reusable session for connection pooling
_http_session = requests.Session()
_http_session.headers.update({"User-Agent": USER_AGENT})

# Authentication cache
_auth_cache = {
    "sig": None,
    "timestamp": 0
}
_auth_lock = Lock()


def get_auth_signature():
    """
    Get authentication signature from Vavoo API.
    Returns the signature string or None if failed.
    """
    with _auth_lock:
        # Check if cached signature is still valid (10 minutes)
        if _auth_cache["sig"] and (time.time() - _auth_cache["timestamp"] < 600):
            return _auth_cache["sig"]
        
        url = f"{API_BASE}/addon/sig"
        headers = {
            "user-agent": USER_AGENT,
            "accept": "application/json",
            "content-type": "application/json; charset=utf-8"
        }
        
        data = {
            "token": "tos",
            "reason": "app",
            "locale": "de",
            "theme": "dark",
            "metadata": {
                "device": {
                    "type": "Android",
                    "name": "Pixel 8 Pro",
                    "osVersion": "14",
                    "appVersion": "3.1.20",
                    "language": "de",
                    "userAgent": USER_AGENT,
                    "screenResolution": "1440x2960",
                    "supportedTypes": ["dash", "hls"]
                },
                "addonVersion": "3.1.20",
                "hasAddon": True,
                "castConnected": False,
                "package": "tv.vavoo.app",
                "version": "3.1.20",
                "process": "app",
                "firstAppStart": 1743962904623,
                "lastAppStart": 1743962904623,
                "ipLocation": "",
                "adblockEnabled": True,
                "proxy": {"supported": ["ss", "openvpn"], "engine": "ss", "ssVersion": 1, "enabled": True, "autoServer": True, "id": "pl-waw"},
                "iap": {"supported": False}
            }
        }
        
        try:
            logger.info("Requesting authentication signature...")
            response = _http_session.post(url, json=data, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            sig = response.json().get("addonSig")
            if sig:
                _auth_cache["sig"] = sig
                _auth_cache["timestamp"] = time.time()
                logger.info("Signature received successfully.")
                return sig
        except Exception as e:
            logger.error(f"Error getting auth signature: {e}")
        
        return None


def proxy_stream(url, headers=None):
    """
    Generator function to proxy stream content.
    
    Args:
        url: The actual stream URL from Vavoo
        headers: Additional headers to send with the request
    
    Yields:
        Chunks of stream data
    """
    try:
        # Prepare headers for the upstream request
        upstream_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive"
        }
        
        if headers:
            upstream_headers.update(headers)
        
        # Make request to upstream stream
        response = _http_session.get(
            url,
            headers=upstream_headers,
            stream=True,
            timeout=30,
            verify=False
        )
        response.raise_for_status()
        
        # Stream the content back
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                yield chunk
                
    except Exception as e:
        logger.error(f"Error proxying stream {url}: {e}")
        raise


@app.route('/stream/<channel_id>')
def stream_channel(channel_id):
    """
    Proxy endpoint for streaming channels.
    
    The channel_id is the base64-encoded original Vavoo URL.
    This endpoint adds the required authentication headers and proxies the stream.
    """
    import base64
    
    try:
        # Decode the original URL
        original_url = base64.b64decode(channel_id).decode('utf-8')
        logger.info(f"Stream request for: {original_url[:100]}...")
        
        # Get authentication signature
        sig = get_auth_signature()
        if not sig:
            return Response(
                "Failed to get authentication signature",
                status=503,
                content_type='text/plain'
            )
        
        # Prepare headers with signature
        headers = {
            "mediahubmx-signature": sig
        }
        
        # Determine content type based on URL
        content_type = 'video/mp2t'  # Default for MPEG-TS streams
        if '.m3u8' in original_url:
            content_type = 'application/vnd.apple.mpegurl'
        elif '.mpd' in original_url:
            content_type = 'application/dash+xml'
        
        # Return streaming response
        return Response(
            stream_with_context(proxy_stream(original_url, headers)),
            content_type=content_type,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream endpoint: {e}")
        return Response(
            f"Error: {str(e)}",
            status=500,
            content_type='text/plain'
        )


@app.route('/playlist.m3u8')
def serve_playlist():
    """
    Serve the generated playlist with proxy URLs.
    """
    try:
        playlist_path = os.path.join(os.path.dirname(__file__), 'playlist_proxy.m3u8')
        if os.path.exists(playlist_path):
            with open(playlist_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(
                content,
                content_type='application/vnd.apple.mpegurl',
                headers={
                    'Content-Disposition': 'attachment; filename="playlist.m3u8"'
                }
            )
        else:
            return Response(
                "Playlist not found. Run generate_proxy_playlist.py first.",
                status=404,
                content_type='text/plain'
            )
    except Exception as e:
        logger.error(f"Error serving playlist: {e}")
        return Response(
            f"Error: {str(e)}",
            status=500,
            content_type='text/plain'
        )


@app.route('/status')
def status():
    """Health check endpoint."""
    sig = get_auth_signature()
    return {
        "status": "running",
        "authenticated": sig is not None,
        "signature_age": time.time() - _auth_cache["timestamp"] if _auth_cache["timestamp"] > 0 else None
    }


@app.route('/')
def index():
    """Root endpoint with usage instructions."""
    return """
    <html>
    <head><title>Vavoo Proxy Server</title></head>
    <body>
        <h1>Vavoo Proxy Server for VLC</h1>
        <p>This server proxies Vavoo streams and adds required authentication headers.</p>
        
        <h2>Endpoints:</h2>
        <ul>
            <li><a href="/playlist.m3u8">/playlist.m3u8</a> - Download playlist with proxy URLs</li>
            <li><a href="/status">/status</a> - Server status</li>
            <li>/stream/<channel_id> - Stream proxy endpoint</li>
        </ul>
        
        <h2>Usage:</h2>
        <ol>
            <li>Run <code>python generate_proxy_playlist.py</code> to generate the playlist</li>
            <li>Start this server: <code>python server.py</code></li>
            <li>Open VLC and load: <code>http://localhost:5000/playlist.m3u8</code></li>
        </ol>
        
        <p>Or load the local file <code>playlist_proxy.m3u8</code> directly in VLC.</p>
    </body>
    </html>
    """


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Vavoo Proxy Server for VLC")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    logger.info(f"Starting Vavoo Proxy Server on {args.host}:{args.port}")
    logger.info("Press Ctrl+C to stop")
    
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
