-- vavoo-resolve.lua: Risolve URL Vavoo on-the-fly in mpv
-- Installa in: %APPDATA%\mpv\scripts\vavoo-resolve.lua

local utils = require 'mp.utils'
local msg = require 'mp.msg'

local AUTH_API = "https://www.lokke.app/api/app/ping"
local RESOLVE_API = "https://vavoo.to/mediahubmx-resolve.json"

local auth_sig = nil
local auth_ts = 0

function get_auth_signature()
    local now = mp.get_time()
    if auth_sig and (now - auth_ts < 540) then
        return auth_sig
    end

    local data = '{"token":"ldCvE092e7gER0rVIajfsXIvRhwlrAzP6_1oEJ4q6HH89QHt24v6NNL_jQJO219hiLOXF2hqEfsUuEWitEIGN4EaHHEHb7Cd7gojc5SQYRFzU3XWo_kMeryAUbcwWnQrnf0-","reason":"app-blur","locale":"de","theme":"dark","metadata":{"device":{"type":"Handset","brand":"google","model":"Nexus","name":"21081111RG","uniqueId":"d10e5d99ab665233"},"os":{"name":"android","version":"7.1.2","abis":["arm64-v8a"],"host":"android"},"app":{"platform":"android","version":"1.1.0","buildId":"97215000","engine":"hbc85","signatures":["6e8a975e3cbf07d5de823a760d4c2547f86c1403105020adee5de67ac510999e"],"installer":"com.android.vending"},"version":{"package":"app.lokke.main","binary":"1.1.0","js":"1.1.0"},"platform":{"isAndroid":true,"isIOS":false,"isTV":false,"isWeb":false,"isMobile":true,"isWebTV":false,"isElectron":false}},"appFocusTime":0,"playerActive":false,"playDuration":0,"devMode":true,"hasAddon":true,"castConnected":false,"package":"app.lokke.main","version":"1.1.0","process":"app","firstAppStart":1772388338206,"lastAppStart":1772388338206,"ipLocation":null,"adblockEnabled":false,"proxy":{"supported":["ss","openvpn"],"engine":"openvpn","ssVersion":1,"enabled":false,"autoServer":true,"id":"fi-hel"},"iap":{"supported":true}}'

    local args = {
        'curl', '-s', '-X', 'POST',
        '-H', 'user-agent: okhttp/4.11.0',
        '-H', 'accept: application/json',
        '-H', 'content-type: application/json; charset=utf-8',
        '-H', 'accept-encoding: gzip',
        '-d', data,
        AUTH_API
    }

    local result = utils.subprocess({args = args, cancellable = false, timeout = 10})
    if result.status == 0 and result.stdout then
        local json = utils.parse_json(result.stdout)
        if json and json.addonSig then
            auth_sig = json.addonSig
            auth_ts = now
            msg.info("Auth signature obtained")
            return auth_sig
        end
    end
    msg.error("Failed to get auth signature")
    return nil
end

function resolve_url(play_url)
    local sig = get_auth_signature()
    if not sig then return nil end

    local body = '{"language":"de","region":"AT","url":"' .. play_url .. '","clientVersion":"3.0.2"}'

    local args = {
        'curl', '-s', '-X', 'POST',
        '-H', 'user-agent: MediaHubMX/2',
        '-H', 'accept: application/json',
        '-H', 'content-type: application/json; charset=utf-8',
        '-H', 'accept-encoding: gzip',
        '-H', 'mediahubmx-signature: ' .. sig,
        '-d', body,
        RESOLVE_API
    }

    local result = utils.subprocess({args = args, cancellable = false, timeout = 10})
    if result.status == 0 and result.stdout then
        local json = utils.parse_json(result.stdout)
        if json and json[1] and json[1].url then
            msg.info("Resolved: " .. json[1].url:sub(1, 80) .. "...")
            return json[1].url
        end
    end
    msg.error("Failed to resolve URL")
    return nil
end

function on_file_loaded()
    local path = mp.get_property("path")
    if not path then return end

    if path:match("vavoo%.to/vavoo%-iptv/play/") then
        msg.info("Resolving Vavoo URL: " .. path)
        local resolved = resolve_url(path)
        if resolved then
            mp.set_property("stream-open-filename", resolved)
            mp.set_property("http-header-fields", "User-Agent: okhttp/4.11.0")
        else
            msg.error("Could not resolve Vavoo URL")
        end
    end
end

mp.register_event("file-loaded", on_file_loaded)
