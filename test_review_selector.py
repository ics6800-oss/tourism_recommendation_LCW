from playwright.sync_api import sync_playwright
import time
import json

LIST_URL = "https://www.veltra.com/en/asia/japan/"


def main():
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

        # 목록 페이지에서 상품 URL 수집
        print("목록 페이지 수집...")
        page.goto(LIST_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1)

        links = []
        for a in page.query_selector_all('a[href*="/en/asia/japan/"]'):
            href = a.get_attribute("href") or ""
            if href and any(c.isdigit() for c in href) and href.count("/") >= 5 and "/reviews" not in href:
                full = href if href.startswith("http") else "https://www.veltra.com" + href
                full = full.split("?")[0]
                if full not in links:
                    links.append(full)
            if len(links) >= 5:
                break
        print(f"링크 {len(links)}개: {links[:2]}")

        # 리뷰 API 응답 가로채기
        review_data = {}

        def handle_response(response):
            if "api.veltra.com/reviews/v1/reviews" in response.url and "summary" not in response.url:
                try:
                    body = response.json()
                    review_data[response.url] = body
                    print(f"  [API 캡처] {response.url[:80]}")
                except Exception:
                    pass

        page.on("response", handle_response)

        # 각 상품 /reviews 페이지 방문
        for url in links[:3]:
            review_url = url + "/reviews"
            print(f"\n접속: {review_url}")
            page.goto(review_url, wait_until="load", timeout=30000)
            time.sleep(4)

        browser.close()

    # 결과 출력
    print(f"\n=== 캡처된 리뷰 API 응답: {len(review_data)}개 ===")
    all_rows = []
    for api_url, data in review_data.items():
        print(f"\nURL: {api_url[:80]}")
        print(f"키: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        items = []
        if isinstance(data, dict):
            items = data.get("reviews") or data.get("data") or data.get("items") or []
        elif isinstance(data, list):
            items = data
        print(f"리뷰 수: {len(items)}")
        if items:
            r = items[0]
            print(f"첫 리뷰 키: {list(r.keys()) if isinstance(r, dict) else r}")
            body = r.get("body") or r.get("text") or r.get("comment") or r.get("content") or ""
            title = r.get("title") or r.get("activity_name") or ""
            print(f"타이틀: {title}")
            print(f"리뷰: {str(body)[:150]}")
            for item in items:
                all_rows.append({
                    "title": item.get("title") or item.get("activity_name") or "",
                    "review": item.get("body") or item.get("text") or item.get("comment") or "",
                })

    if all_rows:
        import pandas as pd
        df = pd.DataFrame(all_rows)
        df.to_csv("japan_reviews_test.csv", index=False, encoding="utf-8-sig")
        print(f"\n{len(df)}행 저장 -> japan_reviews_test.csv")
    else:
        print("\n데이터 없음 - API 구조 확인 필요")


if __name__ == "__main__":
    main()
