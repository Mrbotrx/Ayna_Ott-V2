"""
Ayna OTT V2 - Live TV M3U8 Playlist Generator
✅ যেকোনো JSON key থেকে list খুঁজে বের করে
✅ stream.url, images.poster_url, title, taxonomies.category
✅ শুধু working .m3u8
✅ Auto group + speed sort (fast আগে)
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
IMG_BASE    = "https://web.aynaott.com"

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

PINNED_ENTRY = (
    '#EXTINF:-1 tvg-id="" tvg-name="1 IPTV LINKS" '
    'tvg-logo="https://raw.githubusercontent.com/Mrbotrx/Mrbotrx/refs/heads/main/IPTV_LINKS_LOGO.jpg" '
    'group-title="IPTV",IPTV LINKS\n'
    'https://github.com/Mrbotrx/Mrbotrx/raw/refs/heads/main/IPTV_LINKS_VIDEO.mp4\n'
)

# ================= HTTP =================
try:
    from curl_cffi import requests as cffi_requests
    USE_CFFI = True
    print("[i] curl_cffi available")
except Exception:
    cffi_requests = None
    USE_CFFI = False
    print("[i] curl_cffi not installed")

def http_get(url, params=None):
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

def detect_group(name):
    n = name.lower()
    for group, keys in GROUP_RULES:
        for k in keys:
            if k in n:
                return group
    return "General"

# ================= UNIVERSAL LIST FINDER =================
def find_items(data, depth=0):
    """
    যেকোনো JSON structure থেকে list-of-dict বের করে।
    depth limit 6, infinite recursion নিরাপদ।
    """
    if depth > 6:
        return []

    # data নিজেই list
    if isinstance(data, list):
        dicts = [x for x in data if isinstance(x, dict)]
        if dicts:
            return dicts
        return []

    if isinstance(data, dict):
        # Priority keys
        for k in ("data", "items", "results", "related", "streams",
                  "contents", "channels", "list", "records", "rows",
                  "videos", "live_tvs", "live-tvs"):
            v = data.get(k)
            if isinstance(v, list):
                dicts = [x for x in v if isinstance(x, dict)]
                if dicts:
                    return dicts
            if isinstance(v, dict):
                r = find_items(v, depth + 1)
                if r:
                    return r

        # Fallback: সব values scan
        for v in data.values():
            r = find_items(v, depth + 1)
            if r:
                return r

    return []

# ================= PARSE =================
def fix_logo(url):
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return IMG_BASE + url

def parse_api_response(data):
    items = find_items(data)
    print(f"[i] find_items → {len(items)} items")
    if not items:
        # DEBUG: top-level keys দেখাও
        if isinstance(data, dict):
            print(f"[DEBUG] top keys = {list(data.keys())}")
            print(f"[DEBUG] sample   = {str(data)[:400]}")
        return []

    out = []
    for it in items:
        if not isinstance(it, dict):
            continue

        # নাম
        name = it.get("title") or it.get("name") or it.get("slug")
        if not name:
            continue

        # লোগো
        logo = ""
        images = it.get("images") or {}
        if isinstance(images, dict):
            logo = (images.get("poster_url") or images.get("thumbnail_url")
                    or images.get("poster_wide_url")
                    or images.get("thumbnail_wide_url") or "")
        logo = fix_logo(logo)

        # স্ট্রিম (.m3u8)
        stream = ""
        st = it.get("stream") or {}
        if isinstance(st, dict):
            stream = st.get("url") or ""
            if not stream and isinstance(st.get("urls"), list) and st["urls"]:
                first = st["urls"][0]
                if isinstance(first, dict):
                    stream = first.get("url", "")
                elif isinstance(first, str):
                    stream = first

        if not stream or ".m3u8" not in stream:
            continue

        # গ্রুপ
        group = None
        tax = it.get("taxonomies") or {}
        if isinstance(tax, dict):
            cats = tax.get("category") or []
            if isinstance(cats, list):
                for c in cats:
                    if isinstance(c, dict):
                        t = (c.get("title") or "").strip()
                        if t and t.lower() not in ("channels", "channel-channels"):
                            group = t
                            break
        if not group:
            group = detect_group(name)

        out.append({
            "name": str(name).strip(),
            "logo": logo,
            "url": stream,
            "group": group,
        })

    print(f"[i] Parsed {len(out)} channels from page")
    return out

# ================= FETCH =================
def fetch_page(page):
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
                    print(f"[✓] {ch['name']} ({ms}ms) [{ch.get('group','?')}]")
                    return ch
                print(f"[✗] {ch['name']}")
                return None
        out = await asyncio.gather(*(run(c) for c in channels))
    return [r for r in out if r]

# ================= HEADER =================
def build_header(count):
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
        f"# 🔢 Channels : {count}",
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
            f.write(
                f'#EXTINF:-1 tvg-id="" tvg-name="{name}" '
                f'tvg-logo="{ch["logo"]}" group-title="{ch.get("group","General")}",{name}\n'
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
