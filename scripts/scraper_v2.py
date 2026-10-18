r"""
scraper_v2.py

Perubahan dari scraper.py:
1. Opsi urutan dipilih hanya di dalam menu "Urutkan" dan divalidasi dari data.
   Jika gagal, scraping berhenti (tidak memakai urutan bawaan diam-diam).
2. Filter bintang (opsional) juga divalidasi.
3. Melanjutkan dari file hasil sebelumnya, tidak menimpa. File lama dicadangkan
   otomatis ke data/raw/backup_otomatis.
4. Mode uji (--uji): 30 ulasan, hasil di data/uji_scraper (tidak masuk data/raw).
5. Perintah memakai argparse. Gunakan: python scripts\scraper_v2.py --help
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import argparse
import datetime
import os
import re
import shutil
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


# ============================================================
# KONFIGURASI
# ============================================================

DESTINATIONS = {
    "jatimpark1": "https://maps.app.goo.gl/TeFCLBmmoJUcMHn97",
    "jatimpark2": "https://maps.app.goo.gl/cJuHcetEuSNWhkAPA",
    "jatimpark3": "https://maps.app.goo.gl/FPn1ZtLKeLrtM2BV8",
    "museum_angkut": "https://maps.app.goo.gl/pfRMMzpxZqJqz5xs8",
    "bns": "https://maps.app.goo.gl/8WAo9nPJG6csYGJn7",
    "museum_tubuh": "https://maps.app.goo.gl/GRsMBxLU4e3MWqLz6",
}

RAW_DIR = os.path.join("data", "raw")
PROFILE_DIR = os.path.join("browser_profile")
UJI_DIR = os.path.join("data", "uji_scraper")
BACKUP_DIR = os.path.join(RAW_DIR, "backup_otomatis")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)


# ============================================================
# HELPER
# ============================================================

def safe_inner_text(locator, timeout=3000):
    try:
        if locator.count() > 0:
            return locator.first.inner_text(timeout=timeout).strip()
    except Exception:
        pass
    return ""


def set_language_parameters(url):
    """Pastikan URL Google Maps menggunakan Bahasa Indonesia."""
    try:
        parsed = urlsplit(url)

        query = dict(parse_qsl(
            parsed.query,
            keep_blank_values=True
        ))

        query["hl"] = "id"
        query["gl"] = "ID"

        return urlunsplit((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment
        ))

    except Exception:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}hl=id&gl=ID"


def save_reviews(reviews, output_file):
    """Simpan progress secara berkala agar data tidak hilang jika proses berhenti."""
    if not reviews:
        return

    df = pd.DataFrame(reviews.values())

    if "review_id" in df.columns:
        df = df.drop_duplicates(subset=["review_id"])

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# BAHASA GOOGLE MAPS
# ============================================================

def force_indonesian(page):
    print("[LANG] Mengatur preferensi Bahasa Indonesia...")

    # Cookie preferensi Google.
    try:
        page.context.add_cookies([
            {
                "name": "PREF",
                "value": "hl=id&gl=ID",
                "domain": ".google.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax",
            }
        ])
        print("[LANG] Cookie PREF=id berhasil dipasang.")
    except Exception as error:
        print(f"[LANG] Gagal memasang cookie PREF: {error}")

    body_text = ""

    try:
        body_text = page.locator("body").inner_text(timeout=5000)
    except Exception:
        pass

    english_markers = [
        "Overview",
        "Reviews",
        "About",
        "Directions",
        "Tickets",
    ]

    indonesian_markers = [
        "Ringkasan",
        "Ulasan",
        "Tentang",
        "Petunjuk arah",
    ]

    english_detected = any(
        marker in body_text
        for marker in english_markers
    )

    indonesian_detected = any(
        marker in body_text
        for marker in indonesian_markers
    )

    if indonesian_detected and not english_detected:
        print("[LANG] Google Maps sudah Bahasa Indonesia.")
        return

    print("[LANG] Google Maps masih mendeteksi Bahasa Inggris.")

    # Coba menu Language secara otomatis.
    menu_selectors = [
        "button[aria-label='Menu']",
        "button[aria-label='menu']",
        "[role='button'][aria-label='Menu']",
    ]

    menu_clicked = False

    for selector in menu_selectors:
        try:
            menu = page.locator(selector).first
            menu.wait_for(timeout=2500)
            menu.click(timeout=2500)
            page.wait_for_timeout(700)
            print(f"[LANG] Menu dibuka: {selector}")
            menu_clicked = True
            break
        except Exception:
            continue

    if menu_clicked:
        language_candidates = [
            "Language",
            "Language / Bahasa",
            "Bahasa",
            "Bahasa / Language",
        ]

        language_clicked = False

        for text in language_candidates:
            try:
                locator = page.get_by_text(text, exact=True).first
                locator.wait_for(timeout=2000)
                locator.click(timeout=2000)
                page.wait_for_timeout(800)
                print(f"[LANG] Opsi bahasa dibuka: {text}")
                language_clicked = True
                break
            except Exception:
                continue

        if language_clicked:
            language_options = [
                "Indonesia",
                "Indonesian",
                "Bahasa Indonesia",
            ]

            for text in language_options:
                try:
                    locator = page.get_by_text(text, exact=True).first
                    locator.wait_for(timeout=2000)
                    locator.click(timeout=2000)
                    page.wait_for_timeout(2000)
                    print(f"[LANG] Bahasa Indonesia dipilih: {text}")
                    break
                except Exception:
                    continue

    try:
        body_text = page.locator("body").inner_text(timeout=5000)

        if any(
            word in body_text
            for word in ["Ulasan", "Tentang", "Petunjuk arah"]
        ):
            print(
                "[LANG] Berhasil: antarmuka Google Maps "
                "terdeteksi Bahasa Indonesia."
            )
        else:
            print("[LANG] Bahasa Indonesia belum terdeteksi.")
    except Exception:
        pass


# ============================================================
# DISMISS POPUP LOGIN
# ============================================================

def dismiss_login_popup(page):
    """
    Tutup popup login Google Maps jika muncul.
    Strategi utama: tekan Escape (tidak memicu navigasi).
    Fallback: klik area di luar dialog.
    Hindari klik tombol 'Tutup' karena bisa memicu navigasi ke map view.
    """

    # Cek apakah ada dialog/popup login.
    dialog_selectors = [
        "[role='dialog']",
        "div[jsaction*='dismiss']",
    ]

    popup_found = False
    for sel in dialog_selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible(timeout=1000):
                popup_found = True
                break
        except Exception:
            pass

    if not popup_found:
        return False

    # Strategi 1: Escape key — aman, tidak memicu navigasi.
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(600)
        print("[POPUP] Popup login ditutup (Escape).")
        return True
    except Exception:
        pass

    # Strategi 2: Klik di luar area dialog (body pojok kiri atas).
    try:
        page.mouse.click(10, 10)
        page.wait_for_timeout(600)
        print("[POPUP] Popup login ditutup (klik luar).")
        return True
    except Exception:
        pass

    return False


# ============================================================
# LOGIN
# ============================================================

def login_session():
    print("=" * 70)
    print("LOGIN GOOGLE")
    print("=" * 70)
    print("Browser akan dibuka.")
    print("Silakan login ke akun Google.")
    print()
    print("Setelah selesai login, tekan ENTER di terminal.")
    print("=" * 70)

    with sync_playwright() as p:
        context = p.firefox.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            locale="id-ID",
            user_agent=USER_AGENT,
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=1.0,en;q=0.1"
            },
            viewport={
                "width": 1280,
                "height": 800,
            }
        )

        page = context.new_page()
        page.bring_to_front()

        page.goto(
            "https://accounts.google.com",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        input("\nTekan ENTER setelah login selesai... ")
        context.close()

    print("\nLogin tersimpan.")


# ============================================================
# BUKA GOOGLE MAPS
# ============================================================

def open_maps(page, url, name):
    print(f"[{name}] Membuka Google Maps...")

    page.bring_to_front()

    page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000,
    )

    page.wait_for_timeout(3500)

    resolved_url = page.url

    print(f"[{name}] URL hasil redirect:")
    print(resolved_url)

    localized_url = set_language_parameters(resolved_url)

    print(f"[{name}] URL dengan bahasa Indonesia:")
    print(localized_url)

    page.goto(
        localized_url,
        wait_until="domcontentloaded",
        timeout=30000,
    )

    page.bring_to_front()
    page.wait_for_timeout(3500)

    force_indonesian(page)

    page.wait_for_timeout(2500)

    # Tutup popup login jika muncul setelah halaman dimuat.
    dismiss_login_popup(page)

    # Tunggu agar redirect async (jika ada) selesai sebelum cek URL.
    page.wait_for_timeout(2000)

    # Verifikasi masih di place page setelah dismiss popup.
    if "/maps/place/" not in page.url:
        print(f"[{name}] Halaman bukan place page ({page.url[:60]}...). Navigasi ulang...")
        page.goto(
            localized_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )
        page.wait_for_timeout(3000)
        # Gunakan Escape untuk tutup popup kali ini.
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(600)
        except Exception:
            pass

    print(f"[{name}] URL akhir:")
    print(page.url)

    print(f"[{name}] Judul:")
    print(page.title())


# ============================================================
# BUKA TAB ULASAN
# ============================================================

def open_reviews_tab(page, name):
    print(f"[{name}] Mencari tab Ulasan...")

    page.bring_to_front()
    page.wait_for_timeout(1500)

    selectors = [
        "button[role='tab'][aria-label*='Ulasan']",
        "[role='tab'][aria-label*='Ulasan']",
        "button[role='tab'][aria-label*='Reviews']",
        "[role='tab'][aria-label*='Reviews']",
    ]

    for selector in selectors:
        try:
            element = page.locator(selector).first
            element.wait_for(timeout=4000)
            element.click(timeout=4000)
            page.wait_for_timeout(1800)
            print(f"[{name}] Tab ulasan dibuka: {selector}")
            return True
        except Exception:
            continue

    texts = [
        "Ulasan",
        "Reviews",
        "Lihat semua ulasan",
        "See all reviews",
        "Ulasan lainnya",
        "More reviews",
    ]

    for text in texts:
        try:
            locator = page.get_by_text(text, exact=False).first
            locator.wait_for(timeout=3000)
            locator.click(timeout=3000)
            page.wait_for_timeout(1800)
            print(f"[{name}] Tab/tombol ulasan dibuka: {text}")
            return True
        except Exception:
            continue

    # Fallback sekali, menggunakan scroll halaman biasa.
    page.mouse.wheel(0, 1200)
    page.wait_for_timeout(1000)

    for text in texts:
        try:
            locator = page.get_by_text(text, exact=False).first
            locator.wait_for(timeout=2500)
            locator.click(timeout=2500)
            page.wait_for_timeout(1800)
            print(f"[{name}] Ulasan dibuka setelah scroll: {text}")
            return True
        except Exception:
            continue

    return False


# ============================================================
# IDENTIFIKASI CONTAINER REVIEW
# ============================================================

def get_review_container(page):
    """
    Mengembalikan locator container review Google Maps.
    Tidak bergantung pada satu selector saja.
    """

    candidates = [
        "div.m6QErb.DxyBCb",
        "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
        "div.m6QErb.kA9KIf.dS8AEf",
        "div.e07Vkf.kA9KIf",
    ]

    for selector in candidates:
        try:
            locators = page.locator(selector)
            count = locators.count()

            for i in range(count):
                candidate = locators.nth(i)

                if candidate.count() == 0:
                    continue

                info = candidate.evaluate(
                    """
                    element => ({
                        visible: element.offsetParent !== null,
                        scrollable: element.scrollHeight > element.clientHeight,
                        reviewCount: element.querySelectorAll(
                            'div[data-review-id]'
                        ).length,
                        scrollHeight: element.scrollHeight,
                        clientHeight: element.clientHeight
                    })
                    """
                )

                if (
                    info["visible"]
                    and info["scrollable"]
                    and info["reviewCount"] > 0
                ):
                    return candidate

        except Exception:
            continue

    return None


# ============================================================
# SCROLL REVIEW
# ============================================================

def scroll_reviews(page):
    """
    Strategi scroll utama:
    1. Cari container review.
    2. Arahkan browser ke review terakhir.
    3. Gunakan mouse wheel di area container.
    4. Jika perlu, fallback ke scrollTop container.

    Pendekatan ini dibuat untuk infinite list Google Maps.
    """

    try:
        container = get_review_container(page)

        if container is None:
            print("[SCROLL] Container review tidak ditemukan.")
            return False

        # ----------------------------------------------------
        # Kondisi sebelum scroll
        # ----------------------------------------------------

        before = container.evaluate(
            "element => ({top: element.scrollTop, height: element.scrollHeight, client: element.clientHeight})"
        )

        review_locator = page.locator("div[data-review-id]")
        review_count = review_locator.count()

        if review_count == 0:
            print("[SCROLL] Tidak ada review card.")
            return False

        # ----------------------------------------------------
        # 1. Scroll review terakhir ke viewport
        # ----------------------------------------------------

        try:
            last_review = review_locator.nth(review_count - 1)
            last_review.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(800)
        except Exception:
            pass

        # ----------------------------------------------------
        # 2. Cari ulang container setelah render
        # ----------------------------------------------------

        container = get_review_container(page)

        if container is None:
            print("[SCROLL] Container review hilang setelah render.")
            return False

        # ----------------------------------------------------
        # 3. Hover ke tengah container dan wheel.
        # Playwright mendokumentasikan mouse.wheel sebagai cara
        # manual untuk infinite list/scroll container.
        # ----------------------------------------------------

        try:
            box = container.bounding_box()

            if box:
                x = box["x"] + (box["width"] * 0.5)
                y = box["y"] + (box["height"] * 0.7)

                page.bring_to_front()
                page.mouse.move(x, y)
                page.mouse.wheel(0, 900)
                page.wait_for_timeout(1800)
        except Exception:
            pass

        # ----------------------------------------------------
        # 4. Ukur hasil scroll
        # ----------------------------------------------------

        container_after_wheel = get_review_container(page)

        if container_after_wheel is not None:
            after = container_after_wheel.evaluate(
                "element => ({top: element.scrollTop, height: element.scrollHeight, client: element.clientHeight})"
            )
        else:
            after = before

        # ----------------------------------------------------
        # 5. Jika mouse wheel tidak menghasilkan gerakan,
        #    gunakan fallback scrollTop.
        # ----------------------------------------------------

        if after["top"] == before["top"] and after["height"] == before["height"]:

            try:
                container_after_wheel.evaluate(
                    "element => element.scrollTop += Math.max(element.clientHeight * 0.75, 700)"
                )
                page.wait_for_timeout(1800)

                container_after_fallback = get_review_container(page)

                if container_after_fallback is not None:
                    after = container_after_fallback.evaluate(
                        "element => ({top: element.scrollTop, height: element.scrollHeight, client: element.clientHeight})"
                    )

            except Exception:
                pass

        print(
            "[SCROLL] "
            f"top {before['top']:.0f} → {after['top']:.0f} | "
            f"height {before['height']:.0f} → {after['height']:.0f} | "
            f"viewport={after['client']:.0f}"
        )

        moved = (
            after["top"] != before["top"]
            or after["height"] > before["height"]
        )

        if not moved:
            print("[SCROLL] Tidak ada perubahan pada panel review.")
            return False

        return True

    except Exception as error:
        print(f"[SCROLL] Error: {error}")
        return False


# ============================================================
# EXPAND REVIEW
# ============================================================

def expand_reviews(page):
    selectors = [
        "button[aria-label='Lihat lainnya']",
        "button[aria-label*='Lihat lainnya']",
        "button:has-text('Lihat lainnya')",
        "button[aria-label='See more']",
        "button[aria-label*='See more']",
        "button:has-text('See more')",
    ]

    clicked = 0

    for selector in selectors:
        try:
            buttons = page.locator(selector)
            count = buttons.count()

            for i in range(count):
                try:
                    buttons.nth(i).click(timeout=1000)
                    clicked += 1
                    page.wait_for_timeout(100)
                except Exception:
                    pass
        except Exception:
            pass

    if clicked > 0:
        print(f"[EXPAND] Membuka {clicked} review terpotong.")


# ============================================================
# REVIEW ASLI
# ============================================================

def click_original_review(item, page):
    selectors = [
        "button[aria-label*='Lihat asli']",
        "button:has-text('Lihat asli')",
        "button[aria-label*='See original']",
        "button:has-text('See original')",
    ]

    for selector in selectors:
        try:
            button = item.locator(selector).first

            if button.count() == 0:
                continue

            button.click(timeout=1500)
            page.wait_for_timeout(500)
            return True
        except Exception:
            continue

    return False


# ============================================================
# EKSTRAK RATING
# ============================================================

def extract_rating(item):
    selectors = [
        "span.kvMYJc[role='img']",
        "span[role='img'][aria-label*='star']",
        "span[role='img'][aria-label*='stars']",
        "span[role='img'][aria-label*='bintang']",
    ]

    for selector in selectors:
        try:
            locator = item.locator(selector).first

            if locator.count() == 0:
                continue

            aria = locator.get_attribute("aria-label") or ""
            match = re.search(r"(\d+)", aria)

            if match:
                return int(match.group(1))

        except Exception:
            continue

    return 0


# ============================================================
# EKSTRAK TEKS
# ============================================================

def extract_review_text(item):
    selectors = [
        "span.wiI7pd",
        "div.MyEned span.wiI7pd",
    ]

    for selector in selectors:
        try:
            locator = item.locator(selector).first
            text = safe_inner_text(locator)

            if text:
                return text
        except Exception:
            continue

    return ""


# ============================================================
# EKSTRAK TANGGAL
# ============================================================

def extract_date(item):
    selectors = [
        "span.rsqaWe",
        "span[class*='rsqaWe']",
    ]

    for selector in selectors:
        try:
            locator = item.locator(selector).first
            text = safe_inner_text(locator)

            if text:
                return text
        except Exception:
            continue

    return ""


# ============================================================
# AMBIL DAN SIMPAN SEMUA REVIEW DI DOM
# ============================================================

def collect_visible_reviews(page, name, reviews):
    """
    Membaca semua review yang sedang ada di DOM.
    Tidak bergantung pada jumlah card karena Google Maps
    dapat melakukan virtualisasi/re-render.
    """

    expand_reviews(page)

    locator = page.locator("div[data-review-id]")
    count = locator.count()

    ids_in_dom = set()
    added = 0

    for i in range(count):

        try:
            item = locator.nth(i)
            review_id = item.get_attribute("data-review-id")

            if not review_id:
                continue

            ids_in_dom.add(review_id)

            if review_id in reviews:
                continue

            original_found = click_original_review(
                item,
                page
            )

            rating = extract_rating(item)
            review_text = extract_review_text(item)
            review_date = extract_date(item)

            # Jangan menyimpan kartu kosong.
            # ID tetap tersedia, tetapi review tanpa teks masih boleh
            # disimpan karena ada kemungkinan reviewer hanya memberi rating.
            reviews[review_id] = {
                "destinasi": name,
                "review_id": review_id,
                "bintang": rating,
                "ulasan": review_text,
                "tanggal": review_date,
                "teks_asli": original_found,
            }

            added += 1

        except Exception as error:
            print(f"[REVIEW] Gagal memproses card: {error}")
            continue

    print(
        f"[{name}] DOM review={count} | "
        f"ID unik di DOM={len(ids_in_dom)} | "
        f"Review baru={added} | "
        f"Total tersimpan={len(reviews)}"
    )

    return added, ids_in_dom


# ============================================================
# URUTAN DAN FILTER (VERSI KETAT: GAGAL = BERHENTI)
# ============================================================
# Perbedaan dari versi lama:
# - Opsi urutan hanya dicari di dalam menu "Urutkan" (bukan di seluruh halaman),
#   sehingga tidak tertukar dengan item lain bernama sama (misalnya "Terbaru").
# - Setelah urutan atau filter dipilih, hasilnya divalidasi dari data ulasan.
#   Jika tidak sesuai, scraping dihentikan. Urutan bawaan tidak dipakai diam-diam.

SORT_OPTIONS = {
    "relevan":  ["Paling relevan", "Most relevant"],
    "terbaru":  ["Terbaru", "Newest"],
    "tertinggi": ["Rating tertinggi", "Highest rating"],
    "terendah": ["Rating terendah", "Lowest rating"],
}

POLA_TANGGAL_BARU = re.compile(
    r"(detik|menit|jam|hari|minggu|bulan|second|minute|hour|day|week|month)",
    re.I
)


def ambil_id_awal(page, jumlah=5):
    """ID unik ulasan pertama di DOM (urut sesuai kemunculan)."""
    try:
        ids = page.locator("div[data-review-id]").evaluate_all(
            "els => els.map(e => e.getAttribute('data-review-id'))"
        )
    except Exception:
        return []

    unik = []
    for rid in ids:
        if rid and rid not in unik:
            unik.append(rid)
        if len(unik) >= jumlah:
            break
    return unik


def ambil_kartu_awal(page, jumlah=8):
    """Baca beberapa kartu ulasan pertama: daftar (id, bintang, tanggal)."""
    hasil, terlihat = [], set()
    locator = page.locator("div[data-review-id]")

    try:
        total = locator.count()
    except Exception:
        return hasil

    for i in range(total):
        if len(hasil) >= jumlah:
            break
        try:
            item = locator.nth(i)
            rid = item.get_attribute("data-review-id")
            if not rid or rid in terlihat:
                continue
            terlihat.add(rid)
            hasil.append((rid, extract_rating(item), extract_date(item)))
        except Exception:
            continue

    return hasil


def atur_urutan(page, sort_order, name):
    """Pilih urutan lewat menu 'Urutkan'. Mengembalikan (ok, pesan)."""
    if sort_order == "relevan":
        return True, "urutan bawaan"

    print(f"[{name}] Mengatur urutan ulasan: {sort_order}...")

    tombol = [
        "button[aria-label*='Urutkan']",
        "button[aria-label*='Sort']",
        "button[data-value='Sort']",
        "button[jsaction*='sort']",
    ]

    terbuka = False
    for selector in tombol:
        try:
            btn = page.locator(selector).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click(timeout=3000)
                page.wait_for_timeout(1200)
                print(f"[{name}] Menu urutan dibuka: {selector}")
                terbuka = True
                break
        except Exception:
            continue

    if not terbuka:
        return False, "Tombol 'Urutkan' tidak ditemukan."

    item = None
    for label in SORT_OPTIONS[sort_order]:
        pola = re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)

        kandidat = page.locator("[role='menuitemradio']").filter(has_text=pola)
        try:
            if kandidat.count() > 0:
                item = kandidat.first
                break
        except Exception:
            pass

        kandidat = page.locator("[role='menu']").get_by_text(label, exact=True)
        try:
            if kandidat.count() > 0:
                item = kandidat.first
                break
        except Exception:
            pass

    if item is None:
        try:
            tampil = page.locator("[role='menuitemradio']").all_inner_texts()
        except Exception:
            tampil = []
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False, f"Opsi '{sort_order}' tidak ada di menu. Opsi yang terbaca: {tampil}"

    try:
        item.click(timeout=3000)
    except Exception as error:
        return False, f"Gagal mengklik opsi '{sort_order}': {error}"

    page.wait_for_timeout(2000)
    return True, "opsi urutan diklik"


def atur_filter_bintang(page, star, name):
    """Klik baris bintang pada ringkasan rating (hanya elemen yang labelnya diawali angka bintang)."""
    print(f"[{name}] Mengatur filter bintang: {star}...")

    selectors = [
        f"[aria-label^='{star} bintang']",
        f"[aria-label^='{star} star']",
    ]

    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.count() > 0 and el.is_visible(timeout=3000):
                el.click(timeout=3000)
                page.wait_for_timeout(2000)
                print(f"[{name}] Filter bintang diklik: {selector}")
                return True, "filter diklik"
        except Exception:
            continue

    try:
        label = page.evaluate(
            "() => Array.from(document.querySelectorAll('[aria-label]'))"
            ".map(e => e.getAttribute('aria-label'))"
            ".filter(t => /bintang|star/i.test(t)).slice(0, 10)"
        )
    except Exception:
        label = []

    return False, f"Elemen filter {star} bintang tidak ditemukan. Label yang terbaca: {label}"


def validasi_tampilan(page, name, sort_order, star, id_sebelum, tunggu_detik=10):
    """
    Pastikan daftar ulasan benar-benar berubah dan sesuai pilihan.
    Mengembalikan (ok, pesan).
    """
    berubah = False
    for _ in range(tunggu_detik * 2):
        id_kini = ambil_id_awal(page)
        if id_kini and id_kini != id_sebelum:
            berubah = True
            break
        page.wait_for_timeout(500)

    if not berubah:
        return False, "Daftar ulasan tidak berubah setelah pilihan (ID awal sama dengan tampilan sebelumnya)."

    page.wait_for_timeout(1500)
    kartu = ambil_kartu_awal(page, 8)

    if len(kartu) < 3:
        return False, "Terlalu sedikit ulasan yang terbaca untuk divalidasi."

    bintang = [k[1] for k in kartu]
    if 0 in bintang:
        return False, f"Bintang tidak terbaca pada sebagian ulasan: {bintang}"

    if star:
        if any(b != star for b in bintang):
            return False, f"Filter {star} bintang tidak sesuai. Bintang yang terbaca: {bintang}"
        return True, f"filter {star} bintang sesuai (bintang: {bintang})"

    if sort_order == "terendah":
        if any(b > 2 for b in bintang):
            return False, f"Urutan 'terendah' tidak sesuai. Bintang yang terbaca: {bintang}"
        return True, f"urutan terendah sesuai (bintang: {bintang})"

    if sort_order == "tertinggi":
        if any(b != 5 for b in bintang):
            return False, f"Urutan 'tertinggi' tidak sesuai. Bintang yang terbaca: {bintang}"
        return True, f"urutan tertinggi sesuai (bintang: {bintang})"

    if sort_order == "terbaru":
        for _, _, tanggal in kartu[:5]:
            t = (tanggal or "").lower()
            if "tahun" in t or "year" in t or not POLA_TANGGAL_BARU.search(t):
                return False, f"Urutan 'terbaru' tidak sesuai. Tanggal yang terbaca: '{tanggal}'"
        return True, f"urutan terbaru sesuai (tanggal: {[k[2] for k in kartu[:5]]})"

    return True, "tidak ada aturan validasi tambahan"


# ============================================================
# PROGRES: LANJUT DARI FILE LAMA, JANGAN MENIMPA
# ============================================================

def muat_progres(output_file):
    """Muat file hasil sebelumnya agar scraping melanjutkan, bukan menimpa."""
    if not os.path.exists(output_file):
        return {}

    try:
        df = pd.read_csv(output_file, encoding="utf-8-sig").fillna("")
    except Exception as error:
        print(f"File hasil lama tidak dapat dibaca ({error}).")
        print("Scraping dibatalkan agar file lama tidak tertimpa.")
        sys.exit(1)

    if "review_id" not in df.columns:
        print("File hasil lama tidak memiliki kolom review_id. Scraping dibatalkan.")
        sys.exit(1)

    return {row["review_id"]: row for row in df.to_dict("records")}


def cadangkan_file(output_file):
    """Salin file lama ke data/raw/backup_otomatis sebelum diubah."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stempel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nama = os.path.splitext(os.path.basename(output_file))[0]
    tujuan = os.path.join(BACKUP_DIR, f"{nama}_{stempel}.csv")
    shutil.copy2(output_file, tujuan)
    print(f"Cadangan otomatis: {tujuan}")


