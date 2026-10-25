"""
Ayna OTT V2 - FULL AUTO Live TV M3U8 Playlist Generator
------------------------------------------------------
✅ Auto-detect
✅ Cloudflare bypass (curl_cffi fallback)
✅ Auto group + speed sort (fast আগে)
✅ সুন্দর header + count + time
"""

import os
import sys
import time
import asyncio
import requests
import aiohttp
from datetime import datetime, timezone, timedelta

# ================= CONFIG =================
API_BASE = os.environ.get("AYNA_API_BASE", "").strip()
if not API_BASE:
    print("[!] AYNA_API_BASE secret not set. Aborting.")
    sys.exit(0)

SLUG        = os.environ.get("AYNA_SLUG", "ntv")
PER_PAGE    = 18
START_PAGE  = 1
END_PAGE    = 18
OUTPUT      = "Playlist/mrbotrx_ayna.m3u8"
TIMEOUT     = 15
CONCURRENCY = 25

AUTHOR      = "Mrbotrx"
TELEGRAM    = "https://t.me/iptvlinksm3u8"
PLAYLIST_ID = "Mrbotrx_ayna.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-A536E) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,bn;q=0.8",
    "Referer": "https://web.aynaott.com/",
    "Origin":  "https://web.aynaott.com",
}
if os.environ.get("AYNA_COOKIE"):
    HEADERS["Cookie"] = os.environ["AYNA_COOKIE"]
if os.environ.get("AYNA_TOKEN"):
    HEADERS["Authorization"] = f"Bearer {os.environ['AYNA_TOKEN']}"

PINNED_ENTRY = (
    '#EXTINF:-1 tvg-id="" tvg-name="1 IPTV LINKS" '
    'tvg-logo="https://raw.githubusercontent.com/Mrbotrx/Mrbotrx/refs/heads/main/IPTV_LINKS_LOGO.jpg" '
    'group-title="IPTV",IPTV LINKS\n'
    'https://github.com/Mrbotrx/Mrbotrx/raw/refs/heads/main/IPTV_LINKS_VIDEO.mp4\n'
)

# ================= HTTP layer (Cloudflare fallback) =================
try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
    print("[i] curl_cffi available — Cloudflare bypass active")
except Exception:
    cffi_requests = None
    USE_CFFI = False
    print("[i] curl_cffi not installed — using requests")

def http_get(url, params=None):
    """GET with automatic Cloudflare fallback"""
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code in (403, 503) and USE_CFFI:
            r = cffi_requests.get(url, params=params, headers=HEADERS,
                                  timeout=TIMEOUT, impersonate="chrome120")
        return r
    except Exception:
        if USE_CFFI:
            try:
                return cffi_requests.get(url, params=params, headers=HEADERS,
                                         timeout=TIMEOUT, impersonate="chrome120")
            except Exception:
                pass
    return None

# ================= AUTO GROUP =================
GROUP_RULES = [
    ("News", ["news", "somoy", "jamuna", "channel 24", "channel24", "dbc",
              "ekattor", "atn news", "independent", "r tv", "rtv",
              "bangla vision", "btv", "ntv", "gazi", "maasranga", "channel i",
              "desh", "samakal", "jugantor", "prothom", "abc", "cnn", "bbc",
              "aljazeera", "al jazeera", "sky news", "dw", "france 24"]),
    ("Sports", ["sports", "sport", "star sports", "sony ten", "sony sports",
                "espn", "tsports", "t sports", "eurosport", "willow", "cricket",
                "football", "ten sports", "bein", "supersport"]),
    ("Movies", ["movie", "cinema", "film", "hbo", "star movies", "sony pix",
                "zee cinema", "colors cineplex", "star gold", "max", "action",
                "thriller", "bollywood", "hollywood"]),
    ("Music", ["music", "mtv", "vh1", "9xm", "zoom", "b4u music", "trace",
               "stingray", "classic", "song", "gaan", "radio"]),
    ("Kids", ["kids", "cartoon", "disney", "nick", "pogo", "chhota bheem",
              "tom and jerry", "baby", "junior", "toon", "hungama"]),
    ("Religious", ["islam", "quran", "deen", "madani", "peace tv", "iqraa",
                   "hindu", "dharm", "sanatan", "krishna", "bhakti", "church",
                   "god", "spiritual", "aastha", "sanskar"]),
    ("Entertainment", ["entertainment", "star plus", "zee tv", "colors", "sony",
                       "star jalsha", "zee bangla", "sun", "vijay", "asianet",
                       "comedy", "serial", "drama", "reality"]),
    ("Lifestyle", ["food", "travel", "cooking", "fashion", "home", "garden",
                   "tlc", "discovery", "nat geo", "national geographic",
                   "animal planet"]),
]

