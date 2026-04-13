"""Intent router: classifies user queries to determine the retrieval strategy."""

from __future__ import annotations

import logging

from models.search import IntentType
from utils.llm import llm_generate

logger = logging.getLogger(__name__)

ROUTER_PROMPT = """Classify the user's message into exactly ONE category:

KNOWLEDGE - Questions about documents, policies, procedures, "how to", historical info
STRUCTURED - Questions about metrics, data, numbers, leads, sales, reports, KPIs
HYBRID - Questions that need BOTH document knowledge AND structured data
ACTION - Requests to DO something (create, update, assign, send, generate)
CONVERSATION - Greetings, thanks, general chat, conceptual questions not about specific data

User message: "{message}"

Respond with ONLY the category name (one word)."""

ROUTER_WITH_TABLES_PROMPT = """Classify the user's message into exactly ONE category:

KNOWLEDGE - Questions about documents, policies, procedures, "how to", historical info
STRUCTURED - Questions about metrics, data, numbers from these tables: {tables}
HYBRID - Questions that need BOTH document knowledge AND structured data
ACTION - Requests to DO something (create, update, assign, send, generate)
CONVERSATION - Greetings, thanks, general chat, conceptual questions not about specific data

User message: "{message}"

Respond with ONLY the category name (one word)."""


async def classify_intent(
    message: str,
    model: str = "gpt-4o-mini",
    db_tables_schema: str | None = None,
) -> IntentType:
    """Classify user message intent using a lightweight LLM call."""
    try:
        if db_tables_schema:
            prompt = ROUTER_WITH_TABLES_PROMPT.format(
                message=message[:500],
                tables=db_tables_schema,
            )
        else:
            prompt = ROUTER_PROMPT.format(message=message[:500])

        response = await llm_generate(
            prompt=prompt,
            model=model,
            temperature=0.0,
            max_tokens=10,
        )

        intent_str = response.strip().upper().split()[0]

        intent_map = {
            "KNOWLEDGE": IntentType.KNOWLEDGE,
            "STRUCTURED": IntentType.STRUCTURED,
            "HYBRID": IntentType.HYBRID,
            "ACTION": IntentType.ACTION,
            "CONVERSATION": IntentType.CONVERSATION,
        }

        intent = intent_map.get(intent_str, IntentType.KNOWLEDGE)
        logger.debug("Intent classified: %s -> %s", message[:50], intent.value)
        return intent

    except Exception as e:
        logger.warning("Intent classification failed: %s. Defaulting to KNOWLEDGE.", e)
        return IntentType.KNOWLEDGE
