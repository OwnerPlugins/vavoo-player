/**
 * Vavoo URL Resolver - Cloudflare Worker
 * Risolve URL Vavoo on-the-fly e fa redirect 302
 * Deploy: wrangler deploy
 */

const AUTH_API = "https://www.lokke.app/api/app/ping";
const RESOLVE_API = "https://vavoo.to/mediahubmx-resolve.json";

let authSig = null;
let authTs = 0;

async function getSig() {
  if (authSig && (Date.now() - authTs < 540000)) {
    return authSig;
  }
  
  const data = {
    token: "ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-",
    reason: "app-blur",
    locale: "de",
    theme: "dark",
    metadata: {
      device: { type: "Handset", brand: "google", model: "Nexus", name: "21081111RG", uniqueId: "d10e5d99ab665233" },
      os: { name: "android", version: "7.1.2", abis: ["arm64-v8a"], host: "android" },
      app: { platform: "android", version: "1.1.0", buildId: "97215000", engine: "hbc85", signatures: ["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"], installer: "com.android.vending" },
      version: { package: "app.lokke.main", binary: "1.1.0", js: "1.1.0" },
      platform: { isAndroid: true, isIOS: false, isTV: false, isWeb: false, isMobile: true, isWebTV: false, isElectron: false }
    },
    appFocusTime: 0,
    playerActive: false,
    playDuration: 0,
    devMode: true,
    hasAddon: true,
    castConnected: false,
    package: "app.lokke.main",
    version: "1.1.0",
    process: "app",
    firstAppStart: 1772388338206,
    lastAppStart: 1772388338206,
    ipLocation: null,
    adblockEnabled: false,
    proxy: { supported: ["ss", "openvpn"], engine: "openvpn", ssVersion: 1, enabled: false, autoServer: true, id: "fi-hel" },
    iap: { supported: true }
  };

  const resp = await fetch(AUTH_API, {
    method: "POST",
    headers: {
      "user-agent": "okhttp/4.11.0",
      "accept": "application/json",
      "content-type": "application/json; charset=utf-8",
      "accept-encoding": "gzip"
    },
    body: JSON.stringify(data)
  });

  if (!resp.ok) throw new Error("Auth failed: " + resp.status);
  
  const json = await resp.json();
  authSig = json.addonSig;
  authTs = Date.now();
  return authSig;
}

async function resolveUrl(playUrl) {
  const sig = await getSig();
  
  const resp = await fetch(RESOLVE_API, {
    method: "POST",
    headers: {
      "user-agent": "MediaHubMX/2",
      "accept": "application/json",
      "content-type": "application/json; charset=utf-8",
      "content-length": "115",
      "accept-encoding": "gzip",
      "mediahubmx-signature": sig
    },
    body: JSON.stringify({
      language: "de",
      region: "AT",
      url: playUrl,
      clientVersion: "3.0.2"
    })
  });

  if (!resp.ok) throw new Error("Resolve failed: " + resp.status);
  
  const json = await resp.json();
  return json[0].url;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    if (url.pathname === "/resolve") {
      const playUrl = url.searchParams.get("url");
      if (!playUrl) {
        return new Response("Missing 'url' parameter", { status: 400 });
      }
      
      try {
        const streamUrl = await resolveUrl(decodeURIComponent(playUrl));
        return Response.redirect(streamUrl, 302);
      } catch (e) {
        return new Response("Error: " + e.message, { status: 500 });
      }
    }
    
    if (url.pathname === "/status") {
      return new Response(JSON.stringify({
        status: "running",
        authenticated: !!authSig,
        sigAge: authTs ? (Date.now() - authTs) / 1000 : null
      }), {
        headers: { "Content-Type": "application/json" }
      });
    }
    
    return new Response("Vavoo Resolver\n\nEndpoints:\n  /resolve?url=<play_url> - Resolve and redirect\n  /status - Check server status", {
      headers: { "Content-Type": "text/plain" }
    });
  }
};
