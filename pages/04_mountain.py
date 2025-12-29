# pages/04_mountain.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
import json
import os
import numpy as np
from PIL import Image
from wordcloud import WordCloud
import plotly.express as px
import platform
import folium
from streamlit_folium import st_folium
from utils.trail_detail import show_trail_detail


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
      
      /* 매력/등산로 버튼 스타일 */
      .stButton > button {
        height: 60px !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        padding: 16px 24px !important;
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
    
    if "mountain_name_en" not in df.columns:
        df["mountain_name_en"] = ""
    if "description" not in df.columns:
        df["description"] = ""
    
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

@st.cache_data
def load_mountain_keywords():
    """산별 키워드 JSON 로드"""
    try:
        json_path = (Path(__file__).resolve().parent.parent / "data" / "mountain_keywords.json").resolve()
        
        if not json_path.exists():
            return {}
        
        if json_path.stat().st_size == 0:
            return {}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not data:
            return {}
            
        return data
        
    except json.JSONDecodeError as e:
        return {}
    except Exception as e:
        return {}

@st.cache_data
def load_mask_image():
    """워드클라우드 마스크 이미지 로드"""
    mask_path = (Path(__file__).resolve().parent.parent / "images" / "mountain_mask_back.png").resolve()
    return np.array(Image.open(mask_path).convert("RGB"))

df_m = load_mountain_csv()
df_trails = load_trail_data()
df_infra = load_infra_data()
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
    
    if platform.system() == 'Windows':
        font_path = 'C:/Windows/Fonts/malgun.ttf'
    
    elif platform.system() == 'Darwin': # Mac
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        
    else: # Linux (Streamlit Cloud)
        # packages.txt로 설치하면 이 경로에 생깁니다.
        font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"

    wc = WordCloud(
            font_path=path,
            background_color="#ffffff",
            mask=mask_img,
            width=1000,
            height=800,
            max_words=top_n,
            prefer_horizontal=0.9,
            collocations=False,
            colormap='gist_earth',
            relative_scaling=0.5,
            min_font_size=12
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
# 세션 상태 초기화
# -------------------------
if "selected_mountain" not in st.session_state:
    st.session_state.selected_mountain = None  # ✅ 초기값을 None으로 변경
if "view_mode" not in st.session_state:
    st.session_state.view_mode = None  # ✅ 초기값을 None으로 변경
if "selected_course" not in st.session_state:
    st.session_state.selected_course = None
if "selected_trail_data" not in st.session_state:
    st.session_state.selected_trail_data = None

# -------------------------
# 유틸: 선택 산 한 줄 가져오기
# -------------------------
def get_selected_row():
    if st.session_state.selected_mountain is None:
        return None
    row = df_m.loc[df_m["mountain_name"] == st.session_state.selected_mountain]
    if row.empty:
        return None
    return row.iloc[0]

# -------------------------
# 상단 제목
# -------------------------
st.markdown(
    """
    <div class="title-wrap">
      <h2>⛰️ 산 정보 조회</h2>
      <div class="subtle">지도에서 산을 클릭하거나 검색하여 정보를 확인하세요.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# -------------------------
# 산 선택 드롭다운 (항상 표시)
# -------------------------
st.markdown("##### 원하시는 산을 선택해 주세요.")

mountain_list = ["선택 안 함"] + df_m["mountain_name"].tolist()  # ✅ "선택 안 함" 추가

if st.session_state.selected_mountain is None:
    selected_idx = 0
elif st.session_state.selected_mountain in mountain_list:
    selected_idx = mountain_list.index(st.session_state.selected_mountain)
else:
    selected_idx = 0

new_selection = st.selectbox(
    "산 선택",
    mountain_list,
    index=selected_idx,
    label_visibility="collapsed"
)

# 드롭다운 선택 변경 감지
if new_selection == "선택 안 함":
    if st.session_state.selected_mountain is not None:
        st.session_state.selected_mountain = None
        st.session_state.view_mode = None
        st.session_state.selected_course = None
        st.session_state.selected_trail_data = None
        st.rerun()
elif new_selection != st.session_state.selected_mountain:
    st.session_state.selected_mountain = new_selection
    st.session_state.view_mode = None  # ✅ 새로운 산 선택 시 view_mode 초기화
    st.session_state.selected_course = None
    st.session_state.selected_trail_data = None
    st.rerun()

st.write("")
st.write("")

# -------------------------
# 지도 영역 (folium + 마커)
# -------------------------
center_lat = float(df_m["lat"].mean())
center_lon = float(df_m["lon"].mean())

m = folium.Map(
    location=[center_lat, center_lon], 
    zoom_start=7, 
    control_scale=True,
    prefer_canvas=True
)

for _, r in df_m.iterrows():
    name = r["mountain_name"]
    lat = float(r["lat"])
    lon = float(r["lon"])
    
    if name == st.session_state.selected_mountain:
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(name, max_width=200),
            tooltip=folium.Tooltip(name, permanent=False),
            icon=folium.DivIcon(html=f'''
                <div style="
                    position: relative;
                    width: 20px;
                    height: 20px;
                ">
                    <div style="
                        position: absolute;
                        width: 20px;
                        height: 20px;
                        background-color: #ff0066;
                        border-radius: 50%;
                        animation: pulse 1.5s infinite;
                    "></div>
                    <div style="
                        position: absolute;
                        width: 20px;
                        height: 20px;
                        background-color: #ff0066;
                        border-radius: 50%;
                        box-shadow: 0 0 0 0 rgba(255, 0, 102, 1);
                    "></div>
                </div>
                <style>
                    @keyframes pulse {{
                        0% {{ transform: scale(1); opacity: 1; }}
                        50% {{ transform: scale(1.5); opacity: 0.5; }}
                        100% {{ transform: scale(1); opacity: 1; }}
                    }}
                </style>
            ''')
        ).add_to(m)
    else:
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            color="#689634",
            fill=True,
            fill_color="#689634",
            fill_opacity=0.6,
            weight=2,
            popup=folium.Popup(name, max_width=200),
            tooltip=folium.Tooltip(name, permanent=False),
        ).add_to(m)

# 지도 렌더링
map_output = st_folium(
    m, 
    width="stretch", 
    height=500,
    key="mountain_map",
    returned_objects=["last_object_clicked"]
)

# 클릭 이벤트 처리
if map_output and map_output.get("last_object_clicked"):
    clicked_obj = map_output["last_object_clicked"]
    
    if clicked_obj and "lat" in clicked_obj and "lng" in clicked_obj:
        clicked_lat = clicked_obj["lat"]
        clicked_lon = clicked_obj["lng"]
        
        distances = []
        for idx, r in df_m.iterrows():
            dist = (r["lat"] - clicked_lat) ** 2 + (r["lon"] - clicked_lon) ** 2
            distances.append((dist, r["mountain_name"]))
        
        distances.sort()
        nearest_mountain = distances[0][1]
        
        if nearest_mountain != st.session_state.selected_mountain and distances[0][0] < 1.0:
            st.session_state.selected_mountain = nearest_mountain
            st.session_state.view_mode = None  # ✅ 새로운 산 선택 시 view_mode 초기화
            st.session_state.selected_course = None
            st.session_state.selected_trail_data = None
            st.rerun()

# ✅ 여기서부터는 산이 선택된 경우에만 표시
if st.session_state.selected_mountain is None:
    st.stop()  # ✅ 산이 선택되지 않았으면 여기서 종료

# -------------------------
# 선택된 산 정보 가져오기
# -------------------------
sel = get_selected_row()
if sel is None:
    st.stop()

st.write("")
st.write("")

# -------------------------
# 산 상세 기본 정보 카드
# -------------------------
left, right = st.columns([1, 1], gap="small")

with left:
    mountain_name = sel['mountain_name']
    mountain_name_en = sel.get('mountain_name_en', '')
    description = sel.get('description', '')
    location = sel.get('location', '-')
    altitude = sel.get('altitude', '-')
    
    st.markdown(
        f"""
        <div style="background: rgba(0,0,0,0); border-radius: 5px; padding: 15px; height: 100%; min-height: 300px; display: flex; flex-direction: column; text-align: center; ">
          <div style="margin-bottom: clamp(8px, 1.5vw, 16px);">
            <div style="margin: 0px 0 4px 0; font-size: clamp(1.5rem, 3vw, 2.8rem); font-weight: 700; color: #1f2937; text-align: center;">{mountain_name}</div>
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
    image_path = (Path(__file__).resolve().parent.parent / "images" / f"{mountain_name}.jpg").resolve()
    
    if image_path.exists():
        st.image(str(image_path), width="stretch")
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
# 모드 선택 버튼 (산이 선택된 경우에만 표시)
# -------------------------
col3, col4 = st.columns(2, gap="medium")

with col3:
    btn_type = "primary" if st.session_state.view_mode == "attraction" else "secondary"
    if st.button("🌟 매력 확인하기", width="stretch", type=btn_type, key="btn_attraction"):
        st.session_state.view_mode = "attraction"
        st.session_state.selected_course = None
        st.session_state.selected_trail_data = None
        st.rerun()

with col4:
    btn_type = "primary" if st.session_state.view_mode == "course" else "secondary"
    if st.button("🥾 등산로 코스 확인하기", width="stretch", type=btn_type, key="btn_course"):
        st.session_state.view_mode = "course"
        st.rerun()

# ✅ 모드가 선택되지 않았으면 여기서 종료
if st.session_state.view_mode is None:
    st.info("👆 위 버튼을 클릭하여 상세 정보를 확인하세요.")
    st.stop()

st.write("")
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
st.write("")

# -------------------------
# 모드별 렌더링
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
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
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

        st.plotly_chart(fig, width='stretch')

    with c2:
        wc_fig = generate_wordcloud(st.session_state.selected_mountain)
        
        if wc_fig:
            st.plotly_chart(wc_fig, width='stretch')
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

elif st.session_state.view_mode == "course":
    st.markdown("### 🥾 등산로 코스")
    
    mountain_trails = df_trails[df_trails['산이름'] == st.session_state.selected_mountain].copy()
    
    if mountain_trails.empty:
        st.warning(f"{st.session_state.selected_mountain}의 등산로 데이터가 없습니다.")
    else:
        st.caption(f"총 {len(mountain_trails)}개의 등산로가 있습니다.")
        st.write("")
        
        trail_df = mountain_trails.copy()
        trail_df["코스명"] = trail_df["코스명"].fillna("코스").astype(str)
        trail_names = trail_df["코스명"].tolist()
        
        default_selection = None
        if st.session_state.selected_course in trail_names:
            default_selection = st.session_state.selected_course
        
        picked = st.pills(
            "코스 선택",
            trail_names,
            selection_mode="single",
            default=default_selection,
            key=f"trail_pills_{st.session_state.selected_mountain}",
        )
        
        if picked:
            if picked != st.session_state.selected_course:
                st.session_state.selected_course = picked
                st.session_state.selected_trail_data = trail_df.loc[trail_df["코스명"] == picked].iloc[0]
                st.rerun()
        else:
            if st.session_state.selected_course is not None:
                st.session_state.selected_course = None
                st.session_state.selected_trail_data = None
        
        st.write("")
        
        if not st.session_state.selected_course:
            st.info("코스를 하나 선택하면 아래에 코스 상세 정보가 나타납니다.")
        else:
            show_trail_detail(st.session_state.selected_trail_data, df_infra)
