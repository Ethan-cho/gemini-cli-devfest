import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
from dotenv import load_dotenv
import time

# --- Matplotlib 한글 폰트 설정 (최종 제안된 방식) ---
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic-Regular.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicCoding.ttf",
    "/usr/share/fonts/truetype/nanum/NanumMyeongjo.ttf",
]

font_found = False
for path in FONT_CANDIDATES:
    if os.path.exists(path):
        fm.fontManager.addfont(path)
        prop = fm.FontProperties(fname=path)
        plt.rcParams["font.family"] = prop.get_name()
        font_found = True
        break

if not font_found:
    print("⚠️ 한글 폰트를 찾지 못했습니다.")
plt.rcParams["axes.unicode_minus"] = False

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 앱 페이지 설정
st.set_page_config(page_title="국토교통부 실거래가 조회 서비스", layout="wide")

# --- 함수 정의 ---
@st.cache_data(ttl=3600)
def get_api_data(service_key, lawd_cd, deal_ymd):
    endpoint = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    params = {"serviceKey": service_key, "LAWD_CD": lawd_cd, "DEAL_YMD": deal_ymd, "pageNo": "1", "numOfRows": "1000"}
    try:
        response = requests.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        if root.findtext("header/resultCode") not in ('00', '000'): return None
        items = [ {child.tag: (child.text or "").strip() for child in item} for item in root.findall(".//item") ]
        return pd.DataFrame(items) if items else None
    except (requests.exceptions.RequestException, ET.ParseError):
        return None

