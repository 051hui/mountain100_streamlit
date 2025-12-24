import streamlit as st
import pandas as pd
import os
import gpxpy
import folium
from streamlit_folium import st_folium

# -----------------------------------------------------------------------------
# 0. 데이터 로드 및 초기 설정 (기존과 동일하되 Cluster 컬럼 처리 확인)
# -----------------------------------------------------------------------------
@st.cache_data
def load_mountain_path():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        file_path = os.path.join(root_dir, 'data', '100mountains_dashboard.csv')
        
        df = pd.read_csv(file_path)
        
        full_columns = [
            '코스명', '산이름', '유형설명', '최고고도_m', '누적상승_m', '편도거리_km', '총거리_km', '예상시간_분', '예상시간', 
            '출발_lat', '출발_lon', '도착_lat', '도착_lon', '난이도', '세부난이도', '난이도점수',
            '관광인프라점수','주차장_접근성점수','정류장_접근성점수','코스수','가중치','매력종합점수',
            '전망','힐링','사진','등산로','성취감','계절매력','특출매력','특출점수',
            '주차장거리_m','정류장거리_m','위치', '주차장명', '정류장명', 'Cluster'
        ]
        
        if len(df.columns) == len(full_columns):
            df.columns = full_columns
        elif len(df.columns) >= 33: 
             df.columns = full_columns[:len(df.columns)]
        
        numeric_cols = ['난이도점수', '관광인프라점수', '매력종합점수', '주차장거리_m', '정류장거리_m', '총거리_km', '최고고도_m', 'Cluster']
        
        for col in numeric_cols:
            if col in df.columns:
                # 주차장 거리는 데이터가 없으면 -1로 채움 (0m와 구분하기 위해)
                if col == '주차장거리_m':
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(-1)
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        str_cols = ['주차장명', '정류장명', '위치']
        for col in str_cols:
            if col in df.columns:
                df[col] = df[col].fillna("-")
            
        return df
        
    except FileNotFoundError:
        st.error(f"파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()

# ... (load_infra_data 함수는 기존 동일) ...
@st.cache_data
def load_infra_data():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        file_path = os.path.join(root_dir, 'data', '관광인프라.csv')
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = load_mountain_path()
df_infra = load_infra_data()

if df.empty:
    st.stop()

st.header("🔍 맞춤 등산로 검색")

difficulty_levels = ['입문', '초급', '중급', '상급', '최상급', '초인', '신']

# -----------------------------------------------------------------------------
# [변경] 클러스터 매핑 정의 ("전체 보기" 제거, 순수 데이터만 남김)
# -----------------------------------------------------------------------------
cluster_map = {
    "🌸 계절매력": 0,
    "📷 전망/사진": 2,
    "👨‍👩‍👧‍👦 가족/인프라": 3,
    "🌿 힐링": 4,
    "💎 오지/숨은명소": 5
}
cluster_options = list(cluster_map.keys())

# -----------------------------------------------------------------------------
# 1. 세션 상태 초기화
# -----------------------------------------------------------------------------
if 'diff_slider' not in st.session_state:
    st.session_state.diff_slider = ('입문', '신')
if 'infra_slider' not in st.session_state:
    st.session_state.infra_slider = (0.0, 10.0)
if 'park_dist_slider' not in st.session_state:
    st.session_state.park_dist_slider = 2000

def reset_infra_selection():
    if 'infra_list' in st.session_state:
        del st.session_state['infra_list']

# -----------------------------------------------------------------------------
# 2. 콜백 함수 (Cluster 선택 시 슬라이더 초기화 또는 프리셋 적용)
# -----------------------------------------------------------------------------
def set_search_condition():
    # 사용자가 테마(클러스터)를 바꿨을 때, 기존 필터가 방해되지 않도록
    # 슬라이더를 '전체 범위'로 초기화해주는 것이 좋습니다.
    # (필요하다면 클러스터 성격에 맞춰 범위를 좁혀줄 수도 있습니다)
    
    selection = st.session_state.type_selection
    target_cluster = cluster_map.get(selection)

    # 기본적으로 필터 초기화 (해당 클러스터의 모든 데이터를 보여주기 위함)
    st.session_state['diff_slider'] = ('입문', '신')
    st.session_state['infra_slider'] = (0.0, 10.0)
    st.session_state['park_dist_slider'] = 2000

    # [선택사항] 클러스터 성격에 따른 "제안" 세팅 (원하시면 주석 해제)
    # if target_cluster == 3: # 가족/인프라
    #     st.session_state['infra_slider'] = (5.0, 10.0) # 인프라 좋은 곳 위주
    #     st.session_state['diff_slider'] = ('입문', '중급') # 너무 어렵지 않게
    # elif target_cluster == 5: # 오지/숨은명소
    #     st.session_state['infra_slider'] = (0.0, 4.0) # 인프라 적은 곳

# -----------------------------------------------------------------------------
# 3. UI 구성
# -----------------------------------------------------------------------------
st.markdown("##### 선호하는 등산 테마를 선택해주세요")

st.pills(
    "등산 테마",
    options=cluster_options,
    selection_mode="single",
    key="type_selection",
    on_change=set_search_condition,
    default=None # 기본값 없음
)

st.divider()

st.markdown("##### 세부 조건을 조절해보세요")

col1, col2, col3 = st.columns(3)

with col1:
    diff_val = st.select_slider(
        "산행 난이도",
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
# 4. 데이터 필터링 [핵심 변경 구간]
# -----------------------------------------------------------------------------
try:
    # 1) 공통 필터 조건
    start_idx = difficulty_levels.index(diff_val[0])
    end_idx = difficulty_levels.index(diff_val[1])
    selected_levels = difficulty_levels[start_idx : end_idx + 1]

    common_condition = (
        (df['난이도'].isin(selected_levels)) &
        (df['관광인프라점수'] >= infra_val[0]) & (df['관광인프라점수'] <= infra_val[1]) &
        (df['주차장거리_m'] != -1) &            # [변경] -1(데이터 없음)인 경우만 제외
        (df['주차장거리_m'] <= park_dist_val)   # 0m(바로 앞)인 경우는 여기에 포함되어 살아남음
    )

    # 2) 테마(Cluster) 필터링 로직
    current_selection = st.session_state.get('type_selection')
    
    if current_selection is None:
        filtered_df = df[common_condition]
    else:
        target_cluster_id = cluster_map.get(current_selection)
        filtered_df = df[
            (df['Cluster'] == target_cluster_id) & 
            common_condition
        ]
        
except Exception as e:
    st.error(f"필터링 오류 발생: {e}")
    filtered_df = pd.DataFrame()

# -----------------------------------------------------------------------------
# 5. 결과 출력 (이후 코드는 기존과 동일)
# -----------------------------------------------------------------------------
st.write(f"검색 결과: **{len(filtered_df)}**개의 코스를 찾았습니다.")

display_cols = ['코스명', '위치', '총거리_km', '최고고도_m', '세부난이도', '관광인프라점수', '매력종합점수', '주차장거리_m']

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
    # 6. 선택된 코스 상세 정보 & 지도 & 인프라
    # -------------------------------------------------------------------------
    if len(event.selection.rows) > 0:
        st.divider()
        
        # 1) 선택된 등산로 데이터 가져오기
        selected_index = event.selection.rows[0]
        selected_row = sorted_df.iloc[selected_index]
        
        mt_name = selected_row['산이름']
        course_name = selected_row['코스명'] 
        
        st.subheader(f"🥾 {course_name}")

        # ---------------------------------------------------------------------
        # [수정] 인프라 데이터 필터링 로직 변경 (산 이름 -> 코스명/trail_code)
        # ---------------------------------------------------------------------
        pin_location = None
        pin_popup = None
        
        # 현재 선택된 카테고리 (기본값: 음식점)
        current_category = st.session_state.get('infra_category_radio', '음식점')
        
        infra_display = pd.DataFrame() # 초기화

        if not df_infra.empty:
            if 'trail_code' in df_infra.columns:
                infra_filtered = df_infra[df_infra['trail_code'] == course_name]
            else:
                infra_filtered = df_infra[df_infra['mountain_name'] == mt_name]

            # 카테고리 필터링
            infra_display = infra_filtered[infra_filtered['category'] == current_category].reset_index(drop=True)
            
            # 리스트에서 선택된 항목이 있다면 핀 위치 설정
            if 'infra_list' in st.session_state and st.session_state.infra_list['selection']['rows']:
                sel_idx = st.session_state.infra_list['selection']['rows'][0]
                if sel_idx < len(infra_display):
                    sel_infra_row = infra_display.iloc[sel_idx]
                    pin_location = [sel_infra_row['lat'], sel_infra_row['lng']]
                    pin_popup = sel_infra_row['place_name']
        
        # ---------------------------------------------------------------------
        # 지도 및 상세 정보 출력 (기존 코드와 동일)
        # ---------------------------------------------------------------------
        col_map, col_info = st.columns([1.2, 1])

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
                         
                         if pin_location:
                             folium.Marker(
                                 pin_location, 
                                 popup=pin_popup, 
                                 icon=folium.Icon(color='orange', icon='star')
                             ).add_to(m)
                         st_folium(m, width=500, height=400)
                     else:
                         st.warning("GPX 경로 없음")
                 except Exception as e:
                     st.error(f"오류: {e}")
             else:
                 st.container(height=400, border=True).info("GPX 파일 없음")

        # --- [오른쪽] 상세 정보 (기존과 동일) ---
        with col_info:
             dist_str = f"{selected_row['총거리_km']} km"
             time_str = f"{selected_row['예상시간']}"
             alt_str = f"{int(selected_row['최고고도_m'])} m"
             diff_str = f"{selected_row['세부난이도']}"
             
             p_name = str(selected_row.get('주차장명', '-'))
             p_dist = selected_row.get('주차장거리_m', 0)
             b_name = str(selected_row.get('정류장명', '-'))
             b_dist = selected_row.get('정류장거리_m', 0)

             with st.container(border=True):
                 c1, c2 = st.columns(2)
                 with c1:
                     st.caption("⏱️ 소요 시간")
                     st.markdown(f":orange[**{time_str}**]") 
                     st.caption("📏 총 거리")
                     st.markdown(f"**{dist_str}**")
                 with c2:
                     st.caption("⛰️ 최고 고도")
                     st.markdown(f"**{alt_str}**")
                     st.caption("💪 난이도")
                     st.markdown(f":red[**{diff_str}**]")

                 st.divider()

                 st.caption("🅿️ 주차장")
                 if p_name in ['-', 'nan', 'None'] or p_dist == 0:
                     st.markdown("-")
                 else:
                     st.markdown(f"**{p_name}** <span style='color:grey; font-size:0.8em'>({int(p_dist)}m)</span>", unsafe_allow_html=True)

                 st.caption("🚏 버스 정류장")
                 if b_name in ['-', 'nan', 'None'] or b_dist == 0:
                     st.markdown("-")
                 else:
                     st.markdown(f"**{b_name}** <span style='color:grey; font-size:0.8em'>({int(b_dist)}m)</span>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # 7. 관광 인프라 리스트 (위에서 정의한 infra_display 사용)
        # ---------------------------------------------------------------------
        if not infra_display.empty:
            categories = ["음식점", "카페", "숙박", "관광명소"]
            st.radio(
                "카테고리 선택", 
                categories, 
                index=0, 
                key="infra_category_radio", 
                horizontal=True,
                on_change=reset_infra_selection,
                label_visibility="collapsed" 
            )
            
            st.write("") 

            # 기준 위치 및 포맷팅 처리
            infra_display['location_type'] = infra_display['base_type'].apply(
                lambda x: '출발지' if x == 'start' else '도착지'
            )
            
            cols_to_show = ['place_name', 'location_type', 'distance_m', 'address']
            col_config = {
                "place_name": st.column_config.TextColumn("장소명"),
                "location_type": st.column_config.TextColumn("기준 위치"),
                "distance_m": st.column_config.NumberColumn("거리", format="%d m"),
                "address": st.column_config.TextColumn("주소")
            }
            
            if current_category == '관광명소':
                cols_to_show.insert(1, 'tour_spot_type')
                col_config["tour_spot_type"] = st.column_config.TextColumn("구분")

            st.dataframe(
                infra_display[cols_to_show],
                key="infra_list",
                on_select="rerun",
                selection_mode="single-row",
                use_container_width=True,
                hide_index=True,
                column_config=col_config
            )
            
            if pin_location:
                 st.info(f"📍 지도에 '{pin_popup}' 위치가 표시되었습니다. (주황색 별)")
            
        else:
            st.info(f"선택하신 '{course_name}' 주변에는 해당 카테고리의 시설 정보가 없습니다.")

    else:
        st.info("등산로를 선택하면 상세 정보가 표시됩니다.")
else:
    st.info("조건에 맞는 등산로가 없습니다. 다른 테마나 조건을 선택해보세요.")