def detect_group(name: str) -> str:
    n = name.lower()
    for group, keys in GROUP_RULES:
        for k in keys:
            if k in n:
                return group
    return "General"

# ================= RECURSIVE .m3u8 FINDER =================
STREAM_KEYS = (
    "stream_url", "m3u8", "play_url", "playback_url", "hls",
    "hls_url", "video_url", "src", "link", "file", "manifest",
    "stream", "url",
)

def find_m3u8(obj, depth=0):
    """যেকোনো depth-এ .m3u8 URL খুঁজে বের করে"""
    if depth > 8:
        return None
    if isinstance(obj, str):
        return obj if ".m3u8" in obj else None
    if isinstance(obj, dict):
        for k in STREAM_KEYS:
            if k in obj:
                r = find_m3u8(obj[k], depth + 1)
                if r:
                    return r
        for v in obj.values():
            r = find_m3u8(v, depth + 1)
            if r:
                return r
    if isinstance(obj, list):
        for v in obj:
            r = find_m3u8(v, depth + 1)
            if r:
                return r
    return None

def find_logo(obj):
    if isinstance(obj, dict):
        for k in ("logo", "thumbnail", "poster", "image", "icon", "cover"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict):
                for kk in ("url", "src", "original", "large", "medium"):
                    if isinstance(v.get(kk), str) and v[kk]:
                        return v[kk]
    return ""

# ================= FETCH =================
def fetch_page(page: int):
    url = f"{API_BASE}/browse/live-tvs/{SLUG}/related"
    params = {"per_page": PER_PAGE, "sort": "similarity", "page": page}
    r = http_get(url, params=params)
    if not r:
        print(f"[!] page={page} network fail")
        return None
    print(f"[i] page={page} status={r.status_code} size={len(r.content)}")
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception as e:
        print(f"[!] page={page} json parse fail: {e}")
        return None

# ================= 2-STEP RESOLVE =================
def resolve_stream_from_id(item_id):
    """item id থেকে playback endpoint চেষ্টা করে .m3u8 খুঁজে বের করে"""
    endpoints = [
        f"{API_BASE}/live-tvs/{item_id}/play",
        f"{API_BASE}/live-tv/{item_id}/play",
        f"{API_BASE}/browse/live-tvs/{item_id}",
        f"{API_BASE}/live-tvs/{item_id}",
        f"{API_BASE}/contents/{item_id}/play",
    ]
    for ep in endpoints:
        r = http_get(ep)
        if not r or r.status_code != 200:
            continue
        try:
            data = r.json()
        except Exception:
            continue
        url = find_m3u8(data)
        if url:
            print(f"[+] resolved via {ep}")
            return url
    return None

# ================= PARSE (AUTO) =================
LIST_KEYS = ("data", "items", "results", "contents", "channels",
             "related", "list", "records", "rows")

def extract_list(data):
    """যেকোনো structure থেকে list of dict বের করে"""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []

    # direct key
    for k in LIST_KEYS:
        v = data.get(k)
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v

    # nested dict
    for k in LIST_KEYS:
        v = data.get(k)
        if isinstance(v, dict):
            for k2 in LIST_KEYS:
                v2 = v.get(k2)
                if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                    return v2

    # যেকোনো প্রথম list of dict
    for v in data.values():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            return v
        if isinstance(v, dict):
            for v2 in v.values():
                if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                    return v2
    return []

