import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import platform
import os

st.title("산/등산로 분석")

# =============================================================================
# 운영체제별 한글 폰트 설정
# =============================================================================
def set_korean_font():
    """운영체제에 따라 적절한 한글 폰트 설정"""
    system = platform.system()
    if system == 'Darwin':  # macOS
        plt.rcParams['font.family'] = 'AppleGothic'
    elif system == 'Windows':  # Windows
        plt.rcParams['font.family'] = 'Malgun Gothic'
    else:  # Linux
        plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.family'] = 'Malgun Gothic' # Windows: Malgun Gothic, Mac: AppleGothic

set_korean_font()
# =============================================================================
# 데이터 로드
# =============================================================================

# @st.cache_data: 데이터 캐싱 데코레이터
# 주요 특징:
# - 동일한 입력에 대해 결과를 메모리에 저장하여 재사용
# - 앱 재실행 시에도 캐시된 데이터 유지 (성능 향상)
@st.cache_data
def load_mountain_path():
    """100대명산 데이터셋 로드"""
    try:
        # 1. 현재 파일(pages/app.py)의 폴더 경로를 구함 -> .../프로젝트/pages
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. 상위 폴더(프로젝트 루트) 경로를 구함 -> .../프로젝트
        # (pages 폴더의 부모 폴더로 이동)
        root_dir = os.path.dirname(current_dir)
        
        # 3. 상위 폴더 기준에서 data 폴더 안의 파일 경로 생성
        file_path = os.path.join(root_dir, 'data', '100mountains.csv')
        
        # 4. 파일 읽기
        df = pd.read_csv(file_path)
        
        df.columns = ['코스명','산이름','유형설명','최고고도_m','누적상승_m','편도거리_km','총거리_km','예상시간_분','예상시간','출발_lat','출발_lon','도착_lat','도착_lon','난이도','세부난이도','난이도점수','관광인프라점수','주차장_접근성점수','정류장_접근성점수','코스수','가중치','매력종합점수','전망','힐링','사진','등산로','성취감','계절매력','특출매력','특출점수', 'Cluster']
        return df
        
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다.\n시도한 경로: {file_path}")
        return pd.DataFrame()

df = load_mountain_path()
if df.empty:
    st.stop()

# =============================================================================
# 데이터 개요
st.header("데이터 개요")

# 데이터 주요 메트릭 표시
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("산림청 선정 100대 명산", "100개")
with col2:
    st.metric("분석에 활용한 등산로 코스", f"{df['코스명'].nunique():,}개")
with col3:
    st.metric("수집한 리뷰 분석", "33,700+")
with col4:
    st.metric("수집한 관광 POI 데이터", "415,300+")

# =============================================================================
# 등산로 분석
st.divider()
st.header("1. 🥾 등산로 분석")

# 탭 3개 생성 (이모지로 시각적 구분)
tab1, tab2, tab3 = st.tabs(["💪 난이도", "📏 등산로 길이", "🏔️ 고도"])
with tab1:
    st.subheader("난이도 분포")
    
    # 데이터 집계
    count_df = df['난이도'].value_counts().reindex(['입문', '초급', '중급', '상급', '최상급', '초인', '신']).reset_index()
    count_df.columns = ['난이도', '개수']

    # Plotly 그래프 생성
    fig = px.bar(count_df, x='난이도', y='개수', 
                 text='개수',  # 막대 위에 숫자 표시
                 color='난이도', # 난이도별 색상 다르게
                 color_discrete_sequence=px.colors.qualitative.Pastel # 파스텔 톤 색상
                )
    
    # 디자인 다듬기
    fig.update_layout(showlegend=False) # 범례 숨김 (x축에 있으므로)
    
    st.plotly_chart(fig, use_container_width=True)
    # 데이터 정렬 (난이도 점수가 있다고 가정)
    # 만약 '난이도점수' 컬럼이 문자열이라면 숫자로 변환 필요: df['난이도점수'] = pd.to_numeric(df['난이도점수'])
    
    # TOP 5
    # 가장 어려운 TOP 5 (점수 내림차순)
    top_hard = df.sort_values(by='난이도점수', ascending=False).head(5)
    
    # 가장 쉬운 TOP 5 (점수 오름차순)
    top_easy = df.sort_values(by='난이도점수', ascending=True).head(5)

    # 화면 분할 (1:1 비율)
    col1, col2 = st.columns(2)

    # 함수: 리스트를 예쁘게 출력해주는 헬퍼 함수
    def show_top5_list(container, title, icon, data, color_theme):
        with container:
            # 컨테이너박스로 감싸서 카드처럼 보이게 만듦
            with st.container(border=True):
                st.markdown(f"#### {icon} {title}")
                
                for idx, (i, row) in enumerate(data.iterrows()):
                    rank = idx + 1
                    # 1,2,3등은 메달 이모지, 나머지는 숫자
                    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                    
                    # 텍스트 출력 (산이름 - 코스명)
                    st.markdown(
                        f"""
                        <div style='padding: 5px; border-radius: 5px; margin-bottom: 5px; background-color: rgba(255,255,255,0.05);'>
                            <span style='font-size: 1.1em;'>{medal} <b>{row['산이름']}</b></span>
                            <br>
                            <span style='color: gray; font-size: 0.9em;'>&nbsp;&nbsp;&nbsp;&nbsp;└ {row['코스명']} ({row['난이도']})</span>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )

    # 왼쪽 컬럼: 어려운 코스
    show_top5_list(col1, "가장 어려운 코스 TOP 5", "🔥", top_hard, "red")

    # 오른쪽 컬럼: 쉬운 코스
    show_top5_list(col2, "가장 쉬운 코스 TOP 5", "💧", top_easy, "blue")
with tab2:
    st.subheader("등산로 길이 분포")
    fig = px.histogram(df, x='총거리_km', nbins=20,
                       labels={'총거리_km': '총거리 (km)', 'count': '코스 개수'},
                       color_discrete_sequence=['teal'])
    
    st.plotly_chart(fig, use_container_width=True)
with tab3:
    st.subheader("등산로 고도 분포")
    fig = px.histogram(df, x='최고고도_m', nbins=20,
                       labels={'최고고도_m': '최고고도 (m)', 'count': '코스 개수'},
                       color_discrete_sequence=['orange'])
    
    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# 산 분석
st.divider()
st.header("2. 🏔️ 산 분석")
tab1, tab2 = st.tabs(["관광 인프라", "매력"])