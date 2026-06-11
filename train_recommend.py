import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import pickle
import os

CSV_FILE = "japan_large_reviews.csv"
if not os.path.exists(CSV_FILE):
    CSV_FILE = "japan_events_reviews.csv"

MODEL_FILE = "tfidf_model.pkl"


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


def recommend(query, vectorizer, tfidf_matrix, activity_df, top_n=5):
    query_vec = vectorizer.transform([clean_text(query)])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_idx = scores.argsort()[::-1][:top_n]
    results = activity_df.iloc[top_idx][["city", "activity"]].copy()
    results["score"] = np.round(scores[top_idx], 4)
    return results[results["score"] > 0].reset_index(drop=True)


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
    print(f"고유 활동 수: {len(activity_df)}개")

    # 5. TF-IDF 학습
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=1,
    )
    tfidf_matrix = vectorizer.fit_transform(activity_df["clean_review"])
    print(f"TF-IDF 행렬: {tfidf_matrix.shape}")

    # 6. 모델 저장
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(
            {
                "vectorizer": vectorizer,
                "matrix": tfidf_matrix,
                "activities": activity_df,
            },
            f,
        )
    print(f"모델 저장 완료: {MODEL_FILE}\n")

    # 7. 추천 테스트
    test_queries = [
        "pottery craft workshop",
        "outdoor nature hiking",
        "food cooking local",
        "cultural temple history",
        "family kids fun",
    ]
    for q in test_queries:
        print(f"[쿼리] '{q}'")
        result = recommend(q, vectorizer, tfidf_matrix, activity_df, top_n=3)
        if result.empty:
            print("  결과 없음")
        else:
            for _, row in result.iterrows():
                print(f"  {row['city']:20s} | {row['activity'][:50]:50s} | score={row['score']}")
        print()


if __name__ == "__main__":
    main()
