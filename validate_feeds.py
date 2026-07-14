"""
Cek cepat: dari semua sumber di config.py, mana yang RSS-nya masih hidup
dan berapa item yang berhasil di-parse.

Jalankan manual sesekali (bukan bagian dari scheduler otomatis), terutama
kalau crawler tiba-tiba mengembalikan 0 berita baru dari satu sumber --
kemungkinan besar medianya mengganti URL RSS.

Usage: python validate_feeds.py
"""

import feedparser

import config


def main():
    feedparser.USER_AGENT = config.USER_AGENT
    print(f"Mengecek {len(config.SOURCES)} sumber RSS...\n")

    ok, broken = [], []

    for source in config.SOURCES:
        name, url = source["name"], source["url"]
        parsed = feedparser.parse(url)
        n = len(parsed.entries)

        if n > 0:
            ok.append((name, url, n))
            print(f"  OK   {name:<35} {n:>3} item  -  {url}")
        else:
            broken.append((name, url))
            reason = parsed.get("bozo_exception", "0 item dikembalikan")
            print(f"  GAGAL {name:<34} -  {url}\n         alasan: {reason}")

    print(f"\nRingkasan: {len(ok)} hidup, {len(broken)} bermasalah dari {len(config.SOURCES)} sumber.")
    if broken:
        print("\nSumber bermasalah -- perlu dicek URL RSS terbaru dari situs medianya:")
        for name, url in broken:
            print(f"  - {name}: {url}")


if __name__ == "__main__":
    main()