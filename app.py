import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import datetime
import matplotlib.pyplot as plt

# 한글 폰트 설정
plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False


# Streamlit 앱 페이지 설정
st.set_page_config(page_title="국토교통부 실거래가 조회 서비스", layout="wide")

# Streamlit 앱 제목 설정
st.title('국토교통부 아파트 실거래가 조회 서비스')
st.caption("국토교통부 실거래가 공개 API를 이용하여 아파트 실거래가 정보를 조회합니다.")


# --- 함수 정의 ---

@st.cache_data
def get_api_data(service_key, lawd_cd, deal_ymd):
    """국토교통부 실거래가 API를 호출하여 데이터를 가져오는 함수"""
    
    # API 엔드포인트 및 파라미터 설정
    endpoint = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {
        'serviceKey': service_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'numOfRows': '1000' # 한 번에 1000개까지 가져오도록 설정
    }
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        
        # XML 응답 파싱
        root = ET.fromstring(response.content)
        
        # 결과 코드가 정상이 아닌 경우
        result_code = root.find('header/resultCode').text
        if result_code != '00':
            result_msg = root.find('header/resultMsg').text
            st.error(f"API 호출 실패: {result_msg} (코드: {result_code})")
            return None
            
        # item들을 DataFrame으로 변환
        items = []
        for item in root.findall('body/items/item'):
            item_data = {child.tag: child.text for child in item}
            items.append(item_data)
            
        if not items:
            st.warning("해당 조건에 맞는 데이터가 없습니다.")
            return None
            
        df = pd.DataFrame(items)
        return df
        
    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 중 오류가 발생했습니다: {e}")
        return None
    except ET.ParseError as e:
        st.error(f"XML 파싱 중 오류가 발생했습니다. API 응답을 확인해주세요: {e}")
        st.text(response.text) # 실제 응답 내용 출력
        return None


# --- Streamlit UI 구성 ---

# 사용자 입력 필드 (사이드바)
with st.sidebar:
    st.header("조회 조건 입력")
    service_key_input = st.text_input("API 서비스 키", type="password", help="공공데이터포털에서 발급받은 API 서비스 키를 입력하세요.")

    # 법정동 코드 예시 (자주 사용하는 지역)
    lawd_cd_options = {
        "강남구": "11680",
        "서초구": "11650",
        "송파구": "11710",
        "용산구": "11170",
        "성동구": "11200",
        "마포구": "11440"
    }
    selected_district_name = st.selectbox("지역(구) 선택", ["직접 입력"] + list(lawd_cd_options.keys()))

    if selected_district_name == "직접 입력":
        lawd_cd_input = st.text_input("법정동 코드 5자리", placeholder="예: 11680")
        st.markdown("[법정동 코드 검색 (외부 링크)](https://www.code.go.kr/stdcode/regCodeL.do)")
    else:
        lawd_cd_input = lawd_cd_options[selected_district_name]

    deal_date = st.date_input("계약년월 선택", datetime.date(2023, 10))
    deal_ymd_input = deal_date.strftime("%Y%m")

    search_button = st.button('실거래가 조회', type="primary")


# 메인 화면
if search_button:
    if not service_key_input:
        st.warning("API 서비스 키를 입력해주세요.")
    elif not lawd_cd_input:
        st.warning("법정동 코드를 입력해주세요.")
    else:
        with st.spinner('데이터를 가져오는 중입니다...'):
            # API 호출
            df = get_api_data(service_key_input, lawd_cd_input, deal_ymd_input)
            
            if df is not None:
                display_district_name = selected_district_name if selected_district_name != "직접 입력" else f"코드: {lawd_cd_input}"
                st.success(f"**{display_district_name}**의 **{deal_ymd_input[:4]}년 {deal_ymd_input[4:]}월** 실거래가 정보입니다.")
                
                # 데이터 전처리 및 표시
                try:
                    # 필요한 컬럼 선택 및 이름 변경
                    display_columns = {
                        '아파트': '아파트', '법정동': '법정동', '거래금액': '거래금액(만원)',
                        '전용면적': '전용면적(㎡)', '층': '층', '건축년도': '건축년도',
                        '년': '거래년', '월': '거래월', '일': '거래일'
                    }
                    df_display = df[list(display_columns.keys())].copy()
                    df_display.rename(columns=display_columns, inplace=True)

                    # 데이터 타입 변환
                    numeric_cols = ['전용면적(㎡)', '층', '건축년도']
                    for col in numeric_cols:
                        df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
                    
                    df_display['거래금액(만원)'] = df_display['거래금액(만원)'].str.replace(',', '').str.strip().astype(int)

                    # 결과 표시를 위한 탭 생성
                    tab1, tab2 = st.tabs(["데이터 표", "요약 및 시각화"])

                    with tab1:
                        st.dataframe(df_display)

                    with tab2:
                        st.subheader("기본 통계")
                        
                        # 거래 건수, 평균/최고/최저가 표시
                        total_deals = len(df_display)
                        avg_price = df_display['거래금액(만원)'].mean()
                        max_price = df_display['거래금액(만원)'].max()
                        min_price = df_display['거래금액(만원)'].min()
                        
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("총 거래 건수", f"{total_deals} 건")
                        col2.metric("평균 거래가", f"{avg_price:,.0f} 만원")
                        col3.metric("최고 거래가", f"{max_price:,.0f} 만원")
                        col4.metric("최저 거래가", f"{min_price:,.0f} 만원")
                        
                        st.divider()
                        
                        st.subheader("시각화")
                        
                        # 거래금액 분포 히스토그램
                        st.write("#### 거래금액 분포 (히스토그램)")
                        fig, ax = plt.subplots()
                        ax.hist(df_display['거래금액(만원)'], bins=30, edgecolor='black')
                        ax.set_xlabel("거래금액 (만원)")
                        ax.set_ylabel("거래 건수")
                        st.pyplot(fig)
                        
                        # 전용면적 대비 거래금액 산점도
                        st.write("#### 전용면적 대비 거래금액 (산점도)")
                        fig, ax = plt.subplots()
                        ax.scatter(df_display['전용면적(㎡)'], df_display['거래금액(만원)'], alpha=0.5)
                        ax.set_xlabel("전용면적 (㎡)")
                        ax.set_ylabel("거래금액 (만원)")
                        ax.grid(True)
                        st.pyplot(fig)

                except KeyError as e:
                    st.error(f"데이터 처리 중 오류가 발생했습니다. 필요한 컬럼({e})이 응답에 없습니다.")
                    st.dataframe(df) # 원본 데이터프레임 출력
                except Exception as e:
                    st.error(f"데이터를 처리하는 도중 오류가 발생했습니다: {e}")
                    st.dataframe(df) # 원본 데이터프레임 출력
