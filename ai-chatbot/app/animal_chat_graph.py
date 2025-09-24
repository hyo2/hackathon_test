from __future__ import annotations
from typing import List, TypedDict, Optional, Any
import os
import httpx

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_chroma import Chroma

from .utils import extract_field, vision_base_url, get_user_checklist


class GraphState(TypedDict, total=False):
    animal_id: int
    model_name: str
    messages: List[BaseMessage]
    animal_profile: dict
    checklist: dict
    retrieval_context: str
    system_prompt: str
    reply: str


async def fetch_animal_profile(state: GraphState) -> GraphState:
    animal_id = state["animal_id"]
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{vision_base_url()}/animals/{animal_id}")
        resp.raise_for_status()
        animal = resp.json()

    info = animal.get("info", [])
    profile = {
        "name": extract_field(info, "이름") or "이름 미상",
        "breed": extract_field(info, "품종") or "-",
        "age": extract_field(info, "나이(추정)") or "-",
        "gender": extract_field(info, "성별") or "-",
        "weight": extract_field(info, "무게") or "-",
        "color": extract_field(info, "털색") or "-",
        "status": extract_field(info, "상태") or "-",
        "serial": extract_field(info, "일련번호") or "-",
        "notes": extract_field(info, "특이사항") or "-",
    }
    return {**state, "animal_profile": profile}


async def load_checklist(state: GraphState) -> GraphState:
    checklist = get_user_checklist()
    return {**state, "checklist": checklist}


def build_system_prompt(state: GraphState) -> GraphState:
    p = state["animal_profile"]
    checklist = state.get("checklist") or {}
    region = os.getenv("SERVICE_REGION", "광주")
    preferred_domains = os.getenv("PREFERRED_DOMAINS", "kcanimal.or.kr")
    retrieval_context = state.get("retrieval_context") or ""

    profile_lines = "\n".join([
        f"이름: {p['name']}",
        f"품종: {p['breed']}",
        f"나이(추정): {p['age']}",
        f"성별: {p['gender']}",
        f"무게: {p['weight']}",
        f"털색: {p['color']}",
        f"상태: {p['status']}",
        f"일련번호: {p['serial']}",
        f"특이사항: {p['notes']}",
    ])

    lifestyle_context = ""
    if checklist:
        lifestyle_context = f"""
        [사용자 라이프스타일 정보]
        - 성별: {checklist.get('gender','정보없음')}
        - 주거환경: {checklist.get('housing','정보없음')}
        - 가족구성: {checklist.get('family','정보없음')}
        - 반려견과 함께할 시간: {checklist.get('time_with_pet','정보없음')}
        - 산책 가능 빈도: {checklist.get('walking_freq','정보없음')}
        위 정보를 고려해 매칭도, 주의사항, 적응 팁을 자연스럽게 반영하세요.
        """

    system_prompt_core = "\n".join([
        f"당신은 {region}시 유기견 보호소의 반려견 챗봇입니다.",
        "프로필 기반으로 정중한 한국어로 답하고 모르는 정보는 모른다고 말하세요.",
        "과하지 않은 친근한 강아지 말투(멍멍, 왈왈)를 약간 섞되 남용하지 않습니다.",
        f"링크/참고자료 언급 시 우선 도메인: {preferred_domains}",
        "지어내지 마세요.",
        "대화가 충분히 진행되어 사용자가 추천서/입양서 같은 것을 원하면 '추천서:' 로 시작하는 단락 1개 생성.",
        "",
        "[반려견 프로필]",
        profile_lines,
        lifestyle_context,
    ])
    if retrieval_context:
        system_prompt = system_prompt_core + "\n\n[지식 기반 발췌]\n" + retrieval_context
    else:
        system_prompt = system_prompt_core
    return {**state, "system_prompt": system_prompt}


