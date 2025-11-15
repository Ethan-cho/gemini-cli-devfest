# Python 3.9 slim 버전을 기반 이미지로 사용
FROM python:3.9-slim

# ✅ 한글 폰트 설치 및 최종 검증
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends fonts-nanum fontconfig && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Matplotlib 폰트 캐시 강제 재빌드 (안전한 방식)
RUN python -c "import matplotlib.font_manager; matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf')"

COPY . .

# matplotlib 설정 디렉토리(권한 문제 방지용)
ENV MPLCONFIGDIR=/tmp/matplotlib

# 앱이 실행될 포트 노출
EXPOSE 8501

# Streamlit 앱 실행 (파일 감시 기능 비활성화)
CMD streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.fileWatcherType=none