"""
Ayna OTT V2 - Live TV M3U8 Playlist Generator
--------------------------------------------
✅ Auto group (News/Sports/Movie/Music/Kids/Religious/Entertainment)
✅ Speed অনুযায়ী সর্ট — fast আগে, slow পরে
✅ সুন্দর Header + Auto count + Auto time
"""

import os
import sys
import time
import asyncio
from datetime import datetime, timezone
import requests
import aiohttp

# ✅ API লিংক শুধু Secret থেকে
API_BASE = os.environ.get("AYNA_API_BASE", "").strip()
if not API_BASE:
    print("[!] AYNA_API_BASE secret not set. Aborting.")
    sys.exit(0)

SLUG        = "ntv"
PER_PAGE    = 18
START_PAGE  = 1
END_PAGE    = 18
OUTPUT      = "Playlist/mrbotrx_ayna.m3u8"
TIMEOUT     = 12
CONCURRENCY = 25

# ================= HEADER INFO =================
AUTHOR      = "Mrbotrx"
TELEGRAM    = "https://t.me/iptvlinksm3u8"
PLAYLIST_ID = "Mrbotrx_ayna.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

PINNED_ENTRY = (
    '#EXTINF:-1 tvg-id="" tvg-name="1 IPTV LINKS" '
    'tvg-logo="https://raw.githubusercontent.com/Mrbotrx/Mrbotrx/refs/heads/main/IPTV_LINKS_LOGO.jpg" '
    'group-title="IPTV",IPTV LINKS\n'
    'https://github.com/Mrbotrx/Mrbotrx/raw/refs/heads/main/IPTV_LINKS_VIDEO.mp4\n'
)

# ================= AUTO GROUP =================
GROUP_RULES = [
    ("News", [
        "news", "somoy", "jamuna", "channel 24", "channel24", "dbc",
        "ekattor", "atn news", "independent", "r tv", "rtv",
        "bangla vision", "btv", "ntv", "gazi", "maasranga", "channel i",
        "desh", "samakal", "jugantor", "prothom", "abc", "cnn", "bbc",
        "aljazeera", "al jazeera", "sky news", "dw", "france 24",
    ]),
    ("Sports", [
        "sports", "sport", "star sports", "sony ten", "sony sports",
        "espn", "tsports", "t sports", "eurosport", "willow", "cricket",
        "football", "ten sports", "bein", "supersport",
    ]),
    ("Movies", [
        "movie", "cinema", "film", "hbo", "star movies", "sony pix",
        "zee cinema", "colors cineplex", "star gold", "max", "action",
        "thriller", "bollywood", "hollywood",
    ]),
    ("Music", [
        "music", "mtv", "vh1", "9xm", "zoom", "b4u music", "trace",
        "stingray", "classic", "song", "gaan", "radio",
    ]),
    ("Kids", [
        "kids", "cartoon", "disney", "nick", "pogo", "chhota bheem",
        "tom and jerry", "baby", "junior", "toon", "hungama",
    ]),
    ("Religious", [
        "islam", "quran", "deen", "madani", "peace tv", "iqraa",
        "hindu", "dharm", "sanatan", "krishna", "bhakti", "church",
        "god", "spiritual", "aastha", "sanskar",
    ]),
    ("Entertainment", [
        "entertainment", "star plus", "zee tv", "colors", "sony",
        "star jalsha", "zee bangla", "sun", "vijay", "asianet",
        "comedy", "serial", "drama", "reality",
    ]),
    ("Lifestyle", [
        "food", "travel", "cooking", "fashion", "home", "garden",
        "tlc", "discovery", "nat geo", "national geographic", "animal planet",
    ]),
]

def detect_group(name: str) -> str:
    n = name.lower()
    for group, keys in GROUP_RULES:
        for k in keys:
            if k.lower() in n:
                return group
    return "General"

# ================= FETCH =================
def fetch_page(page: int):
    url = f"{API_BASE}/browse/live-tvs/{SLUG}/related"
    params = {"per_page": PER_PAGE, "sort": "similarity", "page": page}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        print(f"[i] page={page} status={r.status_code} size={len(r.content)}")
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        print(f"[!] page={page} failed: {e}")
        return None

# ================= PARSE =================
def parse_api_response(data):
    if not isinstance(data, dict):
        return []
    items = data.get("data") or data.get("items") or data.get("results") or []
    if isinstance(items, dict):
        items = items.get("items") or items.get("data") or []

    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("title") or it.get("name") or it.get("channel_name") or it.get("slug")
        if not name:
            continue
        logo = it.get("logo") or it.get("thumbnail") or it.get("image") or it.get("poster") or ""
        stream = it.get("stream_url") or it.get("m3u8") or it.get("play_url") or it.get("url") or ""

        if not stream:
            for s in (it.get("sources") or []):
                if isinstance(s, dict) and str(s.get("url", "")).endswith(".m3u8"):
                    stream = s["url"]; break

        if not stream and isinstance(it.get("content"), dict):
            c = it["content"]
            stream = c.get("stream_url") or c.get("m3u8") or c.get("url") or ""

        if not stream or ".m3u8" not in str(stream):
            continue

        out.append({
            "name": str(name).strip(),
            "logo": logo or "",
            "url": stream,
        })
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
    results = []

    async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
        async def run(ch):
            async with sem:
                alive, ms = await check_stream(session, ch["url"])
                if alive:
                    ch["speed_ms"] = ms
                    ch["group"] = detect_group(ch["name"])
                    print(f"[✓] {ch['name']}  ({ms} ms)  [{ch['group']}]")
                    return ch
                else:
                    print(f"[✗] {ch['name']}")
                    return None

        out = await asyncio.gather(*(run(c) for c in channels))
        results = [r for r in out if r]

    return results

# ================= HEADER BUILDER =================
def build_header(channel_count: int) -> str:
    """
    সুন্দর হেডার তৈরি করে — Auto count, Auto time সহ।
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    bd_time = datetime.now(timezone.utc)
    # Bangladesh time (UTC+6) — optional
    from datetime import timedelta
    bd_time = (bd_time + timedelta(hours=6)).strftime("%Y-%m-%d %H:%M BST")

    lines = [
        "#EXTM3U",
        "# ═══════════════════════════════════════",
        "#       ★ MRBOTRX AYNA PLAYLIST ★",
        "# ═══════════════════════════════════════",
        f"# 📺 Playlist : {PLAYLIST_ID}",
        f"# 👤 Author   : {AUTHOR}",
        f"# 📡 Telegram : {TELEGRAM}",
        f"# 🔢 Channels : {channel_count}",
        f"# 🕒 Updated  : {now_utc}  |  {bd_time}",
        "# ═══════════════════════════════════════",
        "",
    ]
    return "\n".join(lines) + "\n"

# ================= WRITE =================
def write_playlist(channels):
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    # Fast first, slow last
    channels.sort(key=lambda c: (c.get("speed_ms", 999999), c.get("group", ""), c["name"]))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        # ✅ সুন্দর হেডার
        f.write(build_header(len(channels)))

        # ✅ Pinned IPTV LINKS
        f.write(PINNED_ENTRY)
        f.write("\n")

        # ✅ সব working চ্যানেল
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
    summary = Counter(c["group"] for c in channels)
    for g, cnt in summary.most_common():
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
