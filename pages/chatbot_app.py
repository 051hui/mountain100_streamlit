# pages/챗봇추천.py
import pandas as pd
import streamlit as st
import os
import sys

# 상위 디렉토리의 utils를 import하기 위해
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.intent_classifier import classify_intent_with_llm, extract_mountain_name
from utils.llm_client import GeminiClient
from utils.translator import translate_plan
from utils.recommender import run_recommender
from utils.llm_prompts import (
    EXPLAIN_SYSTEM_PROMPT, 
    make_explain_user_prompt,
    QA_SYSTEM_PROMPT,
    make_qa_user_prompt
)


# -----------------------------------------------------------------------------
# 데이터 로드
# -----------------------------------------------------------------------------
@st.cache_data
def load_trails() -> pd.DataFrame:
    """등산로 데이터 로드"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        file_path = os.path.join(root_dir, 'data', '100mountains_dashboard.csv')
        
        df = pd.read_csv(file_path)
        
        full_columns = [
            '코스명', '산이름', '유형설명', '최고고도_m', '누적상승_m', '편도거리_km', '총거리_km', 
            '예상시간_분', '예상시간', '출발_lat', '출발_lon', '도착_lat', '도착_lon', 
            '난이도', '세부난이도', '난이도점수', '관광인프라점수', '주차장_접근성점수', 
            '정류장_접근성점수', '코스수', '가중치', '매력종합점수',
            '전망', '힐링', '사진', '등산로', '성취감', '계절매력', '특출매력', '특출점수',
            '주차장거리_m', '정류장거리_m', '위치', '주차장명', '정류장명', 'Cluster'
        ]
        
        if len(df.columns) == len(full_columns):
            df.columns = full_columns
        
        numeric_cols = [
            '난이도점수', '관광인프라점수', '매력종합점수', 
            '주차장거리_m', '정류장거리_m', '총거리_km', '최고고도_m', 'Cluster'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
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


# -----------------------------------------------------------------------------
# LLM 기반 자연스러운 응답 생성
# -----------------------------------------------------------------------------
def generate_conversational_recommendation(client: GeminiClient, user_input: str, plan: dict, results: pd.DataFrame) -> str:
    """LLM을 사용하여 자연스러운 추천 응답 생성"""
    
    if results.empty:
        return "죄송해요, 말씀하신 조건에 맞는 등산로를 찾지 못했습니다. 😅\n\n조건을 조금 완화해서 다시 말씀해주시겠어요?"
    
    # 추천 결과를 텍스트로 정리
    trails_info = []
    for idx, row in results.head(3).iterrows():
        trail_text = f"""
{row['산이름']} {row['코스명']} ({row['위치']})
- 난이도: {row['세부난이도']}
- 총 거리: {row['총거리_km']:.1f}km
- 고도: {row['최고고도_m']:.0f}m
- 예상 시간: {row['예상시간']}
- 인프라 점수: {row['관광인프라점수']:.1f}/10
- 매력도: {row['매력종합점수']:.1f}점
- 특출 매력: {row['특출매력']} ({row['특출점수']:.1f}점)
"""
        trails_info.append(trail_text.strip())
    
    trails_text = "\n\n".join(trails_info)
    
    system_prompt = """당신은 친근한 등산로 추천 챗봇 '등사니'입니다.

중요 규칙:
- 제공된 등산로 데이터만 사용하세요
- 데이터에 없는 산이나 코스를 언급하지 마세요
- 제공된 정보 외에는 절대 만들어내지 마세요

역할:
- 사용자의 요청을 분석한 결과를 자연스럽게 설명합니다
- 추천 등산로를 대화하듯이 소개합니다
- 각 등산로의 특징을 구체적으로 설명합니다
- 이모지를 적절히 사용하여 친근감을 줍니다

다양한 표현:
- 매번 다른 방식으로 시작 (조건 정리/바로 추천/공감/질문 등)
- 문장 길이와 이모지 사용량 변화
- 설명 순서 변경
- 추천 이유 표현 다양화

주의사항:
- 데이터에 없는 정보는 절대 만들지 마세요
- 제공된 등산로만 언급하세요
- 자연스럽고 친근한 말투 사용
- 매번 같은 패턴으로 답하지 마세요"""

    user_prompt = f"""사용자 요청: "{user_input}"

추천된 등산로 정보:
{trails_text}

