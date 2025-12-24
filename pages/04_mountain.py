# pages/04_mountain.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import json
import numpy as np
from PIL import Image
from wordcloud import WordCloud
import plotly.express as px

import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

# -------------------------
# 스타일
# -------------------------
st.markdown(
    """
    <style>
      .title-wrap { margin-bottom: 20px; }
      .subtle { color: #6b7280; font-size: 0.95rem; margin-top: 8px; }
      .card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 20px;
        background: white;
      }
      .soft { background: #f9fafb; }
      .hr {
        margin: 22px 0 18px 0;
        border-top: 1px solid #e5e7eb;
      }
      .info-box {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
      }
      .button-container {
        display: flex;
        gap: 12px;
        margin: 20px 0;
      }
      
      
      /* =========================
         🥾 등산로 버튼만 스타일 적용
         ========================= */

      .trail-chip-area div.stButton > button {
        padding: 6px 10px;
        height: 38px;
        font-size: 0.75rem;
        border-radius: 10px;

        background-color: #ecfdf5;
        color: #065f46;
        border: 1px solid #86efac;

        font-weight: 500;
        white-space: nowrap;
      }

      .trail-chip-area div.stButton > button:hover {
        background-color: #d1fae5;
        border-color: #34d399;
        color: #064e3b;
      }

      .trail-chip-area div.stButton > button[kind="primary"] {
        background-color: #22c55e !important;
        color: white !important;
        border-color: #16a34a !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# 데이터 로드
# -------------------------
@st.cache_data
def load_mountain_csv():
    csv_path = (Path(__file__).resolve().parent.parent / "data" / "mountain.csv").resolve()
    df = pd.read_csv(csv_path)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["mountain_name", "lat", "lon"]).reset_index(drop=True)
    
    # 영어 이름과 설명 컬럼이 없으면 빈 문자열로 초기화
    if "mountain_name_en" not in df.columns:
        df["mountain_name_en"] = ""
    if "description" not in df.columns:
        df["description"] = ""
    
    # 결측값을 빈 문자열로 처리
    df["mountain_name_en"] = df["mountain_name_en"].fillna("")
    df["description"] = df["description"].fillna("")
    
    return df

@st.cache_data
def load_trail_data():
    """등산로 데이터 로드"""
    csv_path = (Path(__file__).resolve().parent.parent / "data" / "100mountains_dashboard.csv").resolve()
    df = pd.read_csv(csv_path)
    return df

@st.cache_data
def load_mountain_keywords():
    """산별 키워드 JSON 로드"""
    try:
        json_path = (Path(__file__).resolve().parent.parent / "data" / "mountain_keywords.json").resolve()
        
        if not json_path.exists():
            st.error(f"파일을 찾을 수 없습니다: {json_path}")
            return {}
        
        if json_path.stat().st_size == 0:
            st.error(f"파일이 비어있습니다: {json_path}")
            return {}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            st.warning("키워드 데이터가 비어있습니다")
            return {}
            
        return data
        
    except json.JSONDecodeError as e:
        st.error(f"JSON 파싱 에러: {e}")
        return {}
    except Exception as e:
        st.error(f"파일 로드 에러: {e}")
        return {}

@st.cache_data
def load_mask_image():
    """워드클라우드 마스크 이미지 로드"""
    mask_path = (Path(__file__).resolve().parent.parent / "images" / "mountain_mask_back.png").resolve()
    return np.array(Image.open(mask_path).convert("RGB"))

df_m = load_mountain_csv()
df_trails = load_trail_data()
keywords_dict = load_mountain_keywords()
mask_img = load_mask_image()

# -------------------------
# 워드클라우드 생성 함수
# -------------------------
def generate_wordcloud(mountain_name, top_n=65):
    """선택된 산의 워드클라우드 생성"""
    if mountain_name not in keywords_dict:
        return None
    
    freq = keywords_dict[mountain_name]
    if not freq:
        return None
    
    freq_top = dict(sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n])
    
    wc = WordCloud(
        font_path="/System/Library/Fonts/AppleSDGothicNeo.ttc",
        background_color="white",
        mask=mask_img,
        width=1000,
        height=800,
        max_words=top_n,
        prefer_horizontal=0.9,
        collocations=False,
        colormap='summer',
        relative_scaling=0.5,
        min_font_size=10
    ).generate_from_frequencies(freq_top)
    
    img = wc.to_array()
    
    fig = px.imshow(img)
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=400
    )
    fig.update_xaxes(showticklabels=False)
    fig.update_yaxes(showticklabels=False)
    
    return fig

# -------------------------
# 세션 상태
# -------------------------
if "selected_mountain" not in st.session_state:
    st.session_state.selected_mountain = df_m["mountain_name"].iloc[0]
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "attraction"
if "selected_course" not in st.session_state:
    st.session_state.selected_course = None
if "selected_trail_data" not in st.session_state:
    st.session_state.selected_trail_data = None

# -------------------------
# 유틸: 선택 산 한 줄 가져오기
# -------------------------
def get_selected_row():
    row = df_m.loc[df_m["mountain_name"] == st.session_state.selected_mountain]
    if row.empty:
        return df_m.iloc[0]
    return row.iloc[0]

sel = get_selected_row()

# -------------------------
# 상단 제목
# -------------------------
st.markdown(
    """
    <div class="title-wrap">
      <h2>⛰️ 산 정보 조회</h2>
      <div class="subtle">선택창에서 선정한 전국의 100대 명산의 정보를 조회하실 수 있습니다.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# -------------------------
# 산 선택 드롭다운
# -------------------------
st.markdown("##### 원하시는 산을 선택해 주세요.")

mountain_list = df_m["mountain_name"].tolist()
selected_idx = mountain_list.index(st.session_state.selected_mountain) if st.session_state.selected_mountain in mountain_list else 0

new_selection = st.selectbox(
    "산 선택",
    mountain_list,
    index=selected_idx,
    label_visibility="collapsed"
)

if new_selection != st.session_state.selected_mountain:
    st.session_state.selected_mountain = new_selection
    st.session_state.selected_course = None
    st.session_state.selected_trail_data = None
    st.rerun()

st.write("")
st.write("")



# -------------------------
# (A) 지도 영역 (folium + 마커)
# -------------------------
center_lat = float(df_m["lat"].mean())
center_lon = float(df_m["lon"].mean())

m = folium.Map(
    location=[center_lat, center_lon], 
    zoom_start=7, 
    control_scale=True,
    prefer_canvas=True  # ✅ 성능 개선
)

for _, r in df_m.iterrows():
    name = r["mountain_name"]
    lat = float(r["lat"])
    lon = float(r["lon"])
    
    if name == st.session_state.selected_mountain:
        color = "red"
        radius = 10
        weight = 3
    else:
        color = "blue"
        radius = 7
        weight = 2

    folium.CircleMarker(
        location=[lat, lon],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        weight=weight,
        popup=folium.Popup(name, max_width=200),
        tooltip=folium.Tooltip(name, permanent=False),
    ).add_to(m)

# 지도 렌더링
map_output = st_folium(
    m, 
    use_container_width=True, 
    height=500,
    key="mountain_map",  # ✅ 고정 key
    returned_objects=["last_object_clicked"]  # ✅ 필요한 이벤트만 받기
)

# 클릭 이벤트 처리
if map_output and map_output.get("last_object_clicked"):
    clicked_obj = map_output["last_object_clicked"]
    
    if clicked_obj and "lat" in clicked_obj and "lng" in clicked_obj:
        clicked_lat = clicked_obj["lat"]
        clicked_lon = clicked_obj["lng"]
        
        # 클릭한 위치에서 가장 가까운 산 찾기
        distances = []
        for idx, r in df_m.iterrows():
            dist = (r["lat"] - clicked_lat) ** 2 + (r["lon"] - clicked_lon) ** 2
            distances.append((dist, r["mountain_name"]))
        
        distances.sort()
        nearest_mountain = distances[0][1]
        
        # 가장 가까운 산이 현재 선택과 다르고, 거리가 너무 멀지 않으면 선택
        if nearest_mountain != st.session_state.selected_mountain and distances[0][0] < 1.0:  # ✅ 거리 임계값
            st.session_state.selected_mountain = nearest_mountain
            st.session_state.selected_course = None
            st.session_state.selected_trail_data = None
            st.rerun()

st.write("")
st.write("")

# -------------------------
# (B) 산 상세 기본 정보 카드
# -------------------------
left, right = st.columns([1, 1], gap="small")

with left:
    # 산 정보 카드
    mountain_name = sel['mountain_name']
    mountain_name_en = sel.get('mountain_name_en', '')
    description = sel.get('description', '')
    location = sel.get('location', '-')
    altitude = sel.get('altitude', '-')
    
    st.markdown(
        f"""
        <div style="background: white; border-radius: 5px; padding: 15px; height: 100%; min-height: 400px; display: flex; flex-direction: column; text-align: center;">
          <div style="margin-bottom: clamp(8px, 1.5vw, 16px);">
            <div style="margin: 20px 0 4px 0; font-size: clamp(1.5rem, 3vw, 2.8rem); font-weight: 700; color: #1f2937; text-align: center;">{mountain_name}</div>
            <div style="font-size: clamp(1.3rem, 2.5vw, 2.2rem); font-weight: 600; color: #659F34; ">{mountain_name_en}</div>
          </div>
          
          <div style="color: #4b5563; font-size: clamp(0.85rem, 1.2vw, 1.1rem); line-height: 1.6; flex-grow: 0.1; margin-bottom: clamp(12px, 2vw, 24px);">
            {description}
          </div>
          <div style="display: flex; align-items: center; justify-content: center; margin-bottom: clamp(8px, 1vw, 14px);">
              <span style="font-size: clamp(1rem, 1.5vw, 1.4rem); margin-right: 8px;">📍</span>
              <span style="color: #6b7280; font-size: clamp(0.85rem, 1.1vw, 1.05rem);">{location}</span>
            </div>
            <div style="display: flex; align-items: center; justify-content: center;">
              <span style="font-size: clamp(0.9rem, 1.3vw, 1.2rem); margin-right: 8px;">⛰️</span>
              <span style="color: #1f2937; font-size: clamp(1rem, 1.4vw, 1.3rem); font-weight: 600;">{altitude} m</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with right:
    # 산 이미지
    image_path = (Path(__file__).resolve().parent.parent / "images" / f"{mountain_name}.jpg").resolve()
    
    if image_path.exists():
        st.image(str(image_path), use_container_width=True)
    else:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 5px; 
                        height: 500px; 
                        display: flex; 
                        flex-direction: column; 
                        align-items: center; 
                        justify-content: center;
                        color: white;">
              <div style="font-size: 3rem; margin-bottom: 16px;">🏔️</div>
              <div style="font-size: 1.2rem; font-weight: 600;">이미지 준비중</div>
              <div style="font-size: 0.9rem; margin-top: 8px; opacity: 0.8;">images/{mountain_name}.jpg</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")

# -------------------------
# (C) 모드 버튼 (가로 배치)
# -------------------------
col1, col2 = st.columns(2, gap="medium")

def set_mode(mode: str):
    st.session_state.view_mode = mode
    if mode == "attraction":
        st.session_state.selected_course = None
        st.session_state.selected_trail_data = None

# with col1:
#     btn_type = "primary" if st.session_state.view_mode == "weather" else "secondary"
#     if st.button("📊 실시간 날씨 정보", use_container_width=True, type=btn_type):
#         set_mode("weather")

# with col2:
#     btn_type = "primary" if st.session_state.view_mode == "fire_risk" else "secondary"
#     if st.button("🏔️ 실시간 산불 위험도", use_container_width=True, type=btn_type):
#         set_mode("fire_risk")

st.write("")

col3, col4 = st.columns(2, gap="medium")

with col3:
    btn_type = "primary" if st.session_state.view_mode == "attraction" else "secondary"
    if st.button("🌟 매력 확인하기", use_container_width=True, type=btn_type):
        set_mode("attraction")

with col4:
    btn_type = "primary" if st.session_state.view_mode == "course" else "secondary"
    if st.button("🥾 등산로 코스 확인하기", use_container_width=True, type=btn_type):
        set_mode("course")

st.write("")
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.write("")

# -------------------------
# (D) 모드별 렌더링
# -------------------------
if st.session_state.view_mode == "attraction":

    label_to_col = {
        "뷰·경관": "view_score_weighted",
        "힐링": "healing_score_weighted",
        "SNS·사진": "sns_photo_score_weighted",
        "등산로 관리": "trail_condition_score_weighted",
        "재미·성취": "fun_achievement_score_weighted",
        "계절성": "seasonal_attraction_score_weighted",
    }

    categories = list(label_to_col.keys())
    values = [float(sel[label_to_col[k]] or 0) for k in categories]

    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    c1, c2 = st.columns([1, 1], gap="large")

    with c1:
        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=categories_closed,
                fill="toself",
                name=sel["mountain_name"],
                fillcolor='rgba(101, 159, 52, 0.5)',
                line=dict(color='rgba(89, 144, 43, 0.8)', width=2)
            )
        )

        fig.update_layout(
            height=400,
            margin=dict(l=40, r=40, t=20, b=20),
            showlegend=False,
            paper_bgcolor='white',
            plot_bgcolor='white',
            polar=dict(
                bgcolor='white',
                radialaxis=dict(
                    visible=True, 
                    range=[0, 10], 
                    tickfont=dict(size=11),
                    gridcolor='rgba(200, 200, 200, 0.3)'
                ),
                angularaxis=dict(
                    tickfont=dict(size=12, color='#333'),
                    gridcolor='rgba(200, 200, 200, 0.3)'
                ),
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

    with c2:
        wc_fig = generate_wordcloud(st.session_state.selected_mountain)
        
        if wc_fig:
            st.plotly_chart(wc_fig, use_container_width=True)
        else:
            st.markdown(
                """
                <div style="border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; height: 400px; display: flex; align-items: center; justify-content: center; background: white;">
                    <div style="text-align: center;">
                        <div style="font-size: 18px; font-weight: 600; color: #6b7280; margin-bottom: 8px;">워드클라우드</div>
                        <div style="font-size: 14px; color: #9ca3af;">해당 산의 키워드 데이터가 없습니다</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.write("")
    st.write("")

    st.markdown("##### 감성분석 기반 매력 지수")
    st.write("")

    averages = {}
    for k, col in label_to_col.items():
        averages[k] = df_m[col].astype(float).mean()

    index_names = {
        "뷰·경관": "뷰·경관 지수",
        "힐링": "힐링 지수",
        "SNS·사진": "SNS·사진 지수",
        "등산로 관리": "등산로 관리 지수",
        "재미·성취": "재미·성취 지수",
        "계절성": "계절성 지수",
    }

    kpi_cols = st.columns(6, gap="small")

    for i, k in enumerate(categories):
        v = float(sel[label_to_col[k]] or 0)
        avg = averages[k]
        
        diff = v - avg
        diff_percent = (diff / avg * 100) if avg != 0 else 0
        
        if v >= avg:
            box_color = "#ebf2e6"
            num_color = "#39501b"
            diff_color = "#5b7f2b"
            arrow = "▲"
        else:
            box_color = "#f2e9e6"
            num_color = "#50301b"
            diff_color = "#b36c3d"
            arrow = "▼"
        
        with kpi_cols[i]:
            html_content = f"""
            <div style="background-color: {box_color}; border-radius: 10px; padding: 15px 20px; height: 100px; display: flex; flex-direction: column;">
                <div style="font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: auto;">
                    {index_names[k]}
                </div>
                <div style="display: flex; align-items: flex-end; justify-content: space-between; gap: 8px;">
                    <div style="font-size: 38px; font-weight: 500; color: {num_color}; line-height: 1;">
                        {v:.1f}
                    </div>
                    <div style="font-size: 12px; color: {diff_color}; font-weight: 500; text-align: right; white-space: nowrap;">
                        평균대비<br>{arrow}{abs(diff_percent):.1f}%
                    </div>
                </div>
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)                 


# 등산로 코스 확인하기 섹션 수정

elif st.session_state.view_mode == "course":
    st.markdown("### 🥾 등산로 코스")
    
    # 선택된 산의 등산로 목록 가져오기
    mountain_trails = df_trails[df_trails['산이름'] == st.session_state.selected_mountain].copy()
    
    if mountain_trails.empty:
        st.warning(f"{st.session_state.selected_mountain}의 등산로 데이터가 없습니다.")
    else:
        st.caption(f"총 {len(mountain_trails)}개의 등산로가 있습니다.")
        st.write("")
        
        # 코스명 리스트 생성
        trail_df = mountain_trails.copy()
        trail_df["코스명"] = trail_df["코스명"].fillna("코스").astype(str)
        trail_names = trail_df["코스명"].tolist()
        
        # pills 기본값 설정
        default_selection = None
        if st.session_state.selected_course in trail_names:
            default_selection = st.session_state.selected_course
        
        # pills 렌더링
        picked = st.pills(
            "코스 선택",
            trail_names,
            selection_mode="single",
            default=default_selection,
            key=f"trail_pills_{st.session_state.selected_mountain}",  # ✅ 산 이름을 key에 포함
        )
        
        # 선택 변경 감지 및 세션 상태 업데이트
        if picked:
            if picked != st.session_state.selected_course:
                st.session_state.selected_course = picked
                st.session_state.selected_trail_data = trail_df.loc[trail_df["코스명"] == picked].iloc[0]
                st.rerun()  # ✅ rerun 추가
        else:
            # 선택 해제된 경우
            if st.session_state.selected_course is not None:
                st.session_state.selected_course = None
                st.session_state.selected_trail_data = None
        
        st.write("")
        
        # 코스가 선택되지 않았을 때
        if not st.session_state.selected_course:
            st.info("코스를 하나 선택하면 아래에 코스 상세 정보가 나타납니다.")
        else:
            # 선택된 코스의 상세 정보
            selected_trail = st.session_state.selected_trail_data
            
            st.write("")
            st.markdown(f"#### 🥾 {st.session_state.selected_course}")
            
            top_l, top_r = st.columns([1.2, 1.8], gap="large")
            
            with top_l:
                st.markdown(
                    '<div class="card soft" style="height:300px; display: flex; flex-direction: column; justify-content: center; align-items: center;"><div style="font-size: 24px; color: #6b7280;">🗺️ 코스 지도</div><div style="font-size: 14px; color: #9ca3af; margin-top: 8px;">GPX 시각화 예정</div></div>',
                    unsafe_allow_html=True,
                )
            
            with top_r:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                
                # 등산로 정보 표시
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    if '예상시간' in selected_trail and pd.notna(selected_trail['예상시간']):
                        st.write(f"⏱️ **소요시간:** {selected_trail['예상시간']}")
                    
                    if '총거리_km' in selected_trail and pd.notna(selected_trail['총거리_km']):
                        st.write(f"📏 **총 거리:** {selected_trail['총거리_km']:.1f} km")
                    
                    if '최고고도_m' in selected_trail and pd.notna(selected_trail['최고고도_m']):
                        st.write(f"⛰️ **최고 고도:** {selected_trail['최고고도_m']:.0f} m")
                
                with col_info2:
                    if '난이도' in selected_trail and pd.notna(selected_trail['난이도']):
                        st.write(f"⭐ **난이도:** {selected_trail['난이도']}")
                    
                    if '누적상승_m' in selected_trail and pd.notna(selected_trail['누적상승_m']):
                        st.write(f"📈 **누적 상승:** {selected_trail['누적상승_m']:.0f} m")
                    
                    if '유형설명' in selected_trail and pd.notna(selected_trail['유형설명']):
                        st.write(f"🏔️ **유형:** {selected_trail['유형설명']}")
                
                st.write("")
                
                # 접근성 정보
                if '주차장거리_m' in selected_trail and pd.notna(selected_trail['주차장거리_m']):
                    st.write(f"🚗 **주차장까지:** {selected_trail['주차장거리_m']:.0f} m")
                
                if '정류장거리_m' in selected_trail and pd.notna(selected_trail['정류장거리_m']):
                    st.write(f"🚌 **버스정류장까지:** {selected_trail['정류장거리_m']:.0f} m")
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.write("")
            st.write("")
            
            # 주변 정보
            poi_type = st.radio("주변 정보 보기", ["음식점", "카페", "숙박", "관광명소"], horizontal=True)
            st.markdown(f'<div class="card soft" style="padding: 40px; text-align: center;"><div style="font-size: 18px; color: #6b7280;">📍 {poi_type} 정보</div><div style="font-size: 14px; color: #9ca3af; margin-top: 8px;">다음 단계에서 구현 예정</div></div>', unsafe_allow_html=True)

elif st.session_state.view_mode == "weather":
    st.markdown("### 📊 실시간 날씨 정보")
    st.info("날씨 API 연동 예정")
    
elif st.session_state.view_mode == "fire_risk":
    st.markdown("### 🏔️ 실시간 산불 위험도")
    st.info("산불 위험도 API 연동 예정")