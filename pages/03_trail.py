import streamlit as st
import pandas as pd
import os
import gpxpy
import folium
from streamlit_folium import st_folium

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
        
        # [수정] 주차장명, 정류장명 컬럼이 포함된 리스트
        full_columns = [
            '코스명', '산이름', '유형설명', '최고고도_m', '누적상승_m', '편도거리_km', '총거리_km', '예상시간_분', '예상시간', 
            '출발_lat', '출발_lon', '도착_lat', '도착_lon', '난이도', '세부난이도', '난이도점수',
            '관광인프라점수','주차장_접근성점수','정류장_접근성점수','코스수','가중치','매력종합점수',
            '전망','힐링','사진','등산로','성취감','계절매력','특출매력','특출점수','Cluster',
            '주차장거리_m','정류장거리_m','위치', '주차장명', '정류장명'
        ]
        
        # 컬럼 개수 유연하게 맞추기
        if len(df.columns) == len(full_columns):
            df.columns = full_columns
        elif len(df.columns) >= 33: 
             df.columns = full_columns[:len(df.columns)]
        
        # 숫자 변환 및 결측치 처리
        numeric_cols = ['난이도점수', '관광인프라점수', '매력종합점수', '주차장거리_m', '정류장거리_m', '총거리_km', '최고고도_m']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 문자열 결측치 처리 (주차장명 등이 없을 때 '-'로 표시)
        str_cols = ['주차장명', '정류장명', '위치']
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].fillna("-")
            
        return df
        
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()

df = load_mountain_path()
if df.empty:
    st.stop()

st.header("🔍 맞춤 등산로 검색")

difficulty_levels = ['입문', '초급', '중급', '상급', '최상급', '초인', '신']

# -----------------------------------------------------------------------------
# 1. 세션 상태 초기화
# -----------------------------------------------------------------------------
if 'diff_slider' not in st.session_state:
    st.session_state.diff_slider = ('입문', '신')
if 'infra_slider' not in st.session_state:
    st.session_state.infra_slider = (0.0, 10.0)
if 'park_dist_slider' not in st.session_state:
    st.session_state.park_dist_slider = 2000

