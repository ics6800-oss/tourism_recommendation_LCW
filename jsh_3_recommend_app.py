import sys
import os
import re
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from deep_translator import GoogleTranslator
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import pandas as pd

MODEL_FILE = os.path.join(os.path.dirname(__file__), "tfidf_model.pkl")

KEYWORD_MAP = {
    "사원": "temple", "절": "temple", "신사": "shrine", "신전": "shrine",
    "도자기": "pottery ceramic", "공예": "craft workshop", "공방": "craft workshop",
    "요리": "cooking food", "음식": "food local", "먹거리": "food local",
    "하이킹": "hiking outdoor", "등산": "hiking mountain", "자연": "nature outdoor",
    "가족": "family kids", "아이": "kids children", "어린이": "kids children",
    "역사": "history cultural", "문화": "culture traditional", "전통": "traditional cultural",
    "다이빙": "diving snorkeling", "스노클링": "snorkeling ocean", "바다": "ocean sea",
    "스키": "ski snow winter", "눈": "snow winter",
    "온천": "hot spring onsen", "료칸": "ryokan traditional inn",
    "사진": "photography sightseeing", "관광": "sightseeing tour",
    "쇼핑": "shopping market", "시장": "market local",
}


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z぀-鿿\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_model():
    with open(MODEL_FILE, "rb") as f:
        data = pickle.load(f)
    return data["vectorizer"], data["matrix"], data["activities"]


def get_recommendations(query, vectorizer, tfidf_matrix, activity_df, top_n):
    query_vec = vectorizer.transform([clean_text(query)])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_idx = scores.argsort()[::-1][:top_n]
    results = []
    for i in top_idx:
        score = scores[i]
        if score > 0:
            row = activity_df.iloc[i]
            month = int(row["month"]) if pd.notna(row.get("month")) else None
            rating = round(float(row["rating"]), 1) if pd.notna(row.get("rating")) else None
            results.append((row["city"], row["activity"], month, rating, round(float(score), 4)))
    return results


