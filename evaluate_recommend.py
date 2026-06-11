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


def is_english_or_japanese(text):
    text = str(text)
    has_jp = any('぀' <= c <= '鿿' for c in text)
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    is_en = ascii_ratio > 0.85
    return has_jp or is_en


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z぀-鿿\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig")
    df = df[df["review"].apply(is_english_or_japanese)].copy()
    print(f"영어+일본어 필터 후: {len(df)}행")
    df["clean_review"] = df["review"].apply(clean_text)

    # 활동별로 리뷰 분리: 마지막 1개는 테스트, 나머지는 학습
    train_rows, test_rows = [], []
    for (country, city, activity), group in df.groupby(["country", "city", "activity"]):
        group = group.reset_index(drop=True)
        if len(group) < 2:
            continue
        train_rows.append({
            "country": country,
            "city": city,
            "activity": activity,
            "clean_review": " ".join(group["clean_review"].iloc[:-1]),
        })
        test_rows.append({
            "country": country,
            "city": city,
            "activity": activity,
            "query": group["clean_review"].iloc[-1],
        })

    train_df = pd.DataFrame(train_rows)
    test_df  = pd.DataFrame(test_rows)
    print(f"학습 활동 수: {len(train_df)}개 | 테스트 쿼리 수: {len(test_df)}개\n")

    # TF-IDF 학습
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words="english", min_df=1)
    tfidf_matrix = vectorizer.fit_transform(train_df["clean_review"])

    # 평가
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0

    for _, row in test_df.iterrows():
        query_vec = vectorizer.transform([row["query"]])
        scores    = cosine_similarity(query_vec, tfidf_matrix).flatten()
        ranked    = scores.argsort()[::-1]

        pred_top1 = train_df.iloc[ranked[0]]["activity"]
        pred_top3 = [train_df.iloc[i]["activity"] for i in ranked[:3]]
        pred_top5 = [train_df.iloc[i]["activity"] for i in ranked[:5]]

        if pred_top1 == row["activity"]:
            top1_correct += 1
        if row["activity"] in pred_top3:
            top3_correct += 1
        if row["activity"] in pred_top5:
            top5_correct += 1

    n = len(test_df)
    print(f"Top-1 Accuracy : {top1_correct}/{n} = {top1_correct/n*100:.1f}%")
    print(f"Top-3 Accuracy : {top3_correct}/{n} = {top3_correct/n*100:.1f}%")
    print(f"Top-5 Accuracy : {top5_correct}/{n} = {top5_correct/n*100:.1f}%")


if __name__ == "__main__":
    main()