async def retrieve_context(state: GraphState) -> GraphState:
    """Load persisted Chroma vector store and retrieve top-k chunks for current query.

    Query 전략:
      - 최근 사용자 메시지(content role=user) 중 마지막 것을 쿼리로 사용
    실패 (저장소 없음 등) 시 retrieval_context 비워둔 채 진행.
    """
    try:
        persist_dir = os.getenv("DOG_VECTOR_STORE_DIR", "ai-chatbot/dog_vector_store")
        collection_name = os.getenv("DOG_VECTOR_COLLECTION", "dog_knowledge")
        if not os.path.exists(os.path.join(persist_dir, "chroma.sqlite3")):
            return state  # No store available
        # Find last user message
        query = None
        for msg in reversed(state.get("messages", [])):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
        if not query:
            return state
        embeddings = OpenAIEmbeddings(model=os.getenv("DOG_EMBED_MODEL", "text-embedding-3-large"))
        vs = Chroma(
            embedding_function=embeddings,
            collection_name=collection_name,
            persist_directory=persist_dir,
        )
        retriever = vs.as_retriever(search_kwargs={"k": int(os.getenv("DOG_RETRIEVAL_K", "4"))})
        docs = retriever.invoke(query)
        # Build concise context block
        lines = []
        for d in docs:
            src = d.metadata.get("source") if isinstance(d.metadata, dict) else d.metadata
            snippet = d.page_content.strip().replace("\n", " ")
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            lines.append(f"- ({src}) {snippet}")
        context_block = "\n".join(lines)
        return {**state, "retrieval_context": context_block}
    except Exception:
        # Silent fallback; do not break main flow
        return state


async def call_llm(state: GraphState) -> GraphState:
    model_name = state.get("model_name") or os.getenv("OPENAI_MODEL", "gpt-4o")
    api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(model=model_name, api_key=api_key, temperature=0.2)

    system_msg = SystemMessage(content=state["system_prompt"])
    msgs = [system_msg] + state["messages"]
    resp = await llm.ainvoke(msgs)
    return {**state, "reply": resp.content, "messages": msgs + [resp]}


def postprocess(state: GraphState) -> GraphState:
    # Placeholder for future loops / recommendation generation enforcement
    return state


# Graph build
_builder = StateGraph(GraphState)
_builder.add_node("fetch_animal_profile", fetch_animal_profile)
_builder.add_node("load_checklist", load_checklist)
_builder.add_node("retrieve_context", retrieve_context)
_builder.add_node("build_system_prompt", build_system_prompt)
_builder.add_node("call_llm", call_llm)
_builder.add_node("postprocess", postprocess)

_builder.set_entry_point("fetch_animal_profile")
_builder.add_edge("fetch_animal_profile", "load_checklist")
_builder.add_edge("load_checklist", "retrieve_context")
_builder.add_edge("retrieve_context", "build_system_prompt")
_builder.add_edge("build_system_prompt", "call_llm")
_builder.add_edge("call_llm", "postprocess")
_builder.add_edge("postprocess", END)

_memory = MemorySaver()
chat_graph = _builder.compile(checkpointer=_memory)


async def run_animal_chat(animal_id: int, messages: list, model_name: Optional[str] = None, session_id: Optional[str] = None):
    # Convert simple dict messages into LangChain messages
    lc_msgs: List[BaseMessage] = []
    for m in messages:
        role = m.get("role")
        if role == "user":
            lc_msgs.append(HumanMessage(content=m.get("content", "")))
        elif role == "assistant":
            lc_msgs.append(AIMessage(content=m.get("content", "")))
        elif role == "system":
            lc_msgs.append(SystemMessage(content=m.get("content", "")))
        else:
            # Default to human if unknown role
            lc_msgs.append(HumanMessage(content=m.get("content", "")))

    initial_state: GraphState = {
        "animal_id": animal_id,
        "messages": lc_msgs,
    }
    if model_name:
        initial_state["model_name"] = model_name

    # Provide a thread/session id for the MemorySaver checkpointer
    thread_id = session_id or f"animal-{animal_id}"  # simple deterministic id
    final_state = await chat_graph.ainvoke(initial_state, config={"configurable": {"thread_id": thread_id}})
    return {
        "reply": final_state.get("reply", ""),
        "message_count": len(final_state.get("messages", [])),
        "retrieval_context": final_state.get("retrieval_context"),
        "thread_id": thread_id,
    }
