import pandas as pd
from deep_translator import GoogleTranslator
import re
import pickle
import os

CSV_FILE = "japan_large_reviews.csv"
if not os.path.exists(CSV_FILE):
    CSV_FILE = "japan_events_reviews.csv"

PREPROCESSED_FILE = "jsh_activity_df.pkl"


def is_english_or_japanese(text):
    text = str(text)
    has_jp = any('぀' <= c <= '鿿' for c in text)
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    return has_jp or ascii_ratio > 0.85


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z぀-鿿\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def translate_activity(text):
    try:
        return GoogleTranslator(source="en", target="ko").translate(text)
    except Exception:
        return ""


def main():
    # 1. 데이터 로드
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    print(f"원본 데이터: {len(df)}행  (파일: {CSV_FILE})")

    # 2. 영어+일본어 필터
    df = df[df["review"].apply(is_english_or_japanese)].copy()
    print(f"영어+일본어 필터 후: {len(df)}행")

    # 3. 텍스트 정제
    df["clean_review"] = df["review"].apply(clean_text)

    # 4. 활동별 리뷰 합치기
    activity_df = (
        df.groupby(["country", "city", "activity"])["clean_review"]
        .apply(" ".join)
        .reset_index()
    )

    # 5. month, rating 집계 (컬럼이 있을 때만)
    if "month" in df.columns:
        def safe_mode(x):
            valid = x.dropna()
            return int(valid.mode()[0]) if not valid.empty else None
        month_df = df.groupby(["country", "city", "activity"])["month"].agg(safe_mode).reset_index()
        activity_df = activity_df.merge(month_df, on=["country", "city", "activity"])
    else:
        activity_df["month"] = None

    if "rating" in df.columns:
        rating_df = df.groupby(["country", "city", "activity"])["rating"].mean().round(1).reset_index()
        activity_df = activity_df.merge(rating_df, on=["country", "city", "activity"])
    else:
        activity_df["rating"] = None

    print(f"고유 활동 수: {len(activity_df)}개")

    # 6. 활동명 한국어 번역
    print("활동명 번역 중...")
    activity_df["activity_ko"] = activity_df["activity"].apply(translate_activity)
    print("번역 완료")

    # 7. 저장
    with open(PREPROCESSED_FILE, "wb") as f:
        pickle.dump(activity_df, f)
    print(f"전처리 데이터 저장 완료: {PREPROCESSED_FILE}")


if __name__ == "__main__":
    main()