위 정보를 바탕으로 자연스럽게 추천해주세요.
제공된 등산로만 언급하고, 매번 다른 스타일로 답변하세요."""

    try:
        response = client.complete_text(system_prompt, user_prompt, temperature=1.0)
        return response
    except Exception as e:
        fallback = f"""좋습니다! 사용자님의 조건에 맞는 등산로를 찾았어요.

🏔️ 추천 등산로

"""
        for idx, row in results.head(3).iterrows():
            fallback += f"""**{row['산이름']} {row['코스명']}** ({row['위치']})
추천 이유: 난이도 {row['세부난이도']}, {row['특출매력']} 점수가 높습니다.
특징: 총 {row['총거리_km']:.1f}km, 예상 시간 {row['예상시간']}

"""
        fallback += "\n어떠세요? 더 궁금한 점이나 다른 옵션이 필요하시면 말씀해주세요! 🌲"
        return fallback


def generate_trail_detail_explanation(client: GeminiClient, trail_name: str, trail_data: pd.Series) -> str:
    """특정 등산로에 대한 상세 설명 생성"""
    
    trail_info = f"""
등산로: {trail_data['산이름']} {trail_data['코스명']}
위치: {trail_data['위치']}
난이도: {trail_data['세부난이도']}
총 거리: {trail_data['총거리_km']:.1f}km
최고 고도: {trail_data['최고고도_m']:.0f}m
예상 시간: {trail_data['예상시간']}
주차장: {trail_data['주차장명']} (거리: {trail_data['주차장거리_m']:.0f}m)
정류장: {trail_data['정류장명']} (거리: {trail_data['정류장거리_m']:.0f}m)
관광 인프라 점수: {trail_data['관광인프라점수']:.1f}/10
매력 종합 점수: {trail_data['매력종합점수']:.1f}점
매력 요소: 전망 {trail_data['전망']:.1f}, 힐링 {trail_data['힐링']:.1f}, 사진 {trail_data['사진']:.1f}, 성취감 {trail_data['성취감']:.1f}, 계절매력 {trail_data['계절매력']:.1f}
특출 매력: {trail_data['특출매력']} ({trail_data['특출점수']:.1f}점)
"""
    
    system_prompt = """친근한 등산로 안내 챗봇입니다.

특정 등산로 상세 설명 시:
1. 위치와 기본 정보 소개
2. 난이도, 거리, 시간 등 실용 정보
3. 교통/접근성 정보
4. 매력 포인트 구체적 설명
5. 어떤 사람에게 추천하는지

자연스럽고 친근한 말투로, 모든 정보는 제공된 데이터에 기반하세요."""

    user_prompt = f"""다음 등산로에 대해 자세히 설명해주세요:

{trail_info}

사용자가 이 코스를 선택하는 데 도움이 되도록 상세하게 안내해주세요."""

    try:
        response = client.complete_text(system_prompt, user_prompt, temperature=0.7)
        return response
    except Exception as e:
        return f"""{trail_data['위치']}에 위치한 **{trail_data['산이름']} {trail_data['코스명']}**에 대해 설명해드릴게요.

**기본 정보**
- 난이도: {trail_data['세부난이도']}
- 총 거리: {trail_data['총거리_km']:.1f}km
- 최고 고도: {trail_data['최고고도_m']:.0f}m
- 예상 시간: {trail_data['예상시간']}

**접근성**
- 주차장: {trail_data['주차장명']} (입구에서 {trail_data['주차장거리_m']:.0f}m)
- 대중교통: {trail_data['정류장명']} (입구에서 {trail_data['정류장거리_m']:.0f}m)

**매력 포인트**
이 코스의 가장 큰 매력은 **{trail_data['특출매력']}**입니다.

더 궁금하신 점이 있으시면 말씀해주세요! 😊"""


# -----------------------------------------------------------------------------
# 메인 앱
# -----------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="등산로 추천 챗봇",
        page_icon="🏔️",
        layout="wide"
    )
    
    st.title("🏔️ 등산로 추천 챗봇")
    st.caption("자연스러운 대화로 나에게 맞는 등산로를 찾아보세요!")
    
    # 데이터 로드
    trails_df = load_trails()
    
    if trails_df.empty:
        st.error("데이터를 로드할 수 없습니다.")
        st.stop()
    
    # 세션 상태 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": """안녕하세요! 등산로 추천 챗봇 등사니입니다. ⛰️

사용자님께 딱 맞는 등산로를 추천해드리기 위해 몇 가지만 여쭤볼게요.

오늘은 어떤 등산을 하고 싶으신가요?

