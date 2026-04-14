"""Base agent: orchestrates retrieval pipeline + LLM response + conversation memory."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional

from config.schema import AppConfig
from ingestion.conversation_memory import ConversationMemory
from ingestion.embedder import create_embedder
from retrieval.pipeline import RetrievalPipeline
from storage.base import BaseStorage
from agent.system_prompts import build_system_prompt
from agent.response_builder import (
    build_context,
    build_legal_context,
    get_sources,
    get_confidence,
    format_response_with_sources,
    sanitize_llm_response,
    format_live_source_results,
    format_vigencia_results,
)
from utils.llm import get_openai_client

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Stateless RAG agent that:
    1. Loads conversation history from storage per session
    2. Routes query through retrieval pipeline (RAG-first)
    3. Builds context from retrieved data
    4. Generates response using primary LLM
    5. Persists exchange back to conversation memory
    """

    def __init__(self, config: AppConfig, storage: BaseStorage):
        self.config = config
        self.storage = storage
        self.retrieval = RetrievalPipeline(config, storage)
        self.embedder = create_embedder(
            model=config.ingestion.embedding.model,
            use_cache=True,
        )
        self.memory = ConversationMemory(
            storage=storage,
            embedder=self.embedder,
            utility_model=config.agent.utility_model,
        )
        # TTL cache for the allow-list of loaded document titles.
        # Refreshed every 5 min or when invalidated manually after ingestion.
        self._allow_list_cache: Optional[List[str]] = None
        self._allow_list_cached_at: float = 0.0
        self._allow_list_ttl_s: float = 30.0  # 30 seconds — fast refresh after ingest

    async def _build_messages(
        self,
        message: str,
        session_id: str,
        history_limit: int = 10,
    ) -> tuple[List[Dict[str, str]], dict]:
        """Build the message list for the LLM, including system prompt and history.

        The retrieval query is enriched with conversation history so that short
        follow-up messages like "y si yo me robé una computadora" carry the
        context of the previous exchange (in this case, "despido"). Without this,
        the RAG would search only for "robo" and miss the laboral chunks.
        """

        # Step 1: Load conversation history FIRST (we need it for query expansion)
        history: list = []
        try:
            history = await self.storage.get_session_messages(session_id)
        except Exception as e:
            logger.debug("Could not load history for session %s: %s", session_id, e)

        # Step 2: Build a "contextualized query" for retrieval that combines
        # recent conversation context with the new user message. This helps
        # the RAG find relevant chunks even on short follow-up turns.
        retrieval_query = self._build_retrieval_query(message, history)

        # Step 3: Retrieve context using the enriched query
        retrieval_result = await self.retrieval.retrieve(
            query=retrieval_query,
            session_id=session_id,
        )

        # Step 3.5: Legal mode — if RAG didn't find good results,
        # ask LLM what norm is needed and auto-ingest it
        llm_ingested = []
        if self._is_legal_mode():
            has_good = retrieval_result.results and any(
                r.best_score > 0.5 for r in retrieval_result.results[:3]
            )
            if not has_good:
                llm_ingested = await self._identify_needed_norms_via_llm(message, retrieval_result)
                if llm_ingested:
                    self.invalidate_doc_cache()
                    # Re-run retrieval with new docs
                    retrieval_result = await self.retrieval.retrieve(
                        query=retrieval_query, session_id=session_id,
                    )
                    logger.info(f"Re-retrieval after LLM-identified ingest: {llm_ingested}")

        # Always preserve the user's actual message for display/logging purposes
        retrieval_result.query.original_query = message

        sources = get_sources(retrieval_result)
        confidence = get_confidence(retrieval_result)
        intent = (
            retrieval_result.query.intent.value
            if retrieval_result.query.intent
            else "knowledge"
        )

        # Legal mode: search live sources, auto-ingest missing norms, verify vigencia
        live_results = None
        vigencia_results = None
        is_legal = self._is_legal_mode()
        did_ingest = False

        if is_legal and intent != "conversation":
            # Phase 1: Search live sources + check vigencia
            live_results, vigencia_results = await self._enrich_with_legal_sources(
                retrieval_query, retrieval_result
            )

            # Phase 2: Auto-ingest any norms found in live sources that aren't in RAG
            if live_results:
                did_ingest = await self._auto_ingest_live_results(live_results)

            # Phase 3: If we ingested something, RE-RUN retrieval to pick up new chunks
            if did_ingest:
                self.invalidate_doc_cache()
                retrieval_result = await self.retrieval.retrieve(
                    query=retrieval_query,
                    session_id=session_id,
                )
                retrieval_result.query.original_query = message
                sources = get_sources(retrieval_result)
                confidence = get_confidence(retrieval_result)
                # Re-check vigencia with new retrieval results
                _, vigencia_results = await self._enrich_with_legal_sources(
                    retrieval_query, retrieval_result
                )
                logger.info("Re-ran retrieval after auto-ingest, new sources: %s", sources)

        # Build context: legal mode uses enriched context with live sources + vigencia
        if is_legal and (live_results or vigencia_results):
            context = build_legal_context(retrieval_result, live_results, vigencia_results)
            # Add live source names to the sources list
            if live_results:
                for lr in live_results:
                    name = f"{getattr(lr, 'titulo', '')} ({getattr(lr, 'source', '')})"
                    if name.strip(" ()"):
                        sources.append(name)
        else:
            context = build_context(retrieval_result)

        # Load the full list of documents in the corpus for the allow-list.
        # Cached with 5-min TTL: avoids hitting Postgres on every chat turn.
        loaded_doc_titles = await self._get_loaded_doc_titles()

        system_prompt = build_system_prompt(
            agent_name=self.config.agent.name,
            agent_role=self.config.agent.role,
            context=context,
            intent=intent,
            sources=sources,
            confidence=confidence,
            was_refined=retrieval_result.was_refined,
            refined_query=retrieval_result.refined_query,
            custom_template=self.config.agent.system_prompt_template,
            loaded_documents=loaded_doc_titles,
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        # Step 4: Append recent history so the LLM has full conversation context
        if history:
            tail = history[-(history_limit * 2):]
            for h in tail:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": message})

        meta = {
            "intent": intent,
            "sources": sources,
            "context": context,
            "retrieval_result": retrieval_result,
            "retrieval_query": retrieval_query,
            "loaded_documents": loaded_doc_titles,
            "vigencia_results": vigencia_results,
            "live_results": live_results,
            "llm_ingested": llm_ingested,
        }
        return messages, meta

    def _build_retrieval_query(self, message: str, history: list) -> str:
        """Combine recent conversation context with the new message.

        This is critical for follow-up turns. Example:
        - Previous: "me quieren despedir y cumplo mis funciones"
        - New: "pero me robé una computadora"
        - Combined: the second message is enriched with "despido / trabajo /
          empleador" context so vector search finds laboral chunks instead
          of treating "robo" as a pure penal term.
        """
        if not history:
            return message

        # Take the last 2-3 user messages (most recent context wins)
        recent_user_msgs = [
            h["content"] for h in history[-6:]
            if h.get("role") == "user"
        ]

        # If no prior user messages, just use the new one
        if not recent_user_msgs:
            return message

        # Concatenate previous user messages with the new one for retrieval.
        # We use the user side only (not the assistant) because:
        # 1. The user's words contain the situation
        # 2. The assistant's reply is verbose and would dilute embeddings
        previous_context = " ".join(recent_user_msgs[-2:])  # last 2 user turns
        combined = f"{previous_context} {message}"

        # Cap at ~500 chars to keep embedding tokens reasonable
        if len(combined) > 500:
            combined = combined[-500:]

        return combined

    async def chat(self, message: str, session_id: Optional[str] = None) -> Dict:
        """Process a user message and return the agent's response."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())

        # Legal mode: auto-ingest missing norms BEFORE building messages
        ingested_norms = []
        if self._is_legal_mode():
            ingested_norms = await self._auto_ingest_missing_norms(message)
            if ingested_norms:
                self.invalidate_doc_cache()

        messages, meta = await self._build_messages(message, session_id)
        if ingested_norms:
            meta["ingested_norms"] = ingested_norms

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
        )

        if response.usage:
            tracker.record_chat(
                model=self.config.agent.primary_model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                purpose="main_response",
                session_id=session_id,
            )

        assistant_message = response.choices[0].message.content.strip()
        assistant_message = sanitize_llm_response(
            assistant_message, allowed_documents=meta.get("loaded_documents")
        )

        # Append vigencia verification (legal mode)
        if meta.get("vigencia_results"):
            vigencia_lines = ["\n\n---\n**Vigencia Verificada:**"]
            for v in meta["vigencia_results"]:
                if v.estado == "VIGENTE":
                    vigencia_lines.append(f"- ✅ {v.tipo} {v.numero or ''} de {v.anio or ''} — VIGENTE")
                elif v.estado == "DEROGADA":
                    derog_info = ""
                    if v.derogaciones:
                        d = v.derogaciones[0]
                        derog_info = f" por {d.get('norma_tipo', '')} {d.get('norma_numero', '')} de {d.get('norma_anio', '')}"
                    vigencia_lines.append(f"- ❌ {v.tipo} {v.numero or ''} de {v.anio or ''} — DEROGADA{derog_info}")
                elif v.estado == "MODIFICADA":
                    vigencia_lines.append(f"- ⚠️ {v.tipo} {v.numero or ''} de {v.anio or ''} — MODIFICADA")
                elif not v.encontrada:
                    pass
                else:
                    vigencia_lines.append(f"- {v.tipo} {v.numero or ''} de {v.anio or ''} — {v.estado}")
            if len(vigencia_lines) > 1:
                assistant_message += "\n".join(vigencia_lines)

        assistant_message = format_response_with_sources(
            assistant_message, meta["retrieval_result"]
        )

        # ALWAYS persist chat history (lightweight) so the next message in
        # this session can see the previous turns.
        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent=meta["intent"],
            sources_used=meta["sources"],
        )

        # Optionally persist exchange to conversation memory (heavyweight, with
        # embeddings). Background task — does not block the response.
        self._schedule_memory_save(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent=meta["intent"],
            sources_used=meta["sources"],
        )

        return {
            "response": assistant_message,
            "intent": meta["intent"],
            "sources": meta["sources"],
            "session_id": session_id,
        }

    async def chat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Process a user message and stream the response with activity protocol.

        Yields prefixed chunks:
          [STATUS] step description   — agent activity (shown in thinking timeline)
          [INGEST] norm name          — downloading/indexing a norm
          [CONTENT] text              — first content token (marks end of thinking)
          [VIGENCIA] {...json}        — vigencia verification result
          [SOURCES] [...json]         — source citations
          [DURATION] Ns               — total thinking time
          (unprefixed)                — subsequent LLM tokens
        """
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())
        start_time = time.time()

        yield "[STATUS] Analizando consulta...\n"

        # Phase 0: Load Case State (accumulated context across all turns)
        from agent.case_state import CaseState
        case_state = CaseState(session_id)
        try:
            saved = await self.storage.get_case_state(session_id)
            if saved:
                case_state = CaseState(session_id, saved)
                logger.info(f"CaseState loaded: turn {case_state.turn_count}, {len(case_state.facts)} facts")
        except Exception as e:
            logger.debug("Could not load case state: %s", e)

        # Phase 1: Auto-ingest norms mentioned by number in the query
        is_legal = self._is_legal_mode()
        if is_legal:
            yield "[STATUS] Revisando normas mencionadas...\n"
            ingested = await self._auto_ingest_missing_norms(message)
            if ingested:
                for n in ingested:
                    yield f"[INGEST] {n}\n"
                self.invalidate_doc_cache()

        # Phase 2: Load history
        yield "[STATUS] Cargando contexto de conversacion...\n"
        history: list = []
        try:
            history = await self.storage.get_session_messages(session_id)
        except Exception as e:
            logger.debug("Could not load history: %s", e)

        retrieval_query = self._build_retrieval_query(message, history)

        # Phase 3: Retrieval
        yield "[STATUS] Buscando en documentos legales...\n"
        retrieval_result = await self.retrieval.retrieve(
            query=retrieval_query, session_id=session_id,
        )
        retrieval_result.query.original_query = message

        # Phase 4: Legal — ALWAYS try to identify and download needed norms
        llm_ingested = []
        if is_legal:
            has_good = retrieval_result.results and any(
                r.best_score > 0.5 for r in retrieval_result.results[:3]
            )
            # ALWAYS investigate — even with some results, there might be
            # more specific norms needed for a complete answer
            yield "[STATUS] Investigando normativa aplicable...\n"
            llm_ingested = await self._identify_needed_norms_via_llm(message, retrieval_result)
            if llm_ingested:
                for n in llm_ingested:
                    yield f"[INGEST] {n}\n"
                self.invalidate_doc_cache()
                yield "[STATUS] Buscando en documentos recién indexados...\n"
                retrieval_result = await self.retrieval.retrieve(
                    query=retrieval_query, session_id=session_id,
                )
                retrieval_result.query.original_query = message

        # Phase 5: Legal enrichment — live sources + vigencia
        live_results = None
        vigencia_results = None
        if is_legal:
            yield "[STATUS] Consultando fuentes legales oficiales...\n"
            live_results, vigencia_results = await self._enrich_with_legal_sources(
                retrieval_query, retrieval_result
            )

            # Auto-ingest from live results if needed
            if live_results:
                did_ingest = await self._auto_ingest_live_results(live_results)
                if did_ingest:
                    self.invalidate_doc_cache()
                    yield "[STATUS] Re-buscando con nuevas normas descargadas...\n"
                    retrieval_result = await self.retrieval.retrieve(
                        query=retrieval_query, session_id=session_id,
                    )
                    retrieval_result.query.original_query = message
                    _, vigencia_results = await self._enrich_with_legal_sources(
                        retrieval_query, retrieval_result
                    )

            if vigencia_results:
                yield "[STATUS] Verificando vigencia de normas...\n"

            # Phase 5.5: Search jurisprudence
            yield "[STATUS] Buscando jurisprudencia relevante...\n"
            try:
                from api.legal import _source_router
                if _source_router:
                    juris_query = retrieval_query
                    if case_state.areas_involved:
                        juris_query = f"{' '.join(case_state.areas_involved)} {message}"
                    juris_results = await _source_router.search_sentencias(
                        query=juris_query, limit=5,
                    )
                    if juris_results:
                        yield f"[STATUS] {len(juris_results)} sentencias encontradas\n"
                        # Add to context
                        juris_block = "\n\nJURISPRUDENCIA RELEVANTE ENCONTRADA:\n"
                        for jr in juris_results[:3]:
                            juris_block += f"- {getattr(jr, 'titulo', '')} ({getattr(jr, 'source', '')})\n"
                            preview = getattr(jr, 'preview', '')
                            if preview:
                                juris_block += f"  {preview[:150]}\n"
                        # Will be added to context in Phase 6
            except Exception as e:
                logger.debug(f"Jurisprudence search failed: {e}")
                juris_results = []

        # Phase 6: Build context & messages
        sources = get_sources(retrieval_result)
        confidence = get_confidence(retrieval_result)
        intent = retrieval_result.query.intent.value if retrieval_result.query.intent else "knowledge"

        if is_legal and (live_results or vigencia_results):
            context = build_legal_context(retrieval_result, live_results, vigencia_results)
            if live_results:
                for lr in live_results:
                    name = f"{getattr(lr, 'titulo', '')} ({getattr(lr, 'source', '')})"
                    if name.strip(" ()"):
                        sources.append(name)
        else:
            context = build_context(retrieval_result)

        loaded_doc_titles = await self._get_loaded_doc_titles()

        # Inject CaseState into context (replaces need for 100 history messages)
        case_context = case_state.to_context_block()
        if case_context:
            context = case_context + "\n\n" + context

        system_prompt = build_system_prompt(
            agent_name=self.config.agent.name,
            agent_role=self.config.agent.role,
            context=context, intent=intent, sources=sources,
            confidence=confidence,
            was_refined=retrieval_result.was_refined,
            refined_query=retrieval_result.refined_query,
            custom_template=self.config.agent.system_prompt_template,
            loaded_documents=loaded_doc_titles,
        )

        llm_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        # With CaseState, we only need last 5 turns for immediate context
        if history:
            for h in history[-(5 * 2):]:
                llm_messages.append({"role": h["role"], "content": h["content"]})
        llm_messages.append({"role": "user", "content": message})

        # Phase 7: Stream LLM response
        yield "[STATUS] Generando respuesta fundamentada...\n"

        client = get_openai_client()
        full_response = ""
        first_token = True

        stream = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=llm_messages,
            temperature=self.config.agent.temperature,
            max_tokens=self.config.agent.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.usage:
                tracker.record_chat(
                    model=self.config.agent.primary_model,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                    purpose="main_response_stream",
                    session_id=session_id,
                )
                continue
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                if first_token:
                    yield f"[CONTENT]{text}"
                    first_token = False
                else:
                    yield text
                full_response += text

        # Phase 8: Post-response metadata
        full_response = sanitize_llm_response(full_response, allowed_documents=loaded_doc_titles)

        # Vigencia as structured data
        if vigencia_results:
            for v in vigencia_results:
                if v.encontrada:
                    import json
                    vdata = {"tipo": v.tipo, "numero": v.numero, "anio": v.anio,
                             "estado": v.estado, "titulo": v.titulo}
                    if v.derogaciones:
                        d = v.derogaciones[0]
                        vdata["derogada_por"] = f"{d.get('norma_tipo','')} {d.get('norma_numero','')} de {d.get('norma_anio','')}"
                    yield f"\n[VIGENCIA] {json.dumps(vdata, ensure_ascii=False)}\n"

        # Sources with URLs for sidebar
        import json
        if sources:
            yield f"\n[SOURCES] {json.dumps(sources, ensure_ascii=False)}\n"

        # Emit source references with real URLs for the activity panel
        source_refs = []
        # From live search results
        if live_results:
            for lr in live_results:
                url = getattr(lr, 'url', None)
                titulo = getattr(lr, 'titulo', '') or ''
                source_name = getattr(lr, 'source', '') or ''
                preview = getattr(lr, 'preview', '') or ''
                if url or titulo:
                    ref = {"url": url or '', "title": titulo, "source": source_name, "preview": preview[:120]}
                    source_refs.append(ref)
        # From ingested norms (they have fuente_url in the graph)
        try:
            from api.legal import _derogation_graph
            if _derogation_graph:
                all_normas = await _derogation_graph.list_normas(limit=30)
                for n in all_normas:
                    if n.get('fuente_url'):
                        nombre = f"{n.get('tipo','')} {n.get('numero','')} de {n.get('anio','')}"
                        ref = {"url": n['fuente_url'], "title": nombre,
                               "source": "Fuente oficial", "preview": n.get('titulo', '')[:120]}
                        # Avoid duplicates
                        if not any(r['url'] == ref['url'] for r in source_refs):
                            source_refs.append(ref)
        except Exception:
            pass
        # From loaded documents
        for s in sources:
            if 'senado' in s.lower() or 'codigo' in s.lower() or 'ley_' in s.lower():
                ref = {"url": "http://www.secretariasenado.gov.co/senado/basedoc/",
                       "title": s, "source": "secretariasenado.gov.co", "preview": "Texto oficial del Senado de la Republica"}
                if not any(r['title'] == ref['title'] for r in source_refs):
                    source_refs.append(ref)
            elif 'funcionpublica' in s.lower():
                ref = {"url": "https://www.funcionpublica.gov.co/eva/gestornormativo/",
                       "title": s, "source": "funcionpublica.gov.co", "preview": "Gestor Normativo de Funcion Publica"}
                if not any(r['title'] == ref['title'] for r in source_refs):
                    source_refs.append(ref)

        if source_refs:
            yield f"\n[SOURCEREFS] {json.dumps(source_refs, ensure_ascii=False)}\n"

        # Update CaseState with this exchange
        try:
            await case_state.update_from_exchange(message, full_response, self.config.agent.utility_model)
            await self.storage.save_case_state(session_id, case_state.to_dict(), case_state.turn_count)
            cs_data = case_state.to_dict()
            yield f"\n[CASESTATE] {json.dumps(cs_data, ensure_ascii=False)}\n"
        except Exception as e:
            logger.warning(f"CaseState save failed: {e}")

        # Duration
        duration = int(time.time() - start_time)
        yield f"\n[DURATION] {duration}s\n"

        # ALWAYS persist chat history (lightweight) for in-session context
        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent=intent,
            sources_used=sources,
        )

        # Optional: heavyweight RAG memory save (background, non-blocking)
        self._schedule_memory_save(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent=intent,
            sources_used=sources,
        )

    async def _build_chitchat_messages(
        self,
        message: str,
        session_id: str,
        history_limit: int = 6,
    ) -> List[Dict[str, str]]:
        """Build a minimal message list for chitchat turns (no retrieval).

        Used by chat_chitchat / chat_chitchat_stream to short-circuit the RAG
        pipeline for trivial turns like greetings, thanks, and farewells.
        Skips: embedding, hybrid_search, cross-encoder rerank, sources footer.
        Result: time-to-first-token drops from ~3s to ~0.5s.
        """
        history: list = []
        try:
            history = await self.storage.get_session_messages(session_id)
        except Exception as e:
            logger.debug("Could not load history for session %s: %s", session_id, e)

        system_prompt = (
            f"Eres {self.config.agent.name}, {self.config.agent.role}. "
            "El usuario te ha enviado un saludo, agradecimiento o mensaje conversacional "
            "breve que no requiere consultar documentos. Responde de forma cordial, "
            "concisa (1-2 frases) y en el mismo idioma del usuario. No inventes citas "
            "legales. Si el usuario quiere una consulta real, invitalo a formularla."
        )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            tail = history[-(history_limit * 2):]
            for h in tail:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": message})
        return messages

    async def chat_chitchat(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> Dict:
        """Lightweight chat path for greetings / trivial turns. No RAG."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())
        messages = await self._build_chitchat_messages(message, session_id)

        client = get_openai_client()
        response = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
        )

        if response.usage:
            tracker.record_chat(
                model=self.config.agent.primary_model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                purpose="chitchat",
                session_id=session_id,
            )

        assistant_message = (response.choices[0].message.content or "").strip()

        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=assistant_message,
            intent="chitchat",
            sources_used=[],
        )

        return {
            "response": assistant_message,
            "intent": "chitchat",
            "sources": [],
            "session_id": session_id,
        }

    async def chat_chitchat_stream(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming variant of chat_chitchat. No RAG pipeline."""
        from utils.usage_tracker import tracker

        session_id = session_id or str(uuid.uuid4())
        messages = await self._build_chitchat_messages(message, session_id)

        client = get_openai_client()
        full_response = ""
        stream = await client.chat.completions.create(
            model=self.config.agent.primary_model,
            messages=messages,
            temperature=0.3,
            max_tokens=200,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.usage:
                tracker.record_chat(
                    model=self.config.agent.primary_model,
                    input_tokens=chunk.usage.prompt_tokens,
                    output_tokens=chunk.usage.completion_tokens,
                    purpose="chitchat_stream",
                    session_id=session_id,
                )
                continue

            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_response += text
                yield text

        await self._save_chat_history(
            session_id=session_id,
            user_message=message,
            assistant_message=full_response,
            intent="chitchat",
            sources_used=[],
        )

    async def _save_chat_history(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str,
        sources_used: list,
    ) -> None:
        """Lightweight chat history save (no embeddings, no LLM calls).

        Always runs so the next user turn in the same session can see the
        previous exchange via get_session_messages(). Independent from the
        heavier RAG memory (save_to_rag) which embeds and re-ranks past
        conversations as additional retrieval context.
        """
        try:
            await self.storage.save_chat_message(
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                intent=intent,
                sources_used=sources_used,
            )
        except Exception as e:
            logger.warning("Chat history save failed (non-fatal): %s", e)

    def _schedule_memory_save(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str,
        sources_used: list,
    ) -> None:
        """Schedule a non-blocking RAG conversation memory save.

        This is for SEMANTIC search of past conversations (heavyweight: embedding
        + relevance grading + summary). Skipped entirely if
        conversation_memory.save_to_rag is disabled.

        Note: chat history persistence (for in-session context) is handled by
        _save_chat_history and runs unconditionally.
        """
        if not self.config.retrieval.conversation_memory.save_to_rag:
            return

        async def _do_save():
            try:
                await self.memory.process_exchange(
                    session_id=session_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                    intent=intent,
                    sources_used=sources_used,
                )
            except Exception as e:
                logger.debug("Background conversation memory save failed: %s", e)

        try:
            asyncio.create_task(_do_save())
        except RuntimeError:
            # No running loop — skip silently
            pass

    async def _get_loaded_doc_titles(self) -> List[str]:
        """Return the allow-list of loaded document titles, cached for 5 min.

        The allow-list drives the anti-hallucination layer in the system prompt.
        Reading it from Postgres on every turn cost ~100-200ms per query; this
        cache brings it down to <1ms on the hot path. Cache is invalidated
        automatically on TTL expiry and manually via `invalidate_doc_cache()`
        after document ingestion or deletion.
        """
        now = time.monotonic()
        if (
            self._allow_list_cache is not None
            and (now - self._allow_list_cached_at) < self._allow_list_ttl_s
        ):
            return self._allow_list_cache

        try:
            all_docs_meta = await self.storage.list_documents()
            titles = [
                d["title"] for d in all_docs_meta
                if d.get("status") in (None, "completed")
                and "tmp" not in (d.get("title") or "").lower()
            ]
        except Exception as e:
            logger.debug("Could not load document allow-list: %s", e)
            titles = self._allow_list_cache or []

        self._allow_list_cache = titles
        self._allow_list_cached_at = now
        return titles

    def invalidate_doc_cache(self) -> None:
        """Force the next query to reload the document allow-list from DB.

        Call this after ingesting or deleting a document so that the prompt
        reflects the current corpus on the next user turn.
        """
        self._allow_list_cache = None
        self._allow_list_cached_at = 0.0

    async def _auto_ingest_missing_norms(self, message: str) -> list[str]:
        """Detect norm references in the query and auto-ingest any that aren't in the RAG.

        Returns list of norm names that were ingested (empty if none needed).
        """
        import re

        try:
            from api.legal import _source_router, _derogation_graph, _storage, _embedder
        except ImportError:
            return []

        if not _source_router or not _derogation_graph or not _storage:
            return []

        # Extract norm references from the user message
        patterns = [
            (r"(?:[Ll]ey)\s+(\d+)\s+(?:de\s+)?(\d{4})", "LEY"),
            (r"(?:[Dd]ecreto)\s+(\d+)\s+(?:de\s+)?(\d{4})", "DECRETO"),
            (r"(?:[Rr]esoluci[oó]n)\s+(\d+)\s+(?:de\s+)?(\d{4})", "RESOLUCION"),
        ]

        norm_refs = []
        seen = set()
        for pattern, tipo in patterns:
            for match in re.finditer(pattern, message):
                key = f"{tipo}:{match.group(1)}:{match.group(2)}"
                if key not in seen:
                    seen.add(key)
                    norm_refs.append({
                        "tipo": tipo,
                        "numero": int(match.group(1)),
                        "anio": int(match.group(2)),
                    })

        if not norm_refs:
            return []

        # Check which norms are already in the RAG (by document title)
        loaded_titles = await self._get_loaded_doc_titles()
        loaded_lower = {t.lower() for t in loaded_titles}

        ingested = []

        for ref in norm_refs:
            nombre = f"{ref['tipo']} {ref['numero']} de {ref['anio']}"
            nombre_variants = [
                nombre.lower(),
                f"{ref['tipo'].lower()} {ref['numero']} de {ref['anio']}",
                f"{ref['tipo'].lower()}_{ref['numero']}_{ref['anio']}",
                f"ley_{ref['numero']}_{ref['anio']}",
                f"resolucion_{ref['numero']}_{ref['anio']}",
                f"decreto_{ref['numero']}_{ref['anio']}",
            ]

            # Check if any variant is already loaded
            already_loaded = any(
                any(variant in title for variant in nombre_variants)
                for title in loaded_lower
            )

            if already_loaded:
                logger.info(f"Norm already in RAG: {nombre}")
                continue

            # Not loaded — fetch and ingest
            logger.info(f"Auto-ingesting missing norm: {nombre}")

            try:
                norm_data = await _source_router.fetch_norm(
                    ref["tipo"], ref["numero"], ref["anio"]
                )

                if not norm_data or not norm_data.get("texto_completo"):
                    logger.warning(f"Could not fetch norm: {nombre}")
                    continue

                # Ingest to graph
                from derogation.models import NormaCreate, TipoNorma, FuenteLegal
                norma_create = NormaCreate(
                    tipo=TipoNorma(ref["tipo"]),
                    numero=ref["numero"],
                    anio=ref["anio"],
                    titulo=norm_data.get("titulo", nombre),
                    fuente=FuenteLegal(norm_data.get("fuente", "manual")),
                    fuente_url=norm_data.get("fuente_url"),
                    fuente_id=norm_data.get("fuente_id"),
                    texto_completo=norm_data.get("texto_completo"),
                    sector=norm_data.get("sector"),
                    metadata=norm_data.get("metadata", {}),
                )

                if _embedder:
                    embed_text = f"{norm_data.get('titulo', '')} {norm_data.get('texto_completo', '')[:1000]}"
                    embeddings = await _embedder.generate_embeddings_batch([embed_text])
                    embedding = embeddings[0] if embeddings else None
                else:
                    embedding = None

                await _derogation_graph.insert_norma(norma_create, embedding=embedding)

                # Detect and register derogations
                from derogation.detector import detect_derogations
                from derogation.models import DerogacionCreate
                derogations = detect_derogations(norm_data.get("texto_completo", ""))
                for det in derogations:
                    if det.norma_afectada_numero and det.norma_afectada_anio:
                        affected = await _derogation_graph.get_norma(
                            det.norma_afectada_tipo or ref["tipo"],
                            det.norma_afectada_numero,
                            det.norma_afectada_anio,
                        )
                        if affected:
                            derog = DerogacionCreate(
                                norma_origen_id=str((await _derogation_graph.get_norma(ref["tipo"], ref["numero"], ref["anio"]))["id"]),
                                norma_destino_id=str(affected["id"]),
                                tipo=det.tipo_derogacion,
                                articulos_afectados=det.articulos_afectados,
                                fuente_texto=det.texto_fuente,
                                detectado_por="auto_regex",
                                confianza=det.confianza,
                            )
                            await _derogation_graph.insert_derogacion(derog)

                # Ingest to RAG (chunks)
                from ingestion.pipeline import IngestionPipeline
                from config.schema import load_config
                config = load_config()
                pipeline = IngestionPipeline(config, _storage)
                await pipeline.ingest_text(
                    text=norm_data.get("texto_completo", ""),
                    title=norm_data.get("titulo", nombre),
                    source=norm_data.get("fuente_url", "legal_source"),
                    doc_type="legal_norm",
                )

                ingested.append(nombre)
                logger.info(f"Auto-ingested: {nombre}")

            except Exception as e:
                logger.error(f"Auto-ingest failed for {nombre}: {e}")

        # Also check derogation chain: if a norm is derogated, auto-ingest the replacement
        for ref in norm_refs:
            try:
                vigencia = await self._check_derogation_and_ingest_replacement(ref, loaded_lower, ingested)
                if vigencia:
                    ingested.extend(vigencia)
            except Exception as e:
                logger.debug(f"Derogation chain check failed: {e}")

        return ingested

    async def _check_derogation_and_ingest_replacement(
        self, ref: dict, loaded_lower: set, already_ingested: list
    ) -> list[str]:
        """If a norm is derogated, auto-ingest the norm that replaced it."""
        from api.legal import _derogation_graph, _source_router, _storage, _embedder

        if not _derogation_graph:
            return []

        norma = await _derogation_graph.get_norma(ref["tipo"], ref["numero"], ref["anio"])
        if not norma or norma.get("estado") != "DEROGADA":
            return []

        # Find what derogated it
        derogations = await _derogation_graph.get_derogations_for(str(norma["id"]))
        ingested = []

        for d in derogations:
            replacement_nombre = f"{d.get('origen_tipo', '')} {d.get('origen_numero', '')} de {d.get('origen_anio', '')}"

            # Skip if already loaded or already ingested in this cycle
            if replacement_nombre in already_ingested:
                continue

            nombre_lower = replacement_nombre.lower()
            if any(nombre_lower in t for t in loaded_lower):
                continue

            # Fetch and ingest the replacement
            logger.info(f"Auto-ingesting replacement norm: {replacement_nombre}")
            try:
                norm_data = await _source_router.fetch_norm(
                    d.get("origen_tipo", ""), d.get("origen_numero", 0), d.get("origen_anio", 0)
                )
                if norm_data and norm_data.get("texto_completo"):
                    from ingestion.pipeline import IngestionPipeline
                    from config.schema import load_config
                    config = load_config()
                    pipeline = IngestionPipeline(config, _storage)
                    await pipeline.ingest_text(
                        text=norm_data.get("texto_completo", ""),
                        title=norm_data.get("titulo", replacement_nombre),
                        source=norm_data.get("fuente_url", "legal_source"),
                        doc_type="legal_norm",
                    )
                    ingested.append(replacement_nombre)
                    logger.info(f"Auto-ingested replacement: {replacement_nombre}")
            except Exception as e:
                logger.error(f"Auto-ingest replacement failed for {replacement_nombre}: {e}")

        return ingested

    async def _identify_needed_norms_via_llm(self, message: str, retrieval_result) -> list[str]:
        """Use LLM to identify which Colombian norms are needed to answer a query.
        ALWAYS runs — even with existing results, identifies additional norms.
        Returns list of norm names that were ingested."""
        import re

        try:
            # Build context about what's already loaded
            loaded = await self._get_loaded_doc_titles()
            loaded_str = ", ".join(loaded[:10]) if loaded else "ninguno"

            client = get_openai_client()
            response = await client.chat.completions.create(
                model=self.config.agent.utility_model,
                temperature=0,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": (
                        "Eres un experto en derecho colombiano. El usuario hizo una consulta legal. "
                        "Identifica TODAS las normas colombianas (leyes, decretos, resoluciones, "
                        "codigos) que se necesitan para responder completamente esta consulta. "
                        "Incluye normas de CUALQUIER area: civil, penal, laboral, comercial, "
                        "administrativo, ambiental, deportivo, propiedad horizontal, etc. "
                        f"Ya estan cargados: {loaded_str}. "
                        "NO repitas normas ya cargadas. "
                        "Responde SOLO con formato: TIPO NUMERO AÑO (una por linea). "
                        "Ejemplo: LEY 675 2001\nDECRETO 1072 2015\nLEY 599 2000\n"
                        "Si no se necesitan normas adicionales, responde: NONE"
                    )},
                    {"role": "user", "content": message},
                ],
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"LLM norm identification: {answer}")

            if "NONE" in answer.upper():
                return []

            # Parse response
            ingested = []
            pattern = r"(LEY|DECRETO|RESOLUCION|CODIGO)\s+(\d+)\s+(?:de\s+)?(\d{4})"
            for match in re.finditer(pattern, answer, re.IGNORECASE):
                tipo = match.group(1).upper()
                numero = int(match.group(2))
                anio = int(match.group(3))
                nombre = f"{tipo} {numero} de {anio}"

                # Check if already loaded
                loaded = await self._get_loaded_doc_titles()
                already = any(str(numero) in t and str(anio) in t for t in [x.lower() for x in loaded])
                if already:
                    continue

                # Auto-ingest
                try:
                    from api.legal import _source_router, _storage
                    if not _source_router or not _storage:
                        continue

                    norm_data = await _source_router.fetch_norm(tipo, numero, anio)
                    if norm_data and norm_data.get("texto_completo"):
                        from ingestion.pipeline import IngestionPipeline
                        from config.schema import load_config
                        config = load_config()
                        pipeline = IngestionPipeline(config, _storage)
                        await pipeline.ingest_text(
                            text=norm_data["texto_completo"],
                            title=norm_data.get("titulo", nombre),
                            source=norm_data.get("fuente_url", "legal_source"),
                            doc_type="legal_norm",
                        )
                        ingested.append(nombre)
                        logger.info(f"LLM-identified norm ingested: {nombre}")
                except Exception as e:
                    logger.warning(f"Failed to ingest LLM-identified norm {nombre}: {e}")

            return ingested
        except Exception as e:
            logger.warning(f"LLM norm identification failed: {e}")
            return []

    async def _auto_ingest_live_results(self, live_results: list) -> bool:
        """Auto-ingest norms found in live sources that aren't already in the RAG.
        Returns True if anything was ingested."""
        try:
            from api.legal import _source_router, _derogation_graph, _storage, _embedder
        except ImportError:
            return False

        if not _source_router or not _storage:
            return False

        loaded_titles = await self._get_loaded_doc_titles()
        loaded_lower = {t.lower() for t in loaded_titles}
        ingested_any = False

        for lr in live_results:
            tipo = getattr(lr, 'tipo', None)
            numero = getattr(lr, 'numero', None)
            anio = getattr(lr, 'anio', None)

            if not tipo or not numero or not anio:
                continue

            nombre = f"{tipo} {numero} de {anio}"
            # Check if already loaded
            already = any(
                str(numero) in t and str(anio) in t
                for t in loaded_lower
            )
            if already:
                continue

            logger.info(f"Auto-ingesting from live results: {nombre}")
            try:
                norm_data = await _source_router.fetch_norm(tipo, int(numero), int(anio))
                if not norm_data or not norm_data.get("texto_completo"):
                    continue

                # Ingest to graph
                if _derogation_graph:
                    from derogation.models import NormaCreate, TipoNorma, FuenteLegal
                    from derogation.detector import detect_derogations
                    from derogation.models import DerogacionCreate

                    try:
                        norma_tipo = TipoNorma(tipo.upper())
                    except ValueError:
                        norma_tipo = TipoNorma.LEY

                    norma_create = NormaCreate(
                        tipo=norma_tipo, numero=int(numero), anio=int(anio),
                        titulo=norm_data.get("titulo", nombre),
                        fuente=FuenteLegal(norm_data.get("fuente", "manual")) if norm_data.get("fuente") in [e.value for e in FuenteLegal] else FuenteLegal.MANUAL,
                        fuente_url=norm_data.get("fuente_url"),
                        texto_completo=norm_data.get("texto_completo"),
                        metadata=norm_data.get("metadata", {}),
                    )

                    embedding = None
                    if _embedder:
                        embed_text = f"{norm_data.get('titulo', '')} {norm_data.get('texto_completo', '')[:1000]}"
                        embeddings = await _embedder.generate_embeddings_batch([embed_text])
                        embedding = embeddings[0] if embeddings else None

                    await _derogation_graph.insert_norma(norma_create, embedding=embedding)

                    # Detect derogations
                    derogations = detect_derogations(norm_data.get("texto_completo", ""))
                    for det in derogations:
                        if det.norma_afectada_numero and det.norma_afectada_anio:
                            affected = await _derogation_graph.get_norma(
                                det.norma_afectada_tipo or tipo,
                                det.norma_afectada_numero, det.norma_afectada_anio,
                            )
                            if affected:
                                origin = await _derogation_graph.get_norma(tipo, int(numero), int(anio))
                                if origin:
                                    derog = DerogacionCreate(
                                        norma_origen_id=str(origin["id"]),
                                        norma_destino_id=str(affected["id"]),
                                        tipo=det.tipo_derogacion,
                                        articulos_afectados=det.articulos_afectados,
                                        fuente_texto=det.texto_fuente,
                                        detectado_por="auto_regex",
                                        confianza=det.confianza,
                                    )
                                    await _derogation_graph.insert_derogacion(derog)

                # Ingest to RAG
                from ingestion.pipeline import IngestionPipeline
                from config.schema import load_config
                config = load_config()
                pipeline = IngestionPipeline(config, _storage)
                await pipeline.ingest_text(
                    text=norm_data.get("texto_completo", ""),
                    title=norm_data.get("titulo", nombre),
                    source=norm_data.get("fuente_url", "legal_source"),
                    doc_type="legal_norm",
                )
                ingested_any = True
                logger.info(f"Auto-ingested from live: {nombre}")

            except Exception as e:
                logger.error(f"Auto-ingest live failed for {nombre}: {e}")

        return ingested_any

    def _is_legal_mode(self) -> bool:
        """Check if the agent is configured for legal mode."""
        role = (self.config.agent.role or "").lower()
        return any(kw in role for kw in ("legal", "abogado", "jurídic", "juridic", "derecho", "lawyer"))

    async def _enrich_with_legal_sources(self, query: str, retrieval_result) -> tuple:
        """Search live legal sources and verify vigencia in parallel.

        Returns:
            (live_results, vigencia_results) — both can be None if not available
        """
        import re

        live_results = None
        vigencia_results = None

        try:
            from api.legal import _source_router, _vigencia_checker
        except ImportError:
            logger.debug("Legal API not available for enrichment")
            return None, None

        # Task 1: Search live sources
        if _source_router:
            try:
                result = await _source_router.search(query, limit=5)
                live_results = result.get("results", [])
                logger.info("Legal live search: %d results", len(live_results))
            except Exception as e:
                logger.warning("Live source search failed: %s", e)

        # Task 2: Extract ALL norm references from query + RAG results + document titles
        if _vigencia_checker:
            try:
                normas = []
                patterns = [
                    (r"(?:[Ll]ey)\s+(\d+)\s+(?:de\s+)?(\d{4})", "LEY"),
                    (r"(?:[Dd]ecreto)\s+(\d+)\s+(?:de\s+)?(\d{4})", "DECRETO"),
                    (r"(?:[Rr]esoluci[oó]n)\s+(\d+)\s+(?:de\s+)?(\d{4})", "RESOLUCION"),
                ]

                # Extract from user query
                for pattern, tipo in patterns:
                    for match in re.finditer(pattern, query):
                        normas.append({"tipo": tipo, "numero": match.group(1), "anio": match.group(2)})

                # Extract from RAG retrieval results (chunks content)
                for r in (retrieval_result.results or [])[:10]:
                    content = r.content or ""
                    for pattern, tipo in patterns:
                        for match in re.finditer(pattern, content):
                            normas.append({"tipo": tipo, "numero": match.group(1), "anio": match.group(2)})

                # Extract from document titles in sources
                for r in (retrieval_result.results or [])[:10]:
                    title = r.document_title or ""
                    for pattern, tipo in patterns:
                        for match in re.finditer(pattern, title):
                            normas.append({"tipo": tipo, "numero": match.group(1), "anio": match.group(2)})

                # Deduplicate
                seen = set()
                unique_normas = []
                for n in normas:
                    key = f"{n['tipo']}:{n['numero']}:{n['anio']}"
                    if key not in seen:
                        seen.add(key)
                        unique_normas.append(n)

                logger.info("Legal vigencia check: %d unique norms extracted", len(unique_normas))

                if unique_normas:
                    vigencia_results = await _vigencia_checker.verify_results(unique_normas[:15])
                    logger.info("Legal vigencia results: %d checked", len(vigencia_results))
            except Exception as e:
                logger.warning("Vigencia check failed: %s", e)

        return live_results, vigencia_results

    @staticmethod
    def new_session_id() -> str:
        """Generate a new session ID."""
        return str(uuid.uuid4())
