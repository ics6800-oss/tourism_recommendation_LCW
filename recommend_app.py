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
    QTableWidgetItem, QHeaderView, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

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
            results.append((row["city"], row["activity"], round(float(score), 4)))
    return results


class RecommendApp(QWidget):
    def __init__(self):
        super().__init__()
        self.vectorizer, self.tfidf_matrix, self.activity_df = load_model()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Japan Activity Recommender")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # 제목
        title = QLabel("Japan Activity Recommender")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

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
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["도시", "활동", "유사도"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setFont(QFont("Arial", 10))
        layout.addWidget(self.table)

        # 상태 레이블
        self.status_label = QLabel(f"모델 로드 완료 | 활동 {len(self.activity_df)}개")
        self.status_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

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

        top_n = self.top_n_spin.value()
        results = get_recommendations(translated_query, self.vectorizer, self.tfidf_matrix, self.activity_df, top_n)

        self.table.setRowCount(len(results))
        if not results:
            self.status_label.setText("결과 없음")
            return

        for row_idx, (city, activity, score) in enumerate(results):
            self.table.setItem(row_idx, 0, QTableWidgetItem(city))
            self.table.setItem(row_idx, 1, QTableWidgetItem(activity))
            score_item = QTableWidgetItem(str(score))
            score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 2, score_item)

        self.status_label.setText(f"'{query}' 검색 결과: {len(results)}개")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecommendApp()
    window.show()
    sys.exit(app.exec_())
