import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import os  # 경로 설정을 위해 추가

# =========================
# Page config
# =========================
st.set_page_config(page_title="등산로 추천 챗봇", page_icon="💬", layout="wide")

# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
      .title-row{ display:flex; align-items:center; gap:10px; margin-top: 8px; margin-bottom: 6px; }
      .title-row .emoji{font-size:34px;}
      .title-row .title{font-size:34px; font-weight:800;}
      .subtext{color:#555; font-size:16px; line-height:1.6;}
      .divider{margin: 14px 0 18px 0; border-bottom:1px solid #e6e6e6;}
      .hintbox{ background:#f3f3f3; border-radius:16px; padding:14px 16px; margin: 8px 0 18px 0; }
      .hintchip{ display:inline-block; padding:6px 10px; border-radius:999px; background:#e7efe7; margin-right:8px; margin-top:8px; font-size:13px; color:#2a5a2a; }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Header area
# =========================
st.markdown(
    """
    <div class="title-row">
      <div class="emoji">💬</div>
      <div class="title">등산로 추천</div>
    </div>
    <div class="divider"></div>
    <div class="subtext">
      우리나라 100대 명산 데이터에 기반하여 딱 맞는 등산로를 추천해 드립니다.<br/>
      희망 난이도, 테마(뷰/힐링/가족 등), 이동수단을 알려주세요!
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hintbox">
      <div style="font-weight:700; margin-bottom:8px;">이렇게 물어보세요!</div>
      <span class="hintchip">초보 / 2시간 이내 / 뷰 좋은 코스 추천해줘</span>
      <span class="hintchip">가족이랑 가기 좋고 주차 편한 곳 어디야?</span>
      <span class="hintchip">대중교통으로 갈 수 있는 힐링 코스</span>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# 1. 데이터 로드 및 전처리 (경로 수정됨)
# =========================
@st.cache_resource
def load_and_process_data():
    """
    CSV와 JSON 파일을 읽어서 LLM에게 넘겨줄 텍스트 문자열(Context)로 변환합니다.
    pages 폴더 밖의 data 폴더를 참조하도록 경로를 설정합니다.
    """
    try:
        # ---------------------------------------------------------
        # [경로 설정 로직]
        # 현재 파일(chat.py)의 절대 경로를 구합니다.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 상위 폴더(대시보드)로 이동 후 data 폴더로 들어갑니다.
        data_dir = os.path.join(current_dir, "..", "data")
        
        # 실제 파일 경로 완성
        path_trails = os.path.join(data_dir, "100mountains_dashboard.csv")
        path_mountains = os.path.join(data_dir, "mountain.csv")
        path_keywords = os.path.join(data_dir, "mountain_keywords.json")
        # ---------------------------------------------------------

        # 데이터 읽기
        df_trails = pd.read_csv(path_trails)
        df_mountains = pd.read_csv(path_mountains)
        
        with open(path_keywords, "r", encoding="utf-8") as f:
            keywords_data = json.load(f)
            
        # 클러스터 설명 매핑
        cluster_map = {
            0: "계절매력(꽃, 단풍, 설경 등)",
            2: "탁 트인 전망, 사진 명소",
            3: "가족 동반, 편안한 인프라",
            4: "숲길, 힐링, 피톤치드",
            5: "오지, 숨은 명소, 한적함"
        }

        # LLM에게 주입할 데이터 텍스트 생성
        context_text = "아래는 네가 참고해야 할 **대한민국 100대 명산 등산로 데이터베이스**야. 이 정보에 기반해서만 답변해.\n\n"
        
        # 등산로 정보를 하나씩 텍스트로 변환
        for _, row in df_trails.iterrows():
            m_name = row['산이름']
            c_name = row['코스명']
            
            # 산 기본 정보
            m_info = df_mountains[df_mountains['mountain_name'] == m_name]
            desc = m_info.iloc[0]['description'] if not m_info.empty else "설명 없음"
            loc = m_info.iloc[0]['location'] if not m_info.empty else ""
            
            # 키워드 정보 (Top 5)
            m_keywords = keywords_data.get(m_name, {})
            sorted_keys = sorted(m_keywords, key=m_keywords.get, reverse=True)[:5]
            keywords_str = ", ".join(sorted_keys)
            
            # 클러스터 해석
            cluster_desc = cluster_map.get(row['Cluster'], "복합 매력")

            # 정보 블록 구성
            course_info = f"""
            ================================================================
            [데이터 ID]: {m_name}_{c_name}
            [산 이름]: {m_name}   <-- 이 이름을 정확히 확인하세요.
            [코스명]: {c_name}
            [위치]: {loc}
            [특징/테마]: {cluster_desc} (특출매력: {row['특출매력']})
            [난이도]: {row['난이도']} (세부: {row['세부난이도']})
            [소요시간]: {row['예상시간']} (왕복/편도 확인 필요, 총거리: {row['총거리_km']}km)
            [대중교통 접근성 점수]: {row['정류장_접근성점수']}점 (정류장명: {row['정류장명']})
            [주차 접근성 점수]: {row['주차장_접근성점수']}점 (주차장명: {row['주차장명']})
            [주요 키워드]: {keywords_str}
            [산 설명]: {desc}
            ================================================================
            """
            context_text += course_info
            
        return context_text

    except Exception as e:
        # 에러 발생 시 화면에 경로와 에러 메시지 출력 (디버깅용)
        st.error(f"데이터 로딩 실패! 경로를 확인해주세요.\n참조하려던 경로: {data_dir}\n에러: {e}")
        return ""

# 데이터 로드 실행
data_context = load_and_process_data()

# =========================
# Secrets & Client
# =========================
def load_gemini_secrets():
    try:
        api_key = st.secrets["gemini"]["GEMINI_API_KEY"]
        model = st.secrets["gemini"].get("model", "gemini-2.5-flash")
        return api_key, model
    except Exception:
        return None, None

api_key, gemini_model = load_gemini_secrets()

if not api_key:
    st.error("API 키 설정이 필요합니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

@st.cache_resource
def get_client(_api_key: str):
    return genai.Client(api_key=_api_key)

client = get_client(api_key)

# =========================
# 2. System Instruction 구성
# =========================
if data_context: # 데이터가 정상적으로 로드되었을 때만 프롬프트 구성
    system_prompt = f"""
    너는 '대한민국 100대 명산 등산로 추천 봇'이야.

    🚨 **[매우 중요 주의사항]** 🚨
    1. **산 이름 혼동 금지**: '가리산'과 '가리왕산', '덕유산'과 '덕숭산' 같이 이름이 비슷한 산들이 있다.
    2. 사용자가 '가리산'을 물어봤다면, 반드시 **[산 이름]: 가리산** 이라고 적힌 구역의 정보만 가져와야 한다.
    3. 절대로 이름이 비슷한 다른 산의 코스명이나 설명을 섞어서 답변하지 마라.
    4. 답변하기 전에 코스명이 해당 산의 코스가 맞는지 한 번 더 검증해라.

    반드시 아래 제공된 **[데이터베이스]**에 있는 내용에 기반해서 답변해야 해.
    데이터에 없는 내용은 지어내지 말고 "해당 조건에 맞는 정보가 데이터에 없습니다"라고 말해.

    **답변 가이드라인:**
    1. 사용자의 질문에서 조건(난이도, 시간, 이동수단, 테마 등)을 파악해.
    2. [데이터베이스]에서 가장 적합한 코스 1~3개를 찾아서 추천해.
    3. 추천할 때는 **산 이름, 코스명, 추천 이유(키워드/테마 활용), 예상 시간, 난이도**를 명시해.
    4. '대중교통'을 물어보면 '정류장_접근성점수'가 높거나(8점 이상 등) 정류장명이 명시된 곳을 우선 추천해.
    5. '주차'를 물어보면 '주차장_접근성점수'가 높은 곳을 추천해.
    6. 톤앤매너: 친절하고 이모지를 적절히 사용해서 등산을 권유하는 느낌으로.

    **[데이터베이스 시작]**
    {data_context}
    **[데이터베이스 끝]**
    """
else:
    system_prompt = "데이터 로딩에 실패했습니다. 관리자에게 문의하세요."

generation_config = types.GenerateContentConfig(
    temperature=0.7,
    system_instruction=system_prompt
)

# =========================
# Session State & Chat Setup
# =========================
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(model=gemini_model, config=generation_config)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 🏔️\n데이터 기반으로 분석된 **100대 명산 등산로**를 추천해 드릴게요.\n\n어떤 산행을 원하시나요? (예: 초보자용 힐링 코스, 대중교통 가능한 뷰 맛집 등)"
        }
    ]

# =========================
# Controls
# =========================
col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.chat = client.chats.create(model=gemini_model, config=generation_config)
        st.session_state.messages = [
            {"role": "assistant", "content": "대화를 새로 시작합니다! 원하시는 조건을 말씀해주세요. 😊"}
        ]
        st.rerun()

# =========================
# Chat UI Loop
# =========================
chat_container = st.container(height=600)

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

prompt = st.chat_input("질문을 입력하세요...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""
            try:
                for chunk in st.session_state.chat.send_message_stream(prompt):
                    if getattr(chunk, "text", None):
                        full_response += chunk.text
                        placeholder.markdown(full_response)
                
            except Exception as e:
                full_response = f"⚠️ 오류 발생: {e}"
                placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})