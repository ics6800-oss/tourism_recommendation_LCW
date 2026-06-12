import sys
import pandas as pd
import numpy as np
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QComboBox
from PyQt5.QtCore import Qt

# 🧠 자연어 처리 연산용 사이킷런 라이브러리
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class TourismRecommendApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_dataset()

    def initUI(self):
        self.setWindowTitle("🌏 아시아 5개국 축제 맞춤형 추천 시스템")
        self.resize(1200, 800)

        main_layout = QVBoxLayout()

        # 상단 타이틀
        title_label = QLabel("🎯 여행 날짜와 지역을 선택하고 테마를 검색하세요!")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # 📍 필터 영역 (지역 및 시기 선택)
        filter_layout = QHBoxLayout()

        self.city_combo = QComboBox()
        self.city_combo.setFixedWidth(200)
        self.city_combo.setStyleSheet("padding: 8px; font-size: 11pt; border: 1px solid #bdc3c7; border-radius: 5px;")

        self.month_combo = QComboBox()
        self.month_combo.setFixedWidth(150)
        self.month_combo.setStyleSheet("padding: 8px; font-size: 11pt; border: 1px solid #bdc3c7; border-radius: 5px;")

        filter_layout.addWidget(QLabel("📍 지역(도시):"))
        filter_layout.addWidget(self.city_combo)
        filter_layout.addSpacing(30)
        filter_layout.addWidget(QLabel("📅 여행 시기:"))
        filter_layout.addWidget(self.month_combo)
        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # 🔍 검색 영역
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("원하는 여행 테마를 입력하세요 (예: 온천, 쇼핑, 맛집, 역사, 힐링, 애니메이션...)")
        self.search_input.setStyleSheet(
            "padding: 12px; font-size: 11pt; border: 2px solid #3498db; border-radius: 5px;")
        self.search_input.returnPressed.connect(self.search_festivals)

        search_btn = QPushButton("맞춤 추천 검색")
        search_btn.setStyleSheet(
            "padding: 12px 25px; font-size: 11pt; font-weight: bold; background-color: #3498db; color: white; border-radius: 5px;")
        search_btn.clicked.connect(self.search_festivals)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)

        # 상태 안내 레이블
        self.status_label = QLabel("📊 시스템 준비 완료: 데이터베이스 로딩 중...")
        self.status_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; margin-top: 5px; margin-bottom: 5px;")
        main_layout.addWidget(self.status_label)

        # 📊 결과 표
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)
        self.result_table.setHorizontalHeaderLabels(["추천 순위", "🔥 매칭 유사도", "국가", "도시", "시기", "행사명", "실제 유저 한국어 리뷰"])

        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        self.result_table.setStyleSheet("font-size: 10pt; gridline-color: #dcdde1;")
        self.result_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.result_table)

        self.setLayout(main_layout)

    def load_dataset(self):
        csv_file = "asia_festivals_master.csv"
        try:
            self.df = pd.read_csv(csv_file)
            
            # 콤보박스 데이터 동적 채우기
            cities = ["전체"] + sorted(self.df['city'].unique().tolist())
            self.city_combo.addItems(cities)
            
            # 월 데이터 정렬하여 채우기 (1월 ~ 12월)
            months = sorted(self.df['month'].unique().tolist(), key=lambda x: int(x.replace('월', '')))
            self.month_combo.addItems(["전체"] + months)

            self.status_label.setText(f"✅ {len(self.df)}행 데이터 로드 완료! 지역과 시기를 선택하고 검색해 보세요.")

            # 초기 화면 상위 15개
            init_df = self.df.head(15).copy()
            init_df['similarity'] = 0.0
            self.update_table_display(init_df, show_rank=False)
        except Exception as e:
            QMessageBox.critical(self, "DB 로드 에러", f"'{csv_file}' 파일을 읽을 수 없습니다.\n에러 내용: {e}")

    def search_festivals(self):
        query = self.search_input.text().strip()
        selected_city = self.city_combo.currentText()
        selected_month = self.month_combo.currentText()

        # 1. 날짜와 지역 필터링 적용 (가장 먼저 수행)
        filtered_df = self.df.copy()
        if selected_city != "전체":
            filtered_df = filtered_df[filtered_df['city'] == selected_city]
        if selected_month != "전체":
            filtered_df = filtered_df[filtered_df['month'] == selected_month]

        if filtered_df.empty:
            self.status_label.setText(f"❌ '{selected_city}', '{selected_month}' 조건에 맞는 데이터가 없습니다.")
            self.result_table.setRowCount(0)
            return

        # 검색어가 없을 경우 필터링된 결과만 보여줌
        if not query:
            filtered_df['similarity'] = 0.0
            self.update_table_display(filtered_df, show_rank=False)
            self.status_label.setText(f"💡 '{selected_city}' - '{selected_month}' 전체 목록입니다. 키워드를 입력하면 정확도가 높아집니다.")
            return

        print(f"🧠 [NLP Engine] 필터 적용 후 유사도 분석: '{selected_city}', '{selected_month}', 키워드: '{query}'")

        # 2. 텍스트 중복 문제 해결을 위해 검색 대상 텍스트 결합 (행사명 + 설명 + 리뷰)
        # 리뷰가 똑같더라도 행사명과 설명이 다르면 유사도 점수가 다르게 계산됩니다.
        filtered_df['combined_text'] = (
            filtered_df['title'] + " " + 
            filtered_df['description'] + " " + 
            filtered_df['review_ko']
        )
        
        corpus = filtered_df['combined_text'].astype(str).tolist()

        # TF-IDF 벡터화
        vectorizer = TfidfVectorizer(min_df=1)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # 쿼리 벡터화 및 코사인 유사도 계산
        query_vector = vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()

        filtered_df['similarity'] = sim_scores

        # 유사도가 0보다 큰 결과만 추출 및 정렬
        recommended_df = filtered_df[filtered_df['similarity'] > 0].sort_values(by='similarity', ascending=False)

        if len(recommended_df) > 0:
            self.update_table_display(recommended_df)
            max_sim = recommended_df['similarity'].iloc[0] * 100
            self.status_label.setText(f"🎯 추천 결과: '{query}'와 가장 잘 맞는 활동을 찾았습니다. (최고 유사도: {max_sim:.1f}%)")
        else:
            self.update_table_display(filtered_df.head(0)) # 결과 없음
            self.status_label.setText(f"❓ 필터링된 범위 내에서 '{query}'와 관련된 결과가 없습니다. 다른 키워드를 입력해 보세요.")

    def update_table_display(self, display_df, show_rank=True):
        self.result_table.setRowCount(0)
        self.result_table.setRowCount(len(display_df))

        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            # 1. 추천 순위
            rank_str = f"제 {row_idx + 1}위" if show_rank else "-"
            self.result_table.setItem(row_idx, 0, QTableWidgetItem(rank_str))

            # 2. 매칭 유사도
            sim_percent = row['similarity'] * 100
            sim_item = QTableWidgetItem(f"{sim_percent:.1f} %")
            if sim_percent > 30:
                sim_item.setForeground(Qt.blue)
            self.result_table.setItem(row_idx, 1, sim_item)

            # 3. 정보 세팅
            self.result_table.setItem(row_idx, 2, QTableWidgetItem(str(row['country'])))
            self.result_table.setItem(row_idx, 3, QTableWidgetItem(str(row['city'])))
            self.result_table.setItem(row_idx, 4, QTableWidgetItem(str(row['month'])))
            self.result_table.setItem(row_idx, 5, QTableWidgetItem(str(row['title'])))

            # 4. 리뷰
            review_item = QTableWidgetItem(str(row['review_ko']))
            review_item.setToolTip(str(row['review_ko']))
            self.result_table.setItem(row_idx, 6, review_item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TourismRecommendApp()
    ex.show()
    sys.exit(app.exec_())
