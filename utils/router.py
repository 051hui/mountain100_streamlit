# router.py
import re


REFINE_PATTERNS = [
    r"더\s*(한적|조용|사람\s*적)",
    r"더\s*(쉬운|가벼운|초보)",
    r"더\s*(뷰|경치)",
    r"(별로|마음에\s*안|다른\s*거|다시|바꿔)",
    r"(너무\s*멀|가까운\s*걸로|거리)",
    r"(좀\s*더|조금\s*더|덜)",
]

EXPLAIN_PATTERNS = [
    r"(왜|이유|근거).*(추천|나왔|골랐)",
    r"(설명).*(해줘|해봐|해주세요)",
    r"(이\s*결과).*(왜|이유)",
    r"(어떻게|무슨\s*기준)",
]

RECOMMEND_PATTERNS = [
    r"(추천|갈만한|어디\s*가|코스|등산로)",
    r"(찾아줘|골라줘|제안해줘|보여줘)",
    r"(어디|어느|뭐)\s*(좋|괜찮)",
]

QUESTION_PATTERNS = [
    r"(뭐야|어때|가능|있어|없어|언제|어떻게)",
    r"(기준|정의|의미|특징)",
    r"(몇\s*개|얼마나|어느\s*정도)",
]


def route_intent(msg: str) -> str:
    """
    사용자 메시지의 의도를 분류
    
    Args:
        msg: 사용자 입력 메시지
        
    Returns:
        "recommend", "refine", "explain", "question", "other" 중 하나
    """
    m = msg.strip()
    
    # 순서가 중요: refine은 recommend보다 먼저 체크해야 함
    if any(re.search(p, m) for p in REFINE_PATTERNS):
        return "refine"
    
    if any(re.search(p, m) for p in EXPLAIN_PATTERNS):
        return "explain"
    
    if any(re.search(p, m) for p in RECOMMEND_PATTERNS):
        return "recommend"
    
    if any(re.search(p, m) for p in QUESTION_PATTERNS):
        return "question"
    
    return "other"
