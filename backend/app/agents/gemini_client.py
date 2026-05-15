"""
Gemini Client — Multi-Model Singleton.

Smart Routing pattern (Anthropic, OpenAI, Perplexity uses this).

Tier'a göre Gemini modeli seç:
- ModelTier.FAST: Hızlı görevler (parsing, simple Q&A, grounding)
- ModelTier.PRO: Karmaşık reasoning (synthesis, audit, decision making)

Production-grade pattern: Stripe, OpenAI, Anthropic tarafında günlük kullanım.

Bu module 3 model factory sağlar:
1. get_gemini_model() — Basic text generation
2. get_grounded_model() — Google Search Grounding ile
3. invoke_with_retry() — Network/transient error retry wrapper
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Model Tiers — Smart Routing
# ============================================================
class ModelTier(str, Enum):
    """
    Model tier'ları — görev tipine göre seçim.

    FAST: Yüksek throughput, düşük latency. Basit task'lar için.
        - Doğal dil → JSON parsing
        - Grounding ile web tarama
        - Hızlı doğrulama (link, format)
        - Function calling (model küçük rol oynar)

    PRO: En güçlü reasoning. Karmaşık task'lar için.
        - Multi-source synthesis (Strategy)
        - Meta-reasoning (Auditor)
        - 1M+ context window gereken işler
        - Reflexion pattern (self-criticism)
    """

    FAST = "fast"
    PRO = "pro"


# ============================================================
# Basic Model Factory (No Tools)
# ============================================================
@lru_cache(maxsize=10)
def get_gemini_model(
    tier: ModelTier = ModelTier.FAST,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> BaseChatModel:
    """
    Tier'a göre Gemini model instance üret veya cache'den al.

    Args:
        tier: Model tier (FAST | PRO).
        temperature: 0.0 (deterministic) - 1.0 (creative).
        max_tokens: Maks output token (None = default).
        json_mode: True → response JSON formatında olur.

    Returns:
        ChatGoogleGenerativeAI: LangChain-uyumlu Gemini wrapper.

    Example:
        >>> # Hızlı parsing için
        >>> fast_model = get_gemini_model(
        ...     tier=ModelTier.FAST,
        ...     temperature=0.2,
        ...     json_mode=True,
        ... )
        >>>
        >>> # Karmaşık reasoning için
        >>> pro_model = get_gemini_model(
        ...     tier=ModelTier.PRO,
        ...     temperature=0.5,
        ... )
    """
    # Tier'a göre model seç
    model_name = (
        settings.GEMINI_MODEL_PRO
        if tier == ModelTier.PRO
        else settings.GEMINI_MODEL_FAST
    )

    kwargs = {
        "model": model_name,
        "google_api_key": settings.GEMINI_API_KEY,
        "temperature": temperature,
        "max_retries": 3,
    }

    if max_tokens is not None:
        kwargs["max_output_tokens"] = max_tokens

    if json_mode:
        kwargs["response_mime_type"] = "application/json"

    instance = ChatGoogleGenerativeAI(**kwargs)

    logger.info(
        "gemini_model_initialized",
        tier=tier.value,
        model=model_name,
        temperature=temperature,
        json_mode=json_mode,
    )

    return instance


# ============================================================
# Grounded Model Factory (Google Search)
# ============================================================
def get_grounded_model(
    tier: ModelTier = ModelTier.FAST,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> BaseChatModel:
    """
    Google Search Grounding ile Gemini model.

    Web'den gerçek zamanlı bilgi çekebilir. ResearchAgent ve MarketAgent
    bunu kullanır.

    KRİTİK: `bind_tools` yerine `bind` kullanıyoruz çünkü Grounding +
    JSON mode kombinasyonu için bu syntax gerekli. Aksi takdirde Gemini
    sadece tool call döner, text dönmez.

    Resmi LangChain docs (Şubat 2026):
    > "To get structured output and search grounding in a single call,
    >  use .bind() with response_mime_type instead of with_structured_output."

    Args:
        tier: Model tier (genelde FAST yeterli — Grounding native).
        temperature: Düşük tutuyoruz (0.3) — factual sonuç istiyoruz.
        json_mode: True → response_mime_type=application/json.

    Returns:
        Grounding tool'lu ChatGoogleGenerativeAI instance.

    Example:
        >>> model = get_grounded_model(tier=ModelTier.FAST, json_mode=True)
        >>> response = await model.ainvoke([
        ...     HumanMessage(content="55 inç TV önerisi 25K bütçe")
        ... ])
        >>> # response.content içinde JSON string olacak
    """
    model_name = (
        settings.GEMINI_MODEL_PRO
        if tier == ModelTier.PRO
        else settings.GEMINI_MODEL_FAST
    )

    base_model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.GEMINI_API_KEY,
        temperature=temperature,
        max_retries=3,
    )

    # Modern LangChain syntax: .bind() ile hem tool hem mime type
    # bind_tools(...) JSON mode'u suppress ediyor, kullanma!
    bind_kwargs: dict = {
        "tools": [{"google_search": {}}],
    }
    if json_mode:
        bind_kwargs["response_mime_type"] = "application/json"

    grounded = base_model.bind(**bind_kwargs)

    logger.info(
        "grounded_model_initialized",
        tier=tier.value,
        model=model_name,
        tool="google_search",
        json_mode=json_mode,
    )

    return grounded


# ============================================================
# Retry Wrapper (Network / Transient Errors)
# ============================================================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
async def invoke_with_retry(
    model: BaseChatModel,
    messages: list,
) -> str:
    """
    Gemini'ye retry logic ile çağrı yap.

    Network hataları, timeout'lar için exponential backoff.

    NOT: Grounded model'ler için bu wrapper'ı KULLANMA — onlar kendi
    retry logic'ine sahip (BaseAgent._invoke_with_grounded_retry).
    Bu fonksiyon basic text generation için.

    Args:
        model: Gemini model instance.
        messages: LangChain message list.

    Returns:
        Model cevabının içeriği (str).
    """
    try:
        response = await model.ainvoke(messages)
        return response.content
    except Exception as exc:
        logger.error(
            "gemini_invoke_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise