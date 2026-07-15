"""
Text preprocessing (FR-04).

Fondasi untuk topic modeling (BERTopic, FR-05) dan sentiment analysis
(IndoBERT, FR-06). Pipeline standar NLP Bahasa Indonesia:

1. Cleaning    -> buang URL, angka, tanda baca, whitespace berlebih
2. Case folding -> huruf kecil semua
3. Tokenizing  -> pecah jadi kata per kata
4. Stopword removal -> buang kata umum tak bermakna ("yang", "di", "dan", dst)
5. Stemming    -> kembalikan ke kata dasar ("berlari" -> "lari")

Pakai Sastrawi (library stemming & stopword Bahasa Indonesia paling umum
dipakai), bukan library berbahasa Inggris seperti NLTK -- stemmer bahasa
Inggris tidak paham morfologi Bahasa Indonesia (awalan/akhiran seperti
me-, ber-, -kan, -an, dst).

Catatan performa: StemmerFactory().create_stemmer() itu operasi yang agak
berat untuk di-inisialisasi berkali-kali, jadi dibuat sekali di level
modul (bukan di dalam fungsi) supaya dipakai ulang.
"""

import re

from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

_stopword_remover = StopWordRemoverFactory().create_stop_word_remover()
_stemmer = StemmerFactory().create_stemmer()

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_NON_ALPHA_RE = re.compile(r"[^a-z\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """
    Tahap 1-2: cleaning + case folding.
    Buang URL, angka, tanda baca, huruf kecil semua, rapikan spasi.
    """
    if not text:
        return ""
    text = text.lower()
    text = _URL_RE.sub(" ", text)
    text = _NON_ALPHA_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    """Tahap 3: pecah jadi list kata. Asumsi input sudah lewat clean_text()."""
    if not text:
        return []
    return text.split()


def remove_stopwords(text: str) -> str:
    """Tahap 4: buang stopword Bahasa Indonesia. Input & output string."""
    if not text:
        return ""
    return _stopword_remover.remove(text)


def stem(text: str) -> str:
    """Tahap 5: stemming ke kata dasar. Input & output string."""
    if not text:
        return ""
    return _stemmer.stem(text)


def preprocess(raw_text: str) -> dict:
    """
    Pipeline lengkap. Return dict dengan tahapan menengah -- berguna untuk
    debugging/inspeksi, dan supaya pemanggil bisa pilih mau pakai versi
    mana (misal topic modeling biasanya pakai versi ter-stem, tapi kadang
    versi sebelum stemming lebih baik untuk keperluan lain).

    {
      "clean": "...",       -> setelah cleaning + case folding
      "no_stopwords": "...", -> setelah stopword removal
      "stemmed": "...",      -> setelah stemming (versi final, siap dipakai)
      "tokens": [...],       -> token dari versi stemmed
    }
    """
    cleaned = clean_text(raw_text)
    no_stopwords = remove_stopwords(cleaned)
    stemmed = stem(no_stopwords)
    tokens = tokenize(stemmed)

    return {
        "clean": cleaned,
        "no_stopwords": no_stopwords,
        "stemmed": stemmed,
        "tokens": tokens,
    }