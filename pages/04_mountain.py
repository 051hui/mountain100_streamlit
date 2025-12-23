# pages/04_mountain.py
import streamlit as st

st.set_page_config(layout="wide")

# -------------------------
# 스타일 (원하면 더 다듬기)
# -------------------------
st.markdown(
    """
    <style>
      .title-wrap { margin-bottom: 8px; }
      .subtle { color: #6b7280; font-size: 0.95rem; }
      .card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 16px;
        background: white;
      }
      .soft {
        background: #f9fafb;
      }
      .btn-row { margin-top: 12px; }
      .hr {
        margin: 22px 0 18px 0;
        border-top: 1px solid #e5e7eb;
      }
      .course-chip button {
        border-radius: 999px !important;
        padding: 4px 12px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# 세션 상태 초기화
# -------------------------
if "selected_mountain" not in st.session_state:
    st.session_state.selected_mountain = "가리산"  # 나중에 지도 클릭으로 바꿀 값
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "attraction"  # "attraction" or "course"
if "selected_course" not in st.session_state:
    st.session_state.selected_course = None

# -------------------------
# 상단 제목 + 설명
# -------------------------
st.markdown(
    f"""
    <div class="title-wrap">
      <h2>⛰️ 산 정보 조회</h2>
      <div class="subtle">원하시는 산을 선택해 주세요. (지금은 레이아웃 스켈레톤)</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# (A) 지도 영역: 지금은 빈 틀
# -------------------------
map_placeholder = st.container()
with map_placeholder:
    st.markdown('<div class="card soft">🗺️ 지도 영역 (추후 folium + CSV 좌표 + 클릭 이벤트 연결)</div>', unsafe_allow_html=True)
    st.caption("여기서 산 포인트 클릭 → st.session_state.selected_mountain 갱신 → 아래 정보 표시로 연결할 예정")

st.write("")  # 간격

# -------------------------
# (B) 산 상세 기본 정보 카드 (사진/설명)
# -------------------------
left, right = st.columns([1.15, 2.2], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"### ⛰️ {st.session_state.selected_mountain}  <span class='subtle'>카페/나중에 태그</span>", unsafe_allow_html=True)
    st.write("")
    st.markdown(
        """
        <div class="card soft" style="height: 210px; display:flex; align-items:center; justify-content:center;">
          <div style="font-size:28px; font-weight:700;">사진</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("나중에: 사진 URL/로컬 이미지 연결")
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("##### 위치 / 고도")
    st.write("강원도 홍천군, 강원도 춘천시")
    st.write("1050.9 m")
    st.write("")
    st.markdown("##### 소개")
    st.write("강원도에서 진달래가 가장 많이 피는 산으로 알려져 있고, ... (추후 데이터 연결)")
    st.markdown("</div>", unsafe_allow_html=True)

# -------------------------
# (C) 모드 버튼 2개: 매력 / 등산로
# -------------------------
st.write("")
b1, b2 = st.columns(2, gap="large")

def set_mode(mode: str):
    st.session_state.view_mode = mode
    if mode == "attraction":
        st.session_state.selected_course = None  # 모드 전환 시 코스 선택 초기화 (선호에 따라 제거 가능)

with b1:
    if st.button("매력 확인하기", use_container_width=True, type="secondary"):
        set_mode("attraction")

with b2:
    if st.button("등산로 코스 확인하기", use_container_width=True, type="secondary"):
        set_mode("course")

# -------------------------
# (D) 모드별 영역 렌더링
# -------------------------
st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

# ✅ 1) 매력 확인하기 모드
if st.session_state.view_mode == "attraction":
    st.markdown("### 🌟 매력 분석")
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<div class="card">레이더차트 (자리)</div>', unsafe_allow_html=True)
        st.caption("나중에 plotly/matplotlib 레이더차트 연결")

    with c2:
        st.markdown('<div class="card">워드클라우드 (자리)</div>', unsafe_allow_html=True)
        st.caption("나중에 wordcloud 이미지 연결")

    st.write("")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    metrics = [
        ("뷰·경관 지수", "8.5", "평균대비 -3.5%"),
        ("뷰·경관 지수", "7.5", "평균대비 -3.5%"),
        ("뷰·경관 지수", "7.4", "평균대비 +3.5%"),
        ("뷰·경관 지수", "8.2", "평균대비 -3.5%"),
        ("뷰·경관 지수", "5.6", "평균대비 +3.5%"),
        ("뷰·경관 지수", "6.2", "평균대비 +3.5%"),
    ]
    for col, (label, val, delta) in zip([m1, m2, m3, m4, m5, m6], metrics):
        col.metric(label, val, delta)

# ✅ 2) 등산로 코스 확인하기 모드
else:
    st.markdown("### 🥾 등산로 코스")
    st.caption("코스 버튼 → 코스 선택 → 아래 카드 표시")

    # 지금은 더미 코스 목록 (나중에 산별 코스 리스트로 교체)
    dummy_courses = [f"{st.session_state.selected_mountain}_{i:02d}" for i in range(1, 5)]

    chip_cols = st.columns(len(dummy_courses))
    for i, course_name in enumerate(dummy_courses):
        with chip_cols[i]:
            # "초록색 칩" 느낌은 Streamlit 기본 버튼으로 완벽히는 어렵고 CSS/컴포넌트로 보완 가능
            if st.button(course_name, use_container_width=True):
                st.session_state.selected_course = course_name

    # 코스를 아직 선택 안 했으면 안내만
    if not st.session_state.selected_course:
        st.info("코스를 하나 선택하면 아래에 코스 카드가 나타나요.")
    else:
        st.write("")
        st.markdown(f"#### 🥾 {st.session_state.selected_course} 코스")
        top_l, top_r = st.columns([1.2, 1.8], gap="large")

        with top_l:
            st.markdown('<div class="card soft" style="height:260px;">🗺️ 코스 지도 자리 (추후 GPX 시각화)</div>', unsafe_allow_html=True)
            st.caption("나중에: folium + GPX polyline / 또는 pydeck/leafmap 등으로 연결")

        with top_r:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("⏱️ 2시간 30분")
            st.write("⛰️ 1050.9 m")
            st.write("📏 10.8 km")
            st.write("⭐ 중상")
            st.write("🅿️ 주차장 / 🚻 화장실 (예시)")
            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        poi_type = st.radio(
            "주변 정보 보기",
            ["음식점", "카페", "숙박", "관광명소"],
            horizontal=True,
        )
        st.markdown(f'<div class="card soft">📍 {poi_type} 리스트/지도 자리 (추후 반경 데이터 연결)</div>', unsafe_allow_html=True)