예를 들어:
• 힐링이 필요해서 조용하고 경치 좋은 곳
• 체력 단련 목적으로 좀 힘든 코스
• SNS 인증샷 찍기 좋은 명소
• 계절 풍경(단풍, 설경 등)을 즐기고 싶은 곳

어떤 스타일의 등산로를 원하시는지, 그리고 희망 난이도가 있다면 말씀해주세요!"""
        })
    
    if "last_plan" not in st.session_state:
        st.session_state.last_plan = None
    if "last_results" not in st.session_state:
        st.session_state.last_results = None
    
    # Gemini 클라이언트 초기화
    try:
        if "gemini" in st.secrets:
            api_key = st.secrets["gemini"]["GEMINI_API_KEY"]
            model = st.secrets["gemini"].get("GEMINI_MODEL", "gemini-2.0-flash-exp")
        elif "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            model = st.secrets.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
        else:
            st.error("⚠️ Gemini API 키가 설정되지 않았습니다.")
            st.stop()
        
        client = GeminiClient(api_key=api_key, model=model)
        
    except Exception as e:
        st.error(f"Gemini API 초기화 실패: {e}")
        st.stop()
    
    # 채팅 히스토리 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    user_input = st.chat_input("원하시는 등산 스타일을 입력해 주세요...")
    
    if user_input:
        # 사용자 메시지 추가 및 표시
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # 의도 분류 (LLM 기반)
        has_previous = st.session_state.last_results is not None and not st.session_state.last_results.empty
        intent = classify_intent_with_llm(client, user_input, has_previous_results=has_previous)
        
        # Assistant 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("생각 중..."):
                
                if intent in ("recommend", "refine"):
                    # 특정 산이 언급되었는지 확인
                    all_mountains = trails_df['산이름'].unique().tolist()
                    mentioned_mountain = extract_mountain_name(user_input, all_mountains)
                    
                    # LLM translation 수행
                    plan = translate_plan(
                        client, 
                        user_input, 
                        intent=intent,
                        last_plan=st.session_state.last_plan if intent == "refine" else None
                    )
                    
                    # 특정 산이 언급되었으면 필터링 추가
                    if mentioned_mountain:
                        if "exclude" not in plan:
                            plan["exclude"] = {"mountains": [], "trails": []}
                        all_mountains_set = set(trails_df['산이름'].unique())
                        other_mountains = all_mountains_set - {mentioned_mountain}
                        plan["exclude"]["mountains"] = list(other_mountains)
                    
                    # 추천 엔진 실행
                    results = run_recommender(trails_df, plan, top_k=5)
                    
                    # LLM 기반 자연스러운 응답 생성
                    response = generate_conversational_recommendation(
                        client, user_input, plan, results
                    )
                    
                    st.markdown(response)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    st.session_state.last_plan = plan
                    st.session_state.last_results = results
                
                elif intent == "explain":
                    if st.session_state.last_results is None or st.session_state.last_results.empty:
                        response = "아직 추천 결과가 없어요. 먼저 등산로를 추천받아보세요! 😊"
                        st.markdown(response)
                    else:
                        # 사용자가 언급한 산/코스 찾기
                        mentioned_trail = None
                        user_clean = user_input.replace(" ", "").replace("번", "").replace("코스", "")
                        
                        for idx, row in st.session_state.last_results.iterrows():
                            mountain_clean = row['산이름'].replace(" ", "")
                            course_clean = row['코스명'].replace(" ", "").replace("_", "")
                            
                            if (mountain_clean in user_clean or 
                                course_clean in user_clean or
                                row['산이름'] in user_input or 
                                row['코스명'] in user_input):
                                mentioned_trail = row
                                break
                        
                        if mentioned_trail is not None:
                            response = generate_trail_detail_explanation(
                                client, user_input, mentioned_trail
                            )
                        else:
                            try:
                                top_items = []
                                for idx, row in st.session_state.last_results.head(3).iterrows():
                                    top_items.append({
                                        '산이름': row['산이름'],
                                        '코스명': row['코스명'],
                                        '세부난이도': row['세부난이도'],
                                        '관광인프라점수': row['관광인프라점수'],
                                        '매력종합점수': row['매력종합점수']
                                    })
                                
                                response = client.complete_text(
                                    system_prompt=EXPLAIN_SYSTEM_PROMPT,
                                    user_prompt=make_explain_user_prompt(
                                        user_input, 
                                        st.session_state.last_plan, 
                                        top_items
                                    ),
                                    temperature=0.7
                                )
                            except Exception:
                                response = "이전에 추천해드린 등산로들은 사용자님의 조건에 가장 잘 맞는 곳들이에요! 😊"
                        
                        st.markdown(response)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                
                elif intent == "question":
                    # 특정 산에 대한 질문인지 확인
                    all_mountains = trails_df['산이름'].unique().tolist()
                    mentioned_mountain = extract_mountain_name(user_input, all_mountains)
                    
                    if mentioned_mountain:
                        mountain_trails = trails_df[trails_df['산이름'] == mentioned_mountain]
                        
                        if not mountain_trails.empty:
                            trail_info = f"""
{mentioned_mountain}에 대한 정보:
- 총 {len(mountain_trails)}개의 코스
- 평균 난이도: {mountain_trails['세부난이도'].mode()[0] if not mountain_trails['세부난이도'].mode().empty else '중급'}
- 평균 총 거리: {mountain_trails['총거리_km'].mean():.1f}km
- 평균 고도: {mountain_trails['최고고도_m'].mean():.0f}m
- 위치: {mountain_trails.iloc[0]['위치']}
- 주요 매력: {mountain_trails.iloc[0]['특출매력']}

