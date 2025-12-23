import streamlit as st
from google import genai
from google.genai import types

# =========================
# Page config
# =========================
st.set_page_config(page_title="등산로 추천 챗봇", page_icon="💬", layout="wide")

# =========================
# Simple CSS (layout 느낌만)
# =========================
st.markdown(
    """
    <style>
      .title-row{
        display:flex; align-items:center; gap:10px;
        margin-top: 8px; margin-bottom: 6px;
      }
      .title-row .emoji{font-size:34px;}
      .title-row .title{font-size:34px; font-weight:800;}
      .subtext{color:#555; font-size:16px; line-height:1.6;}
      .divider{margin: 14px 0 18px 0; border-bottom:1px solid #e6e6e6;}
      .hintbox{
        background:#f3f3f3; border-radius:16px; padding:14px 16px;
        margin: 8px 0 18px 0;
      }
      .hintchip{
        display:inline-block; padding:6px 10px; border-radius:999px;
        background:#e7efe7; margin-right:8px; margin-top:8px;
        font-size:13px; color:#2a5a2a;
      }
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
      우리나라 100대 명산 중 어떤 산의 어떤 등산로가 내 레벨과 조건에 가장 부합할까요?<br/>
      희망 난이도, 테마(관광/가족/도전/뷰맛집 등), 이동수단(대중교통/자가용)을 알려주세요!<br/>
      100대 명산 챗봇이 추천해 드립니다 😊
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hintbox">
      <div style="font-weight:700; margin-bottom:8px;">예시로 이렇게 말해봐!</div>
      <span class="hintchip">초보 / 2~3시간 / 뷰 좋은 코스</span>
      <span class="hintchip">가족 / 완만 / 주차 편한 곳</span>
      <span class="hintchip">대중교통 / 당일치기 / 유명한 코스</span>
      <span class="hintchip">겨울 / 안전 / 짧게</span>
    </div>
    """,
    unsafe_allow_html=True
)

# =========================
# Secrets 체크
# =========================
def load_gemini_secrets():
    try:
        api_key = st.secrets["gemini"]["GEMINI_API_KEY"]
        model = st.secrets["gemini"].get("model", "gemini-2.5-flash")
        temperature = float(st.secrets["gemini"].get("temperature", 0.7))
        return api_key, model, temperature
    except Exception:
        return None, None, None

api_key, gemini_model, temperature = load_gemini_secrets()

if not api_key or api_key == "your-api-key-here":
    st.error("API 키가 없어요. `.streamlit/secrets.toml` 에 GEMINI_API_KEY를 설정해줘.")
    st.stop()

# =========================
# Client (캐싱)
# =========================
@st.cache_resource
def get_client(_api_key: str):
    return genai.Client(api_key=_api_key)

client = get_client(api_key)

generation_config = types.GenerateContentConfig(
    temperature=temperature,
)

# =========================
# Session State
# =========================
if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(model=gemini_model, config=generation_config)

if "messages" not in st.session_state:
    # 첫 인사(assistant 고정 메시지)
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕! 맞춤 등산로를 추천해주는 100대 명산 챗봇이야 🙂\n\n"
                       "원하는 **난이도**, **테마(관광/가족/도전/뷰맛집 등)**, **이동수단(대중교통/자가용)**을 알려줘!"
        }
    ]

# =========================
# Controls
# =========================
col_a, col_b, col_c = st.columns([2, 3, 4])
with col_a:
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.chat = client.chats.create(model=gemini_model, config=generation_config)
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "대화를 새로 시작할게! 원하는 조건(난이도/테마/이동수단)을 알려줘 🙂"
            }
        ]
        st.rerun()

with col_b:
    st.caption(f"모델: `{gemini_model}` / temp: `{temperature}`")

st.write("")  # spacing

# =========================
# Chat UI
# =========================
chat_container = st.container(height=650)

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

prompt = st.chat_input("원하는 등산 조건을 입력하세요 (예: 초보, 2시간, 뷰 좋은 코스, 대중교통)")

if prompt:
    # user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

        # assistant streaming
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                for chunk in st.session_state.chat.send_message_stream(prompt):
                    if getattr(chunk, "text", None):
                        full_response += chunk.text
                        placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"⚠️ 응답 생성 중 오류가 발생했어: `{e}`"
                placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