# ============================================================
# SCRAPE
# ============================================================

def scrape(name, url, max_reviews=3000, sort_order="relevan", star_filter=None, mode_uji=False):

    suffix = ""
    if sort_order and sort_order != "relevan":
        suffix += f"_{sort_order}"
    if star_filter:
        suffix += f"_bintang{star_filter}"

    folder = UJI_DIR if mode_uji else RAW_DIR
    os.makedirs(folder, exist_ok=True)
    output_file = os.path.join(folder, f"{name}{suffix}.csv")

    # Lanjutkan dari file lama (jika ada) dan cadangkan lebih dulu.
    reviews = muat_progres(output_file)
    awal = len(reviews)
    if awal and not mode_uji:
        cadangkan_file(output_file)

    print()
    print("=" * 70)
    print(f"[{name}] MEMULAI SCRAPING (v2)")
    print(f"[{name}] Target total di file ini: {max_reviews} review")
    print(f"[{name}] Urutan: {sort_order} | Filter bintang: {star_filter or 'semua'}")
    print(f"[{name}] Output: {output_file}")
    if mode_uji:
        print(f"[{name}] MODE UJI: hasil tidak masuk ke data/raw.")
    if awal:
        print(f"[{name}] Melanjutkan dari file yang ada: {awal} review sudah tersimpan.")
    print("=" * 70)

    if awal >= max_reviews:
        print(f"[{name}] Target sudah tercapai oleh file yang ada. Tidak ada yang dikerjakan.")
        return

    with sync_playwright() as p:

        context = p.firefox.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            locale="id-ID",
            user_agent=USER_AGENT,
            extra_http_headers={
                "Accept-Language": "id-ID,id;q=1.0,en;q=0.1"
            },
            viewport={
                "width": 1280,
                "height": 800,
            }
        )

        page = context.new_page()
        page.bring_to_front()

        try:
            open_maps(page, url, name)
        except Exception as error:
            print(f"[{name}] Gagal membuka Maps: {error}")
            context.close()
            return

        if not open_reviews_tab(page, name):
            print(f"[{name}] Gagal membuka tab Ulasan.")
            context.close()
            return

        # Tunggu ulasan pada tampilan bawaan.
        print(f"[{name}] Menunggu review...")
        try:
            page.wait_for_selector("div[data-review-id]", timeout=20000)
            print(f"[{name}] Review terdeteksi.")
        except PlaywrightTimeoutError:
            print(f"[{name}] Review tidak terdeteksi.")
            context.close()
            return
        page.wait_for_timeout(1500)

        # ----------------------------------------------------
        # Urutan dan filter: harus berhasil dan tervalidasi.
        # ----------------------------------------------------

        if sort_order != "relevan":
            id_sebelum = ambil_id_awal(page)
            ok, pesan = atur_urutan(page, sort_order, name)
            if ok:
                ok, pesan = validasi_tampilan(page, name, sort_order, None, id_sebelum)
            if not ok:
                print(f"[{name}] GAGAL MENGATUR URUTAN: {pesan}")
                print(f"[{name}] Scraping dihentikan. Urutan bawaan tidak dipakai diam-diam.")
                context.close()
                return
            print(f"[{name}] URUTAN OK: {pesan}")

        if star_filter:
            id_sebelum = ambil_id_awal(page)
            ok, pesan = atur_filter_bintang(page, star_filter, name)
            if ok:
                ok, pesan = validasi_tampilan(page, name, None, star_filter, id_sebelum)
            if not ok:
                print(f"[{name}] GAGAL MENGATUR FILTER: {pesan}")
                print(f"[{name}] Scraping dihentikan. Tampilan tanpa filter tidak dipakai diam-diam.")
                context.close()
                return
            print(f"[{name}] FILTER OK: {pesan}")

        # ----------------------------------------------------
        # LOOP SCRAPING
        # ----------------------------------------------------

        no_new_data = 0
        scroll_count = 0
        max_scrolls = max(600, max_reviews // 4)

        while len(reviews) < max_reviews:

            added, _ = collect_visible_reviews(page, name, reviews)
            save_reviews(reviews, output_file)

            if len(reviews) >= max_reviews:
                print(f"[{name}] Target {max_reviews} tercapai.")
                break

            scroll_count += 1

            if scroll_count > max_scrolls:
                print(f"[{name}] Batas maksimum scroll ({max_scrolls}) tercapai.")
                break

            print(f"[{name}] Scroll ke-{scroll_count}...")

            scroll_ok = scroll_reviews(page)

            if not scroll_ok:
                no_new_data += 1
                print(f"[{name}] Scroll tidak menghasilkan perubahan ({no_new_data}/5).")

                if no_new_data >= 5:
                    print(f"[{name}] Panel review tidak berkembang lagi.")
                    break

                page.wait_for_timeout(800)
                continue

            page.wait_for_timeout(1800)

            added_after_scroll, _ = collect_visible_reviews(page, name, reviews)
            save_reviews(reviews, output_file)

            print(
                f"[{name}] Setelah scroll: "
                f"+{added_after_scroll} review baru | Total={len(reviews)}"
            )

            if added_after_scroll > 0 or added > 0:
                no_new_data = 0
            else:
                no_new_data += 1
                print(f"[{name}] Belum mendapatkan review baru ({no_new_data}/5)")

                if no_new_data >= 5:
                    print(f"[{name}] Tidak ditemukan review baru setelah beberapa kali scroll.")
                    break

        context.close()

    # ========================================================
    # HASIL AKHIR
    # ========================================================

    if reviews:
        save_reviews(reviews, output_file)
        df = pd.read_csv(output_file)

        print()
        print("=" * 70)
        print(f"[{name}] SELESAI")
        print(f"Total review di file: {len(df)} (baru di sesi ini: {len(df) - awal})")
        print(f"File: {output_file}")
        print("=" * 70)
    else:
        print(f"[{name}] Tidak ada data yang tersimpan.")


# ============================================================
# MAIN
# ============================================================
# Contoh (jalankan dari folder utama project, dengan venv):
#   .\venv\Scripts\python.exe scripts\scraper_v2.py login
#   .\venv\Scripts\python.exe scripts\scraper_v2.py bns terendah --uji
#   .\venv\Scripts\python.exe scripts\scraper_v2.py bns terendah
#   .\venv\Scripts\python.exe scripts\scraper_v2.py bns relevan --bintang 1

def main():
    parser = argparse.ArgumentParser(
        description="Scraper ulasan Google Maps v2 (urutan dan filter divalidasi)."
    )
    parser.add_argument(
        "perintah",
        help="'login' atau nama destinasi: " + ", ".join(DESTINATIONS)
    )
    parser.add_argument(
        "urutan", nargs="?", default="relevan", choices=list(SORT_OPTIONS),
        help="urutan ulasan (bawaan: relevan)"
    )
    parser.add_argument("--bintang", type=int, choices=[1, 2, 3, 4, 5],
                        help="filter bintang (opsional)")
    parser.add_argument("--target", type=int, default=3000,
                        help="target total ulasan di file ini (bawaan: 3000)")
    parser.add_argument("--uji", action="store_true",
                        help="mode uji: 30 ulasan, hasil di data/uji_scraper")
    args = parser.parse_args()

    perintah = args.perintah.strip().lower()

    if perintah == "login":
        login_session()
        return

    if perintah not in DESTINATIONS:
        print("Destinasi tidak dikenali. Pilihan:")
        for destination in DESTINATIONS:
            print(f"  - {destination}")
        sys.exit(1)

    target = 30 if args.uji else args.target

    scrape(
        perintah,
        DESTINATIONS[perintah],
        max_reviews=target,
        sort_order=args.urutan,
        star_filter=args.bintang,
        mode_uji=args.uji,
    )


if __name__ == "__main__":
    main()