코스 목록:
"""
                            for idx, row in mountain_trails.iterrows():
                                trail_info += f"- {row['코스명']}: 난이도 {row['세부난이도']}, 거리 {row['총거리_km']:.1f}km\n"
                            
                            system_prompt = """친근한 등산로 안내 챗봇입니다.
특정 산 질문 답변 시:
1. 기본 정보 소개
2. 코스들 간단히 설명
3. 사용자 조건(난이도 등) 언급 시 맞는 코스 추천
4. 더 자세한 추천 유도

자연스럽고 친근한 말투로 작성하세요."""
                            
                            user_prompt = f"""사용자 질문: "{user_input}"

{mentioned_mountain} 데이터:
{trail_info}

위 정보로 자연스럽게 답변하고, 조건 언급 시 맞는 코스 추천해주세요."""
                            
                            try:
                                response = client.complete_text(system_prompt, user_prompt, temperature=0.8)
                                st.markdown(response)
                            except Exception:
                                response = f"""{mentioned_mountain}에 대해 알려드릴게요!

{mentioned_mountain}는 {mountain_trails.iloc[0]['위치']}에 위치한 산으로, 총 {len(mountain_trails)}개의 코스가 있어요.

주요 매력은 **{mountain_trails.iloc[0]['특출매력']}**이고, 평균적으로 {mountain_trails['총거리_km'].mean():.1f}km 정도입니다.

어떤 스타일의 코스를 원하시는지 말씀해주시면 더 자세한 추천을 해드릴게요! 😊"""
                                st.markdown(response)
                        else:
                            response = f"죄송해요, {mentioned_mountain}에 대한 정보를 찾을 수 없네요. 😅"
                            st.markdown(response)
                    else:
                        data_summary = f"""전체 등산로 수: {len(trails_df)}개
평균 매력도: {trails_df['매력종합점수'].mean():.1f}점
평균 인프라 점수: {trails_df['관광인프라점수'].mean():.1f}점

산 목록 (일부): {', '.join([str(m).strip() for m in trails_df['산이름'].unique()[:10]])}..."""
                        
                        try:
                            response = client.complete_text(
                                system_prompt=QA_SYSTEM_PROMPT,
                                user_prompt=make_qa_user_prompt(user_input, data_summary),
                                temperature=0.7
                            )
                            st.markdown(response)
                        except Exception:
                            response = "죄송해요, 그 질문에 대한 정확한 답변이 어렵네요. 😅\n\n원하시는 등산 스타일을 말씀해주시면 맞춤 추천을 도와드릴게요!"
                            st.markdown(response)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })
                
                else:  # other
                    response = """죄송하지만 잘 이해하지 못했어요. 😅

저는 등산로 추천 전문 챗봇이에요. 다음과 같이 말씀해주시면 도움을 드릴 수 있어요:

• "힐링되는 조용한 곳 추천해줘"
• "가족과 가기 좋은 쉬운 코스"
• "전망 좋은 곳"
• "좀 더 쉬운 곳으로" (이전 추천 수정)
• "가리산 01 코스에 대해 더 설명해줘"

등산로나 산에 대해 궁금한 점이 있으시면 편하게 물어보세요! 😊"""
                    
                    st.markdown(response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })


if __name__ == "__main__":
    main()