def parse_api_response(data):
    """সম্পূর্ণ auto — যেকোনো JSON থেকে চ্যানেল বের করে"""
    items = extract_list(data)
    if not items:
        print("[!] No list found in response")
        return []

    out = []
    resolved_count = 0

    for it in items:
        if not isinstance(it, dict):
            continue

        name = (it.get("title") or it.get("name")
                or it.get("channel_name") or it.get("slug")
                or it.get("label"))
        if not name:
            continue

        logo = find_logo(it)

        # 1st attempt: recursive m3u8
        stream = find_m3u8(it)

        # 2nd attempt: resolve by id
        if not stream:
            item_id = (it.get("id") or it.get("content_id")
                       or it.get("video_id") or it.get("channel_id"))
            if item_id and resolved_count < 100:
                stream = resolve_stream_from_id(item_id)
                if stream:
                    resolved_count += 1

        if not stream:
            continue

        out.append({
            "name": str(name).strip(),
            "logo": logo or "",
            "url": stream,
        })

    print(f"[i] Parsed {len(out)} channels (resolved by id: {resolved_count})")
    return out

# ================= VALIDATE + SPEED =================
async def check_stream(session, url):
    try:
        t0 = time.perf_counter()
        async with session.head(url, timeout=TIMEOUT, allow_redirects=True) as r:
            dt = int((time.perf_counter() - t0) * 1000)
            if r.status in (200, 206, 301, 302, 403):
                return True, dt
    except Exception:
        pass

    try:
        t0 = time.perf_counter()
        async with session.get(url, timeout=TIMEOUT) as r:
            if r.status in (200, 206):
                chunk = await r.content.read(1024)
                dt = int((time.perf_counter() - t0) * 1000)
                if b"#EXTM3U" in chunk or len(chunk) > 0:
                    return True, dt
    except Exception:
        return False, 0
    return False, 0

async def validate_all(channels):
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        async def run(ch):
            async with sem:
                alive, ms = await check_stream(session, ch["url"])
                if alive:
                    ch["speed_ms"] = ms
                    ch["group"] = detect_group(ch["name"])
                    print(f"[✓] {ch['name']} ({ms}ms) [{ch['group']}]")
                    return ch
                print(f"[✗] {ch['name']}")
                return None

        out = await asyncio.gather(*(run(c) for c in channels))
    return [r for r in out if r]

# ================= HEADER BUILDER =================
def build_header(channel_count: int) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bd = (datetime.now(timezone.utc) + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M BST")
    lines = [
        "#EXTM3U",
        "# ═══════════════════════════════════════",
        "#       ★ MRBOTRX AYNA PLAYLIST ★",
        "# ═══════════════════════════════════════",
        f"# 📺 Playlist : {PLAYLIST_ID}",
        f"# 👤 Author   : {AUTHOR}",
        f"# 📡 Telegram : {TELEGRAM}",
        f"# 🔢 Channels : {channel_count}",
        f"# 🕒 Updated  : {now_utc}  |  {bd}",
        "# ═══════════════════════════════════════",
        "",
    ]
    return "\n".join(lines) + "\n"

# ================= WRITE =================
def write_playlist(channels):
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    channels.sort(key=lambda c: (c.get("speed_ms", 999999),
                                 c.get("group", ""), c["name"]))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(build_header(len(channels)))
        f.write(PINNED_ENTRY)
        f.write("\n")
        for ch in channels:
            name = ch["name"].replace(",", " ").replace('"', "")
            logo = ch["logo"]
            group = ch.get("group", "General")
            f.write(
                f'#EXTINF:-1 tvg-id="" tvg-name="{name}" '
                f'tvg-logo="{logo}" group-title="{group}",{name}\n'
                f'{ch["url"]}\n'
            )
    print(f"[✓] Saved {len(channels)} channels → {OUTPUT}")
    from collections import Counter
    for g, cnt in Counter(c["group"] for c in channels).most_common():
        print(f"    • {g}: {cnt}")

# ================= MAIN =================
def main():
    all_channels = {}
    for page in range(START_PAGE, END_PAGE + 1):
        data = fetch_page(page)
        if not data:
            continue
        items = parse_api_response(data)
        if not items:
            print(f"[!] page={page} no channel, stop")
            break
        for ch in items:
            all_channels.setdefault(ch["name"].lower(), ch)
        print(f"[i] page={page} → total unique={len(all_channels)}")

    print(f"[i] Total unique (raw): {len(all_channels)}")
    if not all_channels:
        write_playlist([])
        return

    valid = asyncio.run(validate_all(list(all_channels.values())))
    print(f"[i] Working channels: {len(valid)}")
    write_playlist(valid)

if __name__ == "__main__":
    main()
