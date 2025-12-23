import streamlit as st
import pandas as pd
import os

# -----------------------------------------------------------------------------
# 0. 데이터 로드 및 초기 설정
# -----------------------------------------------------------------------------
@st.cache_data
def load_mountain_path():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        file_path = os.path.join(root_dir, 'data', '100mountains_dashboard.csv')
        
        df = pd.read_csv(file_path)
        
        full_columns = [
            '코스명','산이름','유형설명','최고고도_m','누적상승_m','편도거리_km','총거리_km',
            '예상시간_분','예상시간','출발_lat','출발_lon','도착_lat','도착_lon',
            '난이도','세부난이도','난이도점수','관광인프라점수','주차장_접근성점수','정류장_접근성점수',
            '코스수','가중치','매력종합점수','전망','힐링','사진','등산로','성취감',
            '계절매력','특출매력','특출점수','Cluster',
            '주차장거리_m', '정류장거리_m' 
        ]
        
        # 컬럼 개수 맞추기 (CSV 파일 컬럼 수에 따라 유동적으로 처리)
        if len(df.columns) == len(full_columns):
            df.columns = full_columns
        else:
            # 개수가 안 맞으면 일단 원본 컬럼 사용 후, 필요한 컬럼만 있는지 확인
            st.warning(f"컬럼 개수 불일치! (CSV: {len(df.columns)}개 vs 코드: {len(full_columns)}개). 데이터 파일의 컬럼 순서를 확인해주세요.")
            # 강제로 할당하지 않고 진행 (파일명이 맞다면 에러가 날 수 있음)
        
        # [수정] 숫자로 변환할 컬럼에 '주차장거리_m' 추가
        numeric_cols = ['난이도점수', '관광인프라점수', '주차장_접근성점수', '매력종합점수', '총거리_km', '주차장거리_m']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
        
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()

df = load_mountain_path()
if df.empty:
    st.stop()

st.header("🔍 맞춤 등산로 검색")

# 난이도 등급 순서 정의
difficulty_levels = ['입문', '초급', '중급', '상급', '최상급', '초인', '신']

# -----------------------------------------------------------------------------
# 1. 세션 상태 초기화
# -----------------------------------------------------------------------------
if 'diff_slider' not in st.session_state:
    st.session_state.diff_slider = ('입문', '신')
if 'infra_slider' not in st.session_state:
    st.session_state.infra_slider = (0.0, 10.0)
# [수정] 주차장 슬라이더 초기값 변경 (거리이므로 넉넉하게 2000m)
if 'park_dist_slider' not in st.session_state:
    st.session_state.park_dist_slider = 2000

# -----------------------------------------------------------------------------
# 2. 콜백 함수: 프리셋 버튼 클릭 시 설정 변경
# -----------------------------------------------------------------------------
def set_search_condition():
    selection = st.session_state.type_selection
    
    if selection == "유형 1 (하드코어)":
        st.session_state['diff_slider'] = ('상급', '신')
        st.session_state['infra_slider'] = (0.0, 10.0)
        # 하드코어: 주차장 거리 상관없음 (최대값)
        st.session_state['park_dist_slider'] = 2000
        
    elif selection == "유형 2 (초보자 관광)":
        st.session_state['diff_slider'] = ('입문', '초급')
        st.session_state['infra_slider'] = (7.0, 10.0)
        # 초보자: 1km 이내
        st.session_state['park_dist_slider'] = 1000
        
    elif selection == "유형 3 (접근성 균형)":
        st.session_state['diff_slider'] = ('초급', '상급')
        st.session_state['infra_slider'] = (4.0, 10.0)
        # 접근성 중시: 500m 이내
        st.session_state['park_dist_slider'] = 500

# -----------------------------------------------------------------------------
# 3. UI 구성
# -----------------------------------------------------------------------------
st.markdown("##### 선호하는 등산 유형을 선택해주세요")

st.pills(
    "등산 유형",
    options=["유형 1 (하드코어)", "유형 2 (초보자 관광)", "유형 3 (접근성 균형)"],
    selection_mode="single",
    key="type_selection",
    on_change=set_search_condition
)

st.divider()

st.markdown("##### 세부 조건을 조절해보세요")

col1, col2, col3 = st.columns(3)

with col1:
    diff_val = st.select_slider(
        "산행 난이도 (구간 선택)",
        options=difficulty_levels,
        value=st.session_state['diff_slider'],
        key="diff_slider" 
    )

with col2:
    infra_val = st.slider(
        "관광 인프라 (점수)",
        min_value=0.0, max_value=10.0,
        value=st.session_state['infra_slider'],
        key="infra_slider"
    )

with col3:
    # [수정] 주차장 거리 슬라이더 (0m ~ 2000m)
    park_dist_val = st.slider(
        "주차장 거리 (m 이내)",
        min_value=0, max_value=2000,
        step=100, # 100m 단위로 조절
        value=st.session_state['park_dist_slider'],
        key="park_dist_slider"
    )

# -----------------------------------------------------------------------------
# 4. 데이터 필터링
# -----------------------------------------------------------------------------
try:
    start_idx = difficulty_levels.index(diff_val[0])
    end_idx = difficulty_levels.index(diff_val[1])
    selected_levels = difficulty_levels[start_idx : end_idx + 1]

    filtered_df = df[
        (df['난이도'].isin(selected_levels)) &
        (df['관광인프라점수'] >= infra_val[0]) & (df['관광인프라점수'] <= infra_val[1]) &
        (df['주차장거리_m'] <= park_dist_val) 
    ]
except Exception as e:
    st.error(f"필터링 오류 발생: {e}")
    filtered_df = pd.DataFrame()

# -----------------------------------------------------------------------------
# 5. 결과 출력
# -----------------------------------------------------------------------------
st.write(f"검색 결과: **{len(filtered_df)}**개의 코스를 찾았습니다.")

# [수정] 보여줄 컬럼에 '주차장거리_m' 추가
display_cols = ['산이름', '코스명', '난이도', '난이도점수', '관광인프라점수', '주차장거리_m', '총거리_km', '예상시간']

if not filtered_df.empty:
    st.dataframe(
        filtered_df.sort_values('매력종합점수', ascending=False)[display_cols],
        hide_index=True,
        use_container_width=True,
        column_config={
            "난이도점수": st.column_config.NumberColumn("점수", format="%.1f"),
            "관광인프라점수": st.column_config.ProgressColumn("인프라", format="%.1f", min_value=0, max_value=10),
            "주차장거리_m": st.column_config.NumberColumn("주차장 거리", format="%d m"),
            "총거리_km": st.column_config.NumberColumn("거리(km)", format="%.1f km")
        }
    )
else:
    st.info("조건에 맞는 등산로가 없습니다. 조건을 변경해보세요.")