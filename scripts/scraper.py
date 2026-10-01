from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import pandas as pd
import os
import re
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
# SCRAPE
# ============================================================

def scrape(name, url, max_reviews=30):

    output_file = os.path.join(
        RAW_DIR,
        f"{name}.csv"
    )

    print()
    print("=" * 70)
    print(f"[{name}] MEMULAI SCRAPING")
    print(f"[{name}] Target: {max_reviews} review")
    print("=" * 70)

    reviews = {}

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

        # ----------------------------------------------------
        # Buka Maps
        # ----------------------------------------------------

        try:
            open_maps(
                page,
                url,
                name
            )
        except Exception as error:
            print(f"[{name}] Gagal membuka Maps: {error}")
            context.close()
            return

        # ----------------------------------------------------
        # Buka Ulasan
        # ----------------------------------------------------

        if not open_reviews_tab(page, name):
            print(f"[{name}] Gagal membuka tab Ulasan.")
            context.close()
            return

        # ----------------------------------------------------
        # Tunggu review pertama
        # ----------------------------------------------------

        print(f"[{name}] Menunggu review...")

        try:
            page.wait_for_selector(
                "div[data-review-id]",
                timeout=20000
            )
            print(f"[{name}] Review terdeteksi.")
        except PlaywrightTimeoutError:
            print(f"[{name}] Review tidak terdeteksi.")
            context.close()
            return

        # ----------------------------------------------------
        # LOOP SCRAPING
        # ----------------------------------------------------

        no_new_data = 0
        scroll_count = 0
        max_scrolls = 100

        while len(reviews) < max_reviews:

            # -----------------------------------------------
            # Ambil review yang sedang ada di DOM
            # -----------------------------------------------

            added, _ = collect_visible_reviews(
                page,
                name,
                reviews
            )

            # Simpan progress setiap putaran.
            save_reviews(
                reviews,
                output_file
            )

            # -----------------------------------------------
            # Cek target
            # -----------------------------------------------

            if len(reviews) >= max_reviews:
                print(
                    f"[{name}] Target {max_reviews} tercapai."
                )
                break

            # -----------------------------------------------
            # Scroll
            # -----------------------------------------------

            scroll_count += 1

            if scroll_count > max_scrolls:
                print(
                    f"[{name}] Batas maksimum scroll "
                    f"({max_scrolls}) tercapai."
                )
                break

            print(
                f"[{name}] Scroll ke-{scroll_count}..."
            )

            scroll_ok = scroll_reviews(page)

            if not scroll_ok:
                no_new_data += 1
                print(
                    f"[{name}] Scroll tidak menghasilkan perubahan "
                    f"({no_new_data}/5)."
                )

                if no_new_data >= 5:
                    print(
                        f"[{name}] Panel review tidak berkembang lagi."
                    )
                    break

                # Beri kesempatan satu putaran berikutnya.
                page.wait_for_timeout(1200)
                continue

            # -----------------------------------------------
            # Beri waktu Google Maps melakukan lazy loading
            # -----------------------------------------------

            page.wait_for_timeout(1800)

            # -----------------------------------------------
            # Langsung ambil review lagi setelah scroll
            # -----------------------------------------------

            added_after_scroll, _ = collect_visible_reviews(
                page,
                name,
                reviews
            )

            save_reviews(
                reviews,
                output_file
            )

            print(
                f"[{name}] Setelah scroll: "
                f"+{added_after_scroll} review baru | "
                f"Total={len(reviews)}"
            )

            # -----------------------------------------------
            # Evaluasi
            # -----------------------------------------------

            if added_after_scroll > 0 or added > 0:
                no_new_data = 0
            else:
                no_new_data += 1

                print(
                    f"[{name}] Belum mendapatkan review baru "
                    f"({no_new_data}/5)"
                )

                if no_new_data >= 5:
                    print(
                        f"[{name}] Tidak ditemukan review baru "
                        f"setelah beberapa kali scroll."
                    )
                    break

        context.close()

    # ========================================================
    # HASIL AKHIR
    # ========================================================

    if reviews:

        save_reviews(
            reviews,
            output_file
        )

        df = pd.read_csv(
            output_file
        )

        print()
        print("=" * 70)
        print(f"[{name}] SELESAI")
        print(f"Total review: {len(df)}")
        print(f"File: {output_file}")
        print("=" * 70)

    else:
        print(
            f"[{name}] Tidak ada data yang tersimpan."
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) > 1:

        command = (
            sys.argv[1]
            .strip()
            .lower()
        )

        if command == "login":

            login_session()

        elif command in DESTINATIONS:
            scrape(
                command,
                DESTINATIONS[command],
                max_reviews=1000
            )

        else:

            print(
                "Destinasi tidak dikenali."
            )

            print(
                "Pilihan:"
            )

            for destination in DESTINATIONS:
                print(
                    f"  - {destination}"
                )

    else:

        # Mode semua destinasi tetap memakai 500.
        for name, url in DESTINATIONS.items():
            scrape(
                name,
                url,
                max_reviews=500
            )
