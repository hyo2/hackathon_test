import os
import time
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Path, Body, Query
from pydantic import BaseModel
import httpx

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI

# LangGraph integration
try:
    from .animal_chat_graph import run_animal_chat
except Exception:
    run_animal_chat = None

# Local utilities (avoid circular imports with graph module)
from .utils import (
    save_user_checklist,
    get_user_checklist,
    extract_field,
    vision_base_url,
)

app = FastAPI(title="AI Chat Service")

logger = logging.getLogger("ai-chatbot")
logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def add_utf8_and_log(request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error: %s %s", request.method, request.url.path)
        raise
    duration_ms = (time.time() - start) * 1000
    response.headers.setdefault("Content-Type", "application/json; charset=utf-8")
    logger.info("%s %s -> %s %.2fms", request.method, request.url.path, response.status_code, duration_ms)
    return response

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    system_prompt: Optional[str] = None
    messages: List[ChatMessage]
    model: Optional[str] = None


class ChatByAnimalRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

class ChecklistRequest(BaseModel):
    gender: Optional[str] = None
    housing: Optional[str] = None
    family: Optional[str] = None
    time_with_pet: Optional[str] = None
    walking_freq: Optional[str] = None

# NOTE: In-memory checklist storage moved to utils.user_checklists

def _build_llm(model: Optional[str]):
    """Return (llm_or_none, model_name, is_fake) using LangChain ChatOpenAI.

    If OPENAI_API_KEY is missing, return (None, model_name, True) so caller can fallback.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = model or os.getenv("OPENAI_MODEL", "gpt-4o")
    if not api_key:
        return None, model_name, True
    # temperature tuned a bit lower for consistency
    llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=0.3)
    return llm, model_name, False

def _get_user_checklist(user_key: str = "default_user") -> dict:
    return get_user_checklist(user_key)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/checklist")
async def save_checklist(req: ChecklistRequest):
    """
    Save user checklist data for personalized chat responses.
    This data will be used for LangChain/LangGraph integration to provide 
    personalized recommendations and chat experiences.
    """
    try:
        user_key = "default_user"  # TODO: Improve with session/user management
        checklist_data = {
            "gender": req.gender,
            "housing": req.housing,
            "family": req.family,
            "time_with_pet": req.time_with_pet,
            "walking_freq": req.walking_freq,
        }
        save_user_checklist(checklist_data, user_key=user_key)
        return {"status": "success", "message": "체크리스트가 저장되었습니다", "data": checklist_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Checklist save failed: {e}")

def _fallback_reply(messages: List[ChatMessage], system_prompt: Optional[str] = None) -> str:
    last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
    base = "(fallback) OpenAI Key 미설정 또는 오류로 간단 응답: "
    if last_user:
        return base + f"질문 요약='{last_user[:80]}'"
    return base + "내용이 없습니다. 질문을 입력해 주세요."


@app.post("/chat")
async def chat(req: ChatRequest = Body(default=None)):
    try:
        if req is None:
            # Treat empty body as empty conversation
            req = ChatRequest(system_prompt=None, messages=[], model=None)
        llm, model_name, is_fake = _build_llm(req.model)
        if is_fake:
            return {"reply": _fallback_reply(req.messages, req.system_prompt), "mode": "fallback"}

        lc_messages: List[BaseMessage] = []
        if req.system_prompt:
            lc_messages.append(SystemMessage(content=req.system_prompt))
        for m in req.messages:
            if m.role == "user":
                lc_messages.append(HumanMessage(content=m.content))
            elif m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))
            elif m.role == "system":
                lc_messages.append(SystemMessage(content=m.content))
            else:
                lc_messages.append(HumanMessage(content=m.content))
        try:
            resp = await llm.ainvoke(lc_messages)
            reply = resp.content
        except Exception:
            reply = _fallback_reply(req.messages, req.system_prompt) + " (openai_error)"
            return {"reply": reply, "mode": "fallback"}
        return {"reply": reply, "mode": "openai"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@app.post("/chat/animal/{animal_id}")
async def chat_by_animal(animal_id: int = Path(..., ge=0), req: ChatByAnimalRequest = Body(default=None)):
    """
    Chat endpoint that builds the system prompt on the server using
    the animal profile fetched from ai-vision. Frontend should not send
    any system prompt.
    """
    try:
        # 1) Fetch animal profile
        async with httpx.AsyncClient(timeout=10.0) as client_http:
            resp = await client_http.get(f"{vision_base_url()}/animals/{animal_id}")
            resp.raise_for_status()
            animal = resp.json()

        info = animal.get("info", [])
        dog_name = extract_field(info, "이름") or "이름 미상"
        breed = extract_field(info, "품종") or "-"
        age = extract_field(info, "나이(추정)") or "-"
        gender = extract_field(info, "성별") or "-"
        weight = extract_field(info, "무게") or "-"
        color = extract_field(info, "털색") or "-"
        status = extract_field(info, "상태") or "-"
        serial = extract_field(info, "일련번호") or "-"
        notes = extract_field(info, "특이사항") or "-"

        profile_lines = "\n".join([
            f"이름: {dog_name}",
            f"품종: {breed}",
            f"나이(추정): {age}",
            f"성별: {gender}",
            f"무게: {weight}",
            f"털색: {color}",
            f"상태: {status}",
            f"일련번호: {serial}",
            f"특이사항: {notes}",
        ])

        region = os.getenv("SERVICE_REGION", "광주")
        preferred_domains = os.getenv("PREFERRED_DOMAINS", "kcanimal.or.kr")

        # Get user checklist for personalized system prompt
        checklist = _get_user_checklist()
        lifestyle_context = ""
        if checklist:
            lifestyle_context = f"""
            [사용자 라이프스타일 정보]
            - 성별: {checklist.get('gender', '정보없음')}
            - 주거환경: {checklist.get('housing', '정보없음')}
            - 가족구성: {checklist.get('family', '정보없음')}  
            - 반려동물과 함께할 시간: {checklist.get('time_with_pet', '정보없음')}
            - 산책 가능 빈도: {checklist.get('walking_freq', '정보없음')}

            위 사용자 정보를 고려하여 이 반려견과의 매칭도와 주의사항을 제공해주세요.
            """

        system_prompt = "\n".join([
            f"당신은 {region}시 유기견 보호소의 반려견 챗봇입니다.",
            "아래 프로필 정보에 기반하여 정중한 한국어로 답하고, 모르는 정보는 모른다고 답하세요.",
            "가능하면 친근한 강아지 말투(멍멍, 왈왈)를 사용하되 과하지 않게 해주세요.",
            f"링크나 참고자료를 언급할 경우 다음 도메인을 우선적으로 고려하세요: {preferred_domains}",
            "프로필에 없는 사실을 지어내지 마세요.",
            "대화가 충분히 진행되어 사용자가 추천서를 요청하거나 합의하면, 반드시 '추천서:'로 시작하는 단락 하나를 생성해 주세요.",
            "그 단락에는 입양자 라이프스타일 요약(대화에서 추출), 반려견의 강점, 주의사항, 첫 일주일 적응 팁을 간결히 포함하세요.",
            "",
            "[반려견 프로필]",
            profile_lines,
            lifestyle_context,
        ])

        # 2) Call OpenAI
        llm, model_name, is_fake = _build_llm(req.model if req else None)
        # Build LangChain messages
        lc_messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        if req and req.messages:
            for m in req.messages:
                if m.role == "user":
                    lc_messages.append(HumanMessage(content=m.content))
                elif m.role == "assistant":
                    lc_messages.append(AIMessage(content=m.content))
                elif m.role == "system":
                    lc_messages.append(SystemMessage(content=m.content))
                else:
                    lc_messages.append(HumanMessage(content=m.content))
        if is_fake:
            simple_req_msgs = req.messages if req else []
            return {"reply": _fallback_reply(simple_req_msgs, system_prompt), "mode": "fallback"}
        try:
            resp = await llm.ainvoke(lc_messages)
            reply = resp.content
        except Exception:
            simple_req_msgs = req.messages if req else []
            return {"reply": _fallback_reply(simple_req_msgs, system_prompt) + " (openai_error)", "mode": "fallback"}
        return {"reply": reply, "mode": "openai"}
    except httpx.HTTPError as he:
        raise HTTPException(status_code=502, detail=f"Failed to fetch animal profile: {he}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat (animal) failed: {e}")


@app.post("/chat/animal/{animal_id}/graph")
async def chat_by_animal_graph(
    animal_id: int = Path(..., ge=0),
    req: ChatByAnimalRequest = Body(default=None),
    include_sources: bool = Query(False, description="Include retrieval_context in response"),
    session_id: Optional[str] = Query(None, description="Client session/thread id for graph state"),
):
    """Graph 기반 LangChain/LangGraph 파이프라인을 사용하는 변형 엔드포인트.

    기존 /chat/animal/{id} 와 동일한 입력(messages) 구조를 사용하되
    서버측 그래프에서 프로필 fetch, checklist 로딩, 시스템 프롬프트 구성, LLM 호출을 수행.
    """
    if run_animal_chat is None:
        raise HTTPException(status_code=503, detail="LangGraph runtime not available (dependency missing)")
    try:
        messages = [m.model_dump() for m in (req.messages if req and req.messages else [])]
        result = await run_animal_chat(
            animal_id=animal_id,
            messages=messages,
            model_name=(req.model if req else None),
            session_id=session_id,
        )
        if not include_sources and "retrieval_context" in result:
            result.pop("retrieval_context", None)
        result["mode"] = "graph"
        return result
    except httpx.HTTPError as he:
        raise HTTPException(status_code=502, detail=f"Failed to fetch animal profile: {he}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph chat failed: {e}")