class RecommendApp(QWidget):
    def __init__(self):
        super().__init__()
        self.vectorizer, self.tfidf_matrix, self.activity_df = load_model()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Japan Activity Recommender")
        self.setMinimumWidth(900)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 제목
        title = QLabel("Japan Activity Recommender")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 필터 영역 (도시 / 시기)
        filter_layout = QHBoxLayout()
        self.city_combo = QComboBox()
        self.city_combo.setFixedWidth(180)
        self.city_combo.setFont(QFont("Arial", 10))
        self.month_combo = QComboBox()
        self.month_combo.setFixedWidth(120)
        self.month_combo.setFont(QFont("Arial", 10))

        cities = ["전체"] + sorted(self.activity_df["city"].dropna().unique().tolist())
        self.city_combo.addItems(cities)

        valid_months = sorted(self.activity_df["month"].dropna().unique().tolist())
        self.month_combo.addItems(["전체"] + [f"{int(m)}월" for m in valid_months])

        filter_layout.addWidget(QLabel("도시:"))
        filter_layout.addWidget(self.city_combo)
        filter_layout.addSpacing(20)
        filter_layout.addWidget(QLabel("시기:"))
        filter_layout.addWidget(self.month_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.city_combo.currentIndexChanged.connect(self.apply_filter)
        self.month_combo.currentIndexChanged.connect(self.apply_filter)

        # 입력 영역
        input_layout = QHBoxLayout()
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("키워드 입력 (예: pottery craft, food cooking, temple history ...)")
        self.keyword_input.setFont(QFont("Arial", 11))
        self.keyword_input.returnPressed.connect(self.search)

        top_n_label = QLabel("결과 수:")
        self.top_n_spin = QSpinBox()
        self.top_n_spin.setRange(1, 20)
        self.top_n_spin.setValue(5)
        self.top_n_spin.setFixedWidth(60)

        search_btn = QPushButton("추천")
        search_btn.setFont(QFont("Arial", 11))
        search_btn.setFixedWidth(80)
        search_btn.clicked.connect(self.search)

        input_layout.addWidget(self.keyword_input)
        input_layout.addWidget(top_n_label)
        input_layout.addWidget(self.top_n_spin)
        input_layout.addWidget(search_btn)
        layout.addLayout(input_layout)

        # 결과 테이블
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["도시", "시기", "평점", "활동", "유사도"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Arial", 10))
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        # 상태 레이블
        self.status_label = QLabel(f"모델 로드 완료 | 활동 {len(self.activity_df)}개")
        self.status_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def get_filtered_df(self):
        filtered_df = self.activity_df.copy()
        selected_city = self.city_combo.currentText()
        selected_month = self.month_combo.currentText()
        if selected_city != "전체":
            filtered_df = filtered_df[filtered_df["city"] == selected_city]
        if selected_month != "전체":
            month_num = int(selected_month.replace("월", ""))
            filtered_df = filtered_df[filtered_df["month"] == month_num]
        return filtered_df

    def apply_filter(self):
        filtered_df = self.get_filtered_df().sort_values(
            ["month", "rating"], ascending=[True, False], na_position="last"
        ).reset_index(drop=True)
        self.table.setRowCount(len(filtered_df))
        for row_idx, (_, row) in enumerate(filtered_df.iterrows()):
            self._fill_row(row_idx, row["city"], row["activity"],
                           row.get("month"), row.get("rating"), None)
        self.table.resizeRowsToContents()
        self.status_label.setText(f"필터 결과: {len(filtered_df)}개 | 키워드 입력 시 유사도 검색")

    def search(self):
        query = self.keyword_input.text().strip()
        if not query:
            return

        # 한국어 입력 처리: 매핑 우선, 없으면 번역
        has_non_ascii = any(ord(c) > 127 for c in query)
        translated_query = query
        if has_non_ascii:
            mapped = " ".join(KEYWORD_MAP.get(w, "") for w in query.split())
            if mapped.strip():
                translated_query = mapped.strip()
            else:
                try:
                    translated_query = GoogleTranslator(source="auto", target="en").translate(query)
                except Exception:
                    pass
            self.status_label.setText(f"번역: '{query}' → '{translated_query}'")

        filtered_df = self.get_filtered_df()
        filtered_indices = filtered_df.index.tolist()
        filtered_matrix = self.tfidf_matrix[filtered_indices]

        if not translated_query:
            self.apply_filter()
            return

        top_n = self.top_n_spin.value()
        results = get_recommendations(translated_query, self.vectorizer, filtered_matrix, filtered_df.reset_index(drop=True), top_n)

        self.table.setRowCount(len(results))
        if not results:
            self.status_label.setText("결과 없음")
            return

        for row_idx, (city, activity, month, rating, score) in enumerate(results):
            self._fill_row(row_idx, city, activity, month, rating, score)

        self.table.resizeRowsToContents()
        self.status_label.setText(f"'{query}' 검색 결과: {len(results)}개")

    def _fill_row(self, row_idx, city, activity, month, rating, score):
        self.table.setItem(row_idx, 0, QTableWidgetItem(city))

        month_item = QTableWidgetItem(f"{int(month)}월" if month is not None and pd.notna(month) else "-")
        month_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_idx, 1, month_item)

        rating_item = QTableWidgetItem(f"{rating:.1f} ★" if rating is not None and pd.notna(rating) else "-")
        rating_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_idx, 2, rating_item)

        activity_ko = self.activity_df.loc[self.activity_df["activity"] == activity, "activity_ko"].values
        activity_ko = activity_ko[0] if len(activity_ko) > 0 else ""
        activity_text = f"{activity}\n{activity_ko}" if activity_ko else activity
        self.table.setItem(row_idx, 3, QTableWidgetItem(activity_text))

        score_text = str(score) if score is not None else "-"
        score_item = QTableWidgetItem(score_text)
        score_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row_idx, 4, score_item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecommendApp()
    window.show()
    sys.exit(app.exec_())
