import sys
import pandas as pd
import numpy as np
import re
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTableWidget, \
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView
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
        self.setWindowTitle("🌏 아시아 5개국 축제 자연어 추천 시스템 (NLP 유사도 매칭)")
        self.resize(1200, 700)

        main_layout = QVBoxLayout()

        # 상단 타이틀
        title_label = QLabel("🎯 TF-IDF & Cosine Similarity 기반 실시간 문장 유사도 추천 엔진")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        main_layout.addWidget(title_label)

        # 검색 영역
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("원하는 여행 테마를 한글로 입력하세요 (예: 온천, 쇼핑, 맛집, 깨끗, 친절, 기분 최고)")
        self.search_input.setStyleSheet(
            "padding: 10px; font-size: 11pt; border: 2px solid #bdc3c7; border-radius: 5px;")
        self.search_input.returnPressed.connect(self.search_festivals)

        search_btn = QPushButton("추천 축제 검색")
        search_btn.setStyleSheet(
            "padding: 10px 20px; font-size: 11pt; font-weight: bold; background-color: #27ae60; color: white; border-radius: 5px;")
        search_btn.clicked.connect(self.search_festivals)

        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_btn)
        main_layout.addLayout(search_layout)

        # 상태 안내 레이블
        self.status_label = QLabel("📊 시스템 준비 완료: 마스터 데이터베이스 로드 대기 중...")
        self.status_label.setStyleSheet("font-size: 10pt; color: #7f8c8d; margin-top: 5px; margin-bottom: 5px;")
        main_layout.addWidget(self.status_label)

        # 📊 결과 표 (유사도 컬럼 추가!)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)  # 6개에서 7개로 확장
        self.result_table.setHorizontalHeaderLabels(["추천 순위", "🔥 매칭 유사도", "국가", "도시", "시기", "행사명", "실제 유저 한국어 리뷰"])

        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 순위
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 유사도
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 국가
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 도시
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 시기
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 행사명
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 리뷰 (가장 넓게)

        self.result_table.setStyleSheet("font-size: 10pt; gridline-color: #dcdde1;")
        main_layout.addWidget(self.result_table)

        self.setLayout(main_layout)

    def load_dataset(self):
        csv_file = "asia_festivals_master.csv"
        try:
            self.df = pd.read_csv(csv_file)
            self.status_label.setText(f"✅ 1,080행 마스터 DB 로드 완료! 실시간 TF-IDF 자연어 연산 준비 완료.")

            # 초기 화면에는 유사도 0% 상태로 상위 15개 출력
            init_df = self.df.head(15).copy()
            init_df['similarity'] = 0.0
            self.update_table_display(init_df, show_rank=False)
        except Exception as e:
            QMessageBox.critical(self, "DB 로드 에러", f"'{csv_file}' 파일을 읽을 수 없습니다.\n에러 내용: {e}")

    def search_festivals(self):
        query = self.search_input.text().strip()

        if not query:
            init_df = self.df.head(15).copy()
            init_df['similarity'] = 0.0
            self.update_table_display(init_df, show_rank=False)
            self.status_label.setText(f"💡 검색어를 입력하시면 실시간 TF-IDF 유사도 연산이 시작됩니다.")
            return

        print(f"🧠 [NLP Engine] 입력 쿼리 코사인 유사도 분석 가동: '{query}'")

        # 🎯 [핵심 자연어 처리 알고리즘] TF-IDF 벡터화 및 코사인 유사도 계산
        # 1,080개 리뷰 텍스트 풀 분석
        corpus = self.df['review_ko'].astype(str).tolist()

        # 문맥을 숫자로 변환하는 벡터라이저 생성
        vectorizer = TfidfVectorizer(min_df=1)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # 유저가 입력한 검색어도 동일한 벡터 공간으로 변환
        query_vector = vectorizer.transform([query])

        # 1,080개 리뷰 전체와 유저 검색어 간의 코사인 유사도 실시간 계산
        sim_scores = cosine_similarity(query_vector, tfidf_matrix).flatten()

        # 원본 데이터 복사 후 유사도 점수 컬럼 결합
        search_df = self.df.copy()
        search_df['similarity'] = sim_scores

        # 📈 유사도 점수가 높은 순서대로 내림차순 정렬 (핵심 추천 로직)
        recommended_df = search_df[search_df['similarity'] > 0].sort_values(by='similarity', ascending=False)

        # 표 업데이트 및 상위 매칭 결과 출력
        self.update_table_display(recommended_df)

        if len(recommended_df) > 0:
            max_sim = recommended_df['similarity'].iloc[0] * 100
            self.status_label.setText(f"🎯 NLP 결과: '{query}'와 가장 잘 맞는 추천 활동을 찾았습니다. (최고 유사도: {max_sim:.1f}%)")
        else:
            self.status_label.setText(f"❓ '{query}'와 매칭되는 텍스트 유사도를 찾지 못했습니다. 다른 키워드로 검색해 보세요.")

    def update_table_display(self, display_df, show_rank=True):
        self.result_table.setRowCount(0)
        self.result_table.setRowCount(len(display_df))

        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            # 1. 추천 순위 매기기
            rank_str = f"제 {row_idx + 1}위" if show_rank else "-"
            self.result_table.setItem(row_idx, 0, QTableWidgetItem(rank_str))

            # 2. 🔥 매칭 유사도 점수출력 (퍼센트 포맷 가공)
            sim_percent = row['similarity'] * 100
            sim_item = QTableWidgetItem(f"{sim_percent:.1f} %")

            # 유사도가 높은 행은 시각적으로 돋보이게 색상 텍스트 효과 추가
            if sim_percent > 30:
                sim_item.setForeground(Qt.blue)

            self.result_table.setItem(row_idx, 1, sim_item)

            # 3. 기본 정보 세팅
            self.result_table.setItem(row_idx, 2, QTableWidgetItem(str(row['country'])))
            self.result_table.setItem(row_idx, 3, QTableWidgetItem(str(row['city'])))
            self.result_table.setItem(row_idx, 4, QTableWidgetItem(str(row['month'])))
            self.result_table.setItem(row_idx, 5, QTableWidgetItem(str(row['title'])))

            # 4. 한국어 번역 리뷰 셀 삽입
            review_item = QTableWidgetItem(str(row['review_ko']))
            review_item.setToolTip(str(row['review_ko']))
            self.result_table.setItem(row_idx, 6, review_item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = TourismRecommendApp()
    ex.show()
    sys.exit(app.exec_())