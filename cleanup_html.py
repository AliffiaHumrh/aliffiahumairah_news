"""
Script SEKALI-JALAN untuk membersihkan tag HTML dari data yang sudah
terlanjur tersimpan di Supabase (sebelum fix clean_html() di crawler.py
ditambahkan).

Aman dijalankan berkali-kali (idempotent) -- baris yang sudah bersih
otomatis dilewati, tidak di-update ulang.

Jalankan sekali saja setelah crawler.py sudah di-update:
    python cleanup_html.py
"""

import logging

import config
from crawler import clean_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("cleanup_html")


def main():
    if config.DB_BACKEND != "supabase":
        print(
            "DB_BACKEND di .env bukan 'supabase' -- script ini khusus untuk "
            "membersihkan data yang sudah ada di Supabase. Tidak ada yang dijalankan."
        )
        return

    from supabase import create_client
    client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

    print("Mengambil semua baris dari tabel 'news'...")
    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = client.table("news").select("id, content").range(offset, offset + page_size - 1).execute()
        batch = resp.data
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    print(f"Total {len(rows)} baris ditemukan. Memeriksa mana yang perlu dibersihkan...\n")

    checked = 0
    updated = 0
    skipped_empty = 0

    for row in rows:
        checked += 1
        raw = row.get("content")
        if not raw:
            skipped_empty += 1
            continue

        cleaned = clean_html(raw)
        if cleaned != raw:
            client.table("news").update({"content": cleaned}).eq("id", row["id"]).execute()
            updated += 1
            if updated % 25 == 0:
                print(f"  ... {updated} baris sudah dibersihkan sejauh ini")

    print(
        f"\nSelesai. Diperiksa: {checked}, dibersihkan: {updated}, "
        f"dilewati (content kosong): {skipped_empty}, "
        f"sudah bersih dari awal: {checked - updated - skipped_empty}."
    )


if __name__ == "__main__":
    main()