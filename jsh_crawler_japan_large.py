from playwright.sync_api import sync_playwright
import pandas as pd
import time
import random
import urllib.parse

BASE = "https://www.veltra.com"

JAPAN_CITIES = [
    "/en/asia/japan/tokyo/",
    "/en/asia/japan/kyoto/",
    "/en/asia/japan/osaka/",
    "/en/asia/japan/okinawa/okinawa_main_island/",
    "/en/asia/japan/hokkaido/sapporo/",
    "/en/asia/japan/hokkaido/niseko/",
    "/en/asia/japan/hokkaido/hakodate/",
    "/en/asia/japan/nara/",
    "/en/asia/japan/hiroshima/",
    "/en/asia/japan/fukuoka/",
    "/en/asia/japan/nagasaki/",
    "/en/asia/japan/okinawa/ishigaki_yaeyama/",
    "/en/asia/japan/okinawa/miyako_island/",
    "/en/asia/japan/kanagawa/hakone_odawara/",
    "/en/asia/japan/kanagawa/yokohama_minatomirai/",
    "/en/asia/japan/yamanashi/",
    "/en/asia/japan/nagano/",
    "/en/asia/japan/aichi/",
    "/en/asia/japan/shizuoka/",
    "/en/asia/japan/yakushima/",
    "/en/asia/japan/kagoshima/",
    "/en/asia/japan/miyagi/",
    "/en/asia/japan/ishikawa/kanazawa/",
    "/en/asia/japan/hyogo/",
    "/en/asia/japan/wakayama/",
    "/en/asia/japan/tochigi/nikko_okunikko_chuzenjiko/",
    "/en/asia/japan/hokkaido/shiretoko/",
    "/en/asia/japan/mie/",
    "/en/asia/japan/fukushima/",
    "/en/asia/japan/kumamoto/",
]

TARGET_PRODUCTS = 150
REVIEWS_PER_PRODUCT = 30


def rand_sleep(a=1.5, b=3.0):
    time.sleep(random.uniform(a, b))


def get_links(page, city_url):
    try:
        page.goto(BASE + city_url, wait_until="domcontentloaded", timeout=30000)
        rand_sleep(2, 3)
        for _ in range(20):
            page.evaluate("window.scrollBy(0, 800)")
            rand_sleep(0.5, 0.8)
        rand_sleep(1.5, 2.0)
    except Exception:
        return []

    links = []
    for a in page.query_selector_all('a[href*="/a/"]'):
        href = a.get_attribute("href") or ""
        if href and any(c.isdigit() for c in href) and href.count("/") >= 5 and "/reviews" not in href:
            full = (href if href.startswith("http") else BASE + href).split("?")[0]
            if full not in links:
                links.append(full)
    return links


def main():
    all_product_urls = []
    product_titles   = {}
    review_apis      = {}

    def handle_response(response):
        if "api.veltra.com/reviews/v1/reviews" in response.url and "summary" not in response.url:
            try:
                review_apis[response.url] = response.json()
            except Exception:
                pass

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.on("response", handle_response)

        # 1. 도시별 상품 URL 수집
        print("=== 도시별 상품 URL 수집 ===")
        for city_url in JAPAN_CITIES:
            if len(all_product_urls) >= TARGET_PRODUCTS:
                break
            links = get_links(page, city_url)
            city_name = city_url.strip("/").split("/")[-1]
            # 중복 제거
            new_links = [l for l in links if l not in all_product_urls]
            all_product_urls.extend(new_links)
            print(f"  {city_name}: {len(new_links)}개 추가 (누적 {len(all_product_urls)}개)")

        all_product_urls = all_product_urls[:TARGET_PRODUCTS]
        print(f"\n총 {len(all_product_urls)}개 상품 수집 완료\n")

        # 2. 각 상품 /reviews 페이지 방문
        print("=== 리뷰 수집 시작 ===")
        for i, url in enumerate(all_product_urls, 1):
            review_url = url + "/reviews"
            try:
                page.goto(review_url, wait_until="load", timeout=30000)
                rand_sleep(2, 3)
                h1 = page.query_selector("h1")
                if h1:
                    activity_name = h1.inner_text().strip().split(" - ")[0].strip()
                    pid  = url.split("/a/")[-1].split("/")[0]
                    parts = url.replace(BASE, "").strip("/").split("/")
                    city = parts[-3] if len(parts) >= 3 else "japan"
                    product_titles[pid] = (activity_name, city)
                if i % 10 == 0:
                    print(f"  진행: {i}/{len(all_product_urls)} | API 캡처 {len(review_apis)}개")
            except Exception as e:
                print(f"  [{i}] 오류: {e}")

        browser.close()

    # 3. 파싱
    print(f"\n=== API 응답 {len(review_apis)}개 파싱 ===")
    all_rows = []
    for api_url, data in review_apis.items():
        product_id = api_url.split("target_ids=")[1].split("&")[0] if "target_ids=" in api_url else ""
        pid_list   = urllib.parse.unquote(product_id).split(",")

        activity_name, city = "", ""
        for pid in pid_list:
            if pid.strip() in product_titles:
                activity_name, city = product_titles[pid.strip()]
                break

        review_list = data.get("review_list", [])[:REVIEWS_PER_PRODUCT]
        for r in review_list:
            review_text = r.get("review") or ""
            if not review_text:
                continue

            participated = r.get("participated_date") or ""
            month = int(participated.split("-")[1]) if participated and len(participated.split("-")) >= 2 else None

            ratings = r.get("ratings")
            if isinstance(ratings, dict):
                rating = ratings.get("overall") or ratings.get("total") or next(iter(ratings.values()), None)
            else:
                rating = ratings

            all_rows.append({
                "country":  "japan",
                "city":     city,
                "activity": activity_name,
                "review":   review_text,
                "month":    month,
                "rating":   rating,
            })

    if not all_rows:
        print("데이터 없음.")
        return

    df = pd.DataFrame(all_rows)
    out = "japan_large_reviews.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n=== 완료: {len(df)}행 저장 -> {out} ===")
    print(f"\n도시별 수집량:\n{df.groupby('city')['review'].count().sort_values(ascending=False).to_string()}")


if __name__ == "__main__":
    main()