def format_price(price_in_man):
    eok = int(price_in_man // 10000)
    man = int(price_in_man % 10000)
    if eok > 0 and man > 0: return f"{eok}억 {man: ,}만원"
    elif eok > 0: return f"{eok}억"
    else: return f"{man: ,}만원"

def to_pyeong(area_sqm):
    return area_sqm * 0.3025

# --- 세션 상태 초기화 ---
if 'show_results' not in st.session_state: st.session_state.show_results = False
if 'df' not in st.session_state: st.session_state.df = None

# --- UI 구성 ---
st.title('국토교통부 아파트 실거래가 조회 서비스')
st.caption("국토교통부 실거래가 공개 API를 이용하여 아파트 실거래가 정보를 조회합니다.")

with st.sidebar:
    st.header("조회 조건 입력")
    service_key_input = os.getenv("DATA_API_KEY") or st.text_input("API 서비스 키", type="password")
    if os.getenv("DATA_API_KEY"): st.success("API 키를 성공적으로 로드했습니다.")
    
    lawd_cd_options = {"강남구": "11680", "서초구": "11650", "송파구": "11710", "용산구": "11170", "성동구": "11200", "마포구": "11440", "성남시 분당구": "41135", "성남시 수정구": "41131", "성남시 중원구": "41133"}
    selected_district_name = st.selectbox("지역(구) 선택", list(lawd_cd_options.keys()))
    lawd_cd_input = lawd_cd_options[selected_district_name]

    current_year = datetime.datetime.now().year
    selected_year = st.number_input("조회 년도", min_value=2006, max_value=current_year, value=2025)
    selected_month = st.selectbox("조회 월", list(range(1, 13)), index=9)
    deal_ymd_input = f"{selected_year}{selected_month:02d}"

    if st.button('실거래가 조회', type="primary"):
        if not service_key_input: st.warning("API 서비스 키를 입력해주세요.")
        else:
            with st.spinner('데이터를 가져오는 중입니다...'):
                st.session_state.df = get_api_data(service_key_input, lawd_cd_input, deal_ymd_input)
            st.session_state.show_results = True

# --- 메인 화면 로직 ---
if st.session_state.show_results:
    df = st.session_state.df
    if df is not None:
        st.success(f"**{selected_district_name}**의 **{deal_ymd_input[:4]}년 {deal_ymd_input[4:]}월** 실거래가 정보입니다.")
        
        try:
            display_columns = {'aptNm': '아파트', 'umdNm': '법정동', 'dealAmount': '거래금액(만원)', 'excluUseAr': '전용면적(㎡)', 'floor': '층', 'buildYear': '건축년도', 'dealYear': '거래년', 'dealMonth': '거래월', 'dealDay': '거래일'}
            df_display = df[list(display_columns.keys())].copy()
            df_display.rename(columns=display_columns, inplace=True)

            for col in ['전용면적(㎡)', '층', '건축년도']: df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
            df_display['거래금액(만원)'] = df_display['거래금액(만원)'].str.replace(',', '').str.strip().astype(int)

            tab1, tab2 = st.tabs(["데이터 표", "요약 및 시각화"])
            with tab1: st.dataframe(df_display)
            with tab2:
                st.subheader("요약 통계")
                max_price_row = df_display.loc[df_display['거래금액(만원)'].idxmax()]
                min_price_row = df_display.loc[df_display['거래금액(만원)'].idxmin()]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("총 거래 건수", f"{len(df_display)} 건")
                col2.metric("평균 거래가", format_price(df_display['거래금액(만원)'].mean()))
                col3.metric("최고 거래가", format_price(df_display['거래금액(만원)'].max()))
                col4.metric("최저 거래가", format_price(df_display['거래금액(만원)'].min()))
                
                st.divider()
                st.write("##### 주요 거래 정보")
                col1, col2 = st.columns(2)
                with col1: st.info(f"**최고가 아파트:** {max_price_row['아파트']}  \n**거래 금액:** {format_price(max_price_row['거래금액(만원)'])}  \n**전용 면적:** {max_price_row['전용면적(㎡)']} ㎡ ({to_pyeong(max_price_row['전용면적(㎡)']):.2f} 평)")
                with col2: st.info(f"**최저가 아파트:** {min_price_row['아파트']}  \n**거래 금액:** {format_price(min_price_row['거래금액(만원)'])}  \n**전용 면적:** {min_price_row['전용면적(㎡)']} ㎡ ({to_pyeong(min_price_row['전용면적(㎡)']):.2f} 평)")
                
                st.divider()
                st.subheader("시각화")
                st.write("#### 거래금액 분포 (히스토그램)")
                fig, ax = plt.subplots()
                ax.hist(df_display['거래금액(만원)'], bins=30, edgecolor='black')
                ax.set_xlabel("거래금액 (만원)")
                ax.set_ylabel("거래 건수")
                st.pyplot(fig)
                
                st.write("#### 전용면적 대비 거래금액 (산점도)")
                fig, ax = plt.subplots()
                ax.scatter(df_display['전용면적(㎡)'], df_display['거래금액(만원)'], alpha=0.5)
                ax.set_xlabel("전용면적 (㎡)")
                ax.set_ylabel("거래금액 (만원)")
                ax.grid(True)
                st.pyplot(fig)
            
            st.divider()
            st.subheader("아파트별 최근 3년 시세 조회")
            unique_apts = sorted(df_display['아파트'].unique())
            selected_apt = st.selectbox("시세를 조회할 아파트를 선택하세요.", options=[""] + unique_apts)

            if selected_apt:
                all_dfs = []
                progress_bar = st.progress(0, text="과거 데이터 조회 중...")
                with st.spinner(f"'{selected_apt}'의 최근 3년치 데이터를 가져오는 중..."):
                    for i in range(36):
                        target_date = datetime.date(selected_year, selected_month, 1) - pd.DateOffset(months=i)
                        yyyymm = target_date.strftime("%Y%m")
                        monthly_df = get_api_data(service_key_input, lawd_cd_input, yyyymm)
                        if monthly_df is not None: all_dfs.append(monthly_df)
                        progress_bar.progress((i + 1) / 36, text=f"{yyyymm} 데이터 조회 완료")
                        time.sleep(0.1)
                progress_bar.empty()

                if all_dfs:
                    history_df = pd.concat(all_dfs, ignore_index=True)
                    apt_history_df = history_df[history_df['aptNm'] == selected_apt].copy()
                    if not apt_history_df.empty:
                        apt_history_df['거래일'] = pd.to_datetime(apt_history_df['dealYear'] + '-' + apt_history_df['dealMonth'] + '-' + apt_history_df['dealDay'])
                        apt_history_df['dealAmount'] = apt_history_df['dealAmount'].str.replace(',', '').str.strip().astype(int)
                        apt_history_df.sort_values('거래일', inplace=True)

                        st.write(f"#### '{selected_apt}' 최근 3년 실거래가 추이")
                        fig, ax = plt.subplots(figsize=(12, 6))
                        ax.plot(apt_history_df['거래일'], apt_history_df['dealAmount'], marker='o', linestyle='-')
                        ax.set_xlabel("거래일")
                        ax.set_ylabel("거래금액 (만원)")
                        ax.set_title(f"{selected_apt} 시세 추이")
                        ax.grid(True)
                        plt.xticks(rotation=45)
                        st.pyplot(fig)
                    else: st.warning(f"'{selected_apt}'에 대한 지난 3년간의 데이터가 없습니다.")
                else: st.warning(f"'{selected_apt}'에 대한 지난 3년간의 데이터가 없습니다.")

        except Exception as e:
            st.error(f"데이터를 처리하는 도중 오류가 발생했습니다: {e}")
    else:
        st.info("조회된 데이터가 없습니다. 다른 날짜나 지역을 선택해보세요.")
else:
    st.info("좌측 사이드바에서 조회 조건을 선택한 후 '실거래가 조회' 버튼을 눌러주세요.")
