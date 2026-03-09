"""
Роутер за чатбот - съвети за гребане и спортна подготовка.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from chat.prompts import ROWING_EXPERT_SYSTEM_PROMPT

router = APIRouter()


@router.get("/debug")
async def chat_debug():
    """Проверка дали API ключът се зарежда (не показва стойността)."""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("ABACUS_API_KEY")
    return {
        "key_loaded": bool(key and key.strip()),
        "base_url": os.getenv("ABACUS_BASE_URL") or "(default OpenAI)",
        "source": "ABACUS" if os.getenv("ABACUS_API_KEY") else ("OPENAI" if os.getenv("OPENAI_API_KEY") else "none")
    }


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    analysis_context: Optional[dict] = None  # Метрики от последния анализ


class ChatResponse(BaseModel):
    message: str


def _fallback_response(user_message: str, context: Optional[dict]) -> str:
    """Прост fallback при липса на API ключ - отговори на често срещани въпроси."""
    msg = user_message.lower().strip()
    key_hint = "Добавете OPENAI_API_KEY или ABACUS_API_KEY в backend/.env за AI съвети."
    if "план" in msg or "трениров" in msg:
        return f"За тренировъчен план за гребане препоръчвам: 3-4 седмично водни тренировки, 2 силови, 1 ден почивка. Седмица 1-2: база (ниска интензивност, дълги дистанции). Седмица 3: обем. Седмица 4: възстановяване. {key_hint}"
    if "техник" in msg or "гребане" in msg:
        return f"При гребане фокусирайте се на: 1) Catch - бързо хващане, ръце напред. 2) Drive - задвижване от краката, после торс, после ръце. 3) Recovery - обратен ред. Ротация на торса 25-50°, drive:recovery ≈ 1:2. {key_hint}"
    if "подготовк" in msg or "спорт" in msg:
        return f"Спортната подготовка за гребане включва: силова (leg press, deadlift, core), кардио (erg, бягане), гъвкавост (хамстринг, хипс). {key_hint}"
    return f"Здравейте! Мога да помагам с техника на гребане, тренировъчни планове и спортна подготовка. {key_hint}"


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Изпраща съобщения към чатбота и получава отговор.
    Може да се подаде analysis_context с метрики за персонализирани съвети.
    """
    # Поддръжка за OpenAI и Abacus.ai (RouteLLM - OpenAI съвместим)
    api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("ABACUS_API_KEY") or "").strip()
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("ABACUS_BASE_URL")
    if api_key and not base_url and os.getenv("ABACUS_API_KEY"):
        base_url = "https://routellm.abacus.ai/v1"  # Auto за Abacus
    last_user = next((m.content for m in reversed(request.messages) if m.role == "user"), "")

    if not api_key:
        return ChatResponse(message=_fallback_response(last_user, request.analysis_context))

    # Подготвяне на контекст от анализа (ако има)
    context_text = ""
    if request.analysis_context and request.analysis_context.get("metrics"):
        m = request.analysis_context["metrics"]
        context_text = f"\n\n[Контекст от последния анализ на техниката: Ротация на торса: {m.get('torso_rotation', {}).get('range_deg', 'N/A')}°; Drive/Recovery: 1:{1/(m.get('drive_recovery_ratio', {}).get('ratio', 0.5) or 0.5):.1f}; SPM: {m.get('stroke_rate', {}).get('spm', 'N/A')}; Симетрия: {m.get('symmetry', {}).get('symmetry_score', 'N/A')}%]"

    system_content = ROWING_EXPERT_SYSTEM_PROMPT
    if context_text:
        system_content += "\n\nАко потребителят пита за своята техника или резултати, използвай горния контекст от анализа."

    messages = [
        {"role": "system", "content": system_content}
    ]

    for msg in request.messages[-10:]:  # Последните 10 съобщения
        messages.append({"role": msg.role, "content": msg.content})

    try:
        from openai import OpenAI
        client_kw = {"api_key": api_key}
        if base_url:
            client_kw["base_url"] = base_url
        client = OpenAI(**client_kw)
        model = os.getenv("OPENAI_MODEL") or os.getenv("ABACUS_MODEL", "route-llm" if base_url else "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=0.7
        )
        reply = response.choices[0].message.content
        return ChatResponse(message=reply or "Не успях да генерирам отговор.")
    except Exception as e:
        return ChatResponse(
            message=f"Грешка при свързване с AI: {str(e)}. Проверете OPENAI_API_KEY и интернет връзката."
        )