# -----------------------------------------------------------------------------
# 2. 콜백 함수
# -----------------------------------------------------------------------------
def set_search_condition():
    selection = st.session_state.type_selection
    
    if selection == "유형 1 (하드코어)":
        st.session_state['diff_slider'] = ('상급', '신')
        st.session_state['infra_slider'] = (0.0, 10.0)
        st.session_state['park_dist_slider'] = 2000
        
    elif selection == "유형 2 (초보자 관광)":
        st.session_state['diff_slider'] = ('입문', '초급')
        st.session_state['infra_slider'] = (7.0, 10.0)
        st.session_state['park_dist_slider'] = 1000
        
    elif selection == "유형 3 (접근성 균형)":
        st.session_state['diff_slider'] = ('초급', '상급')
        st.session_state['infra_slider'] = (4.0, 10.0)
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
    park_dist_val = st.slider(
        "주차장 거리 (m 이내)",
        min_value=0, max_value=2000,
        step=100,
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
# 5. 결과 출력 (리스트)
# -----------------------------------------------------------------------------
st.write(f"검색 결과: **{len(filtered_df)}**개의 코스를 찾았습니다.")

display_cols = ['코스명', '위치', '총거리_km', '최고고도_m', '예상시간', '관광인프라점수', '매력종합점수', '주차장거리_m']

if not filtered_df.empty:
    
    sorted_df = filtered_df.sort_values('매력종합점수', ascending=False)
    
    event = st.dataframe(
        sorted_df[display_cols],
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "관광인프라점수": st.column_config.ProgressColumn("인프라", format="%.1f", min_value=0, max_value=10),
            "매력종합점수": st.column_config.NumberColumn("매력도", format="⭐ %.1f"),
            "주차장거리_m": st.column_config.NumberColumn("주차장", format="%d m"),
            "총거리_km": st.column_config.NumberColumn("거리(km)", format="%.1f km"),
            "최고고도_m": st.column_config.NumberColumn("고도", format="%d m")
        }
    )

    # -------------------------------------------------------------------------
    # 6. 선택된 코스 상세 정보 (높이 균형 맞춤)
    # -------------------------------------------------------------------------
    if len(event.selection.rows) > 0:
        st.divider()
        
        # 1) 데이터 추출
        selected_index = event.selection.rows[0]
        selected_row = sorted_df.iloc[selected_index]
        
        mt_name = selected_row['산이름']
        course_name = selected_row['코스명']
        
        st.subheader(f"🥾 {course_name}")

        # 2) 화면 분할
        col_map, col_info = st.columns([1.2, 1])

        # --- [오른쪽] 상세 정보 (먼저 계산하여 높이 짐작) ---
        # 지도를 그리기 전에 정보창을 컴팩트하게 구성합니다.
        with col_info:
            dist_str = f"{selected_row['총거리_km']} km"
            time_str = f"{selected_row['예상시간']}"
            alt_str = f"{int(selected_row['최고고도_m'])} m"
            diff_str = f"{selected_row['난이도']}"
            
            p_name = str(selected_row.get('주차장명', '-'))
            p_dist = selected_row.get('주차장거리_m', 0)
            
            b_name = str(selected_row.get('정류장명', '-'))
            b_dist = selected_row.get('정류장거리_m', 0)

            # [수정] 높이를 줄이기 위해 여백(st.write(""))을 제거하고 구성
            with st.container(border=True):
                
                # 상단 4개 정보
                c1, c2 = st.columns(2)
                with c1:
                    st.caption("⏱️ 소요 시간")
                    st.markdown(f":orange[**{time_str}**]") 
                    st.caption("📏 총 거리") # 간격 없이 바로 배치
                    st.markdown(f"**{dist_str}**")
                with c2:
                    st.caption("⛰️ 최고 고도")
                    st.markdown(f"**{alt_str}**")
                    st.caption("💪 난이도")
                    st.markdown(f":red[**{diff_str}**]")

                st.divider() # 구분선

                # 하단 주차장/정류장 정보 (여백 최소화)
                st.caption("🅿️ 주차장")
                if p_name in ['-', 'nan', 'None'] or p_dist == 0:
                    st.markdown("없음")
                else:
                    st.markdown(f"**{p_name}** <span style='color:grey; font-size:0.8em'>({int(p_dist)}m)</span>", unsafe_allow_html=True)
                
                st.caption("🚏 버스 정류장") # 바로 이어서 출력
                if b_name in ['-', 'nan', 'None'] or b_dist == 0:
                    st.markdown("없음")
                else:
                    st.markdown(f"**{b_name}** <span style='color:grey; font-size:0.8em'>({int(b_dist)}m)</span>", unsafe_allow_html=True)

        # --- [왼쪽] 지도 (높이 조절: 405px) ---
        with col_map:
            base_path = os.path.dirname(os.path.abspath(__file__))
            root_path = os.path.dirname(base_path)
            gpx_folder = os.path.join(root_path, 'data', '100대명산', mt_name)
            gpx_file_path = None
            
            if os.path.exists(gpx_folder):
                files = os.listdir(gpx_folder)
                gpx_files = [f for f in files if f.endswith('.gpx')]
                if gpx_files:
                    gpx_file_path = os.path.join(gpx_folder, gpx_files[0])
            
            if gpx_file_path and os.path.exists(gpx_file_path):
                try:
                    with open(gpx_file_path, 'r', encoding='utf-8') as gpx_file:
                        gpx = gpxpy.parse(gpx_file)
                    
                    points = []
                    for track in gpx.tracks:
                        for segment in track.segments:
                            for point in segment.points:
                                points.append([point.latitude, point.longitude])
                    
                    if points:
                        start_pos = points[0]
                        m = folium.Map(location=start_pos, zoom_start=13)
                        folium.PolyLine(points, color="red", weight=5, opacity=0.8).add_to(m)
                        folium.Marker(points[0], popup="출발", icon=folium.Icon(color='green', icon='play')).add_to(m)
                        folium.Marker(points[-1], popup="도착", icon=folium.Icon(color='blue', icon='stop')).add_to(m)
                        
                        st_folium(m, width=500, height=405) 
                    else:
                        st.warning("GPX 경로 없음")
                except Exception as e:
                    st.error(f"오류: {e}")
            else:
                st.container(height=405, border=True).info("GPX 파일 없음")

else:
    st.info("조건에 맞는 등산로가 없습니다. 조건을 변경해보세요.")