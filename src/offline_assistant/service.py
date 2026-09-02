"""Streamlit ve diğer istemciler için yeniden kullanılabilir yerel RAG servisi."""

from dataclasses import dataclass
from pathlib import Path
import threading
from time import perf_counter

from .rag import (
    FALLBACK_ANSWER, build_messages, citation_warnings, has_sufficient_context,
    select_context, source_lines,
)
from .retrieval import SearchResult, load_index, search_chunks


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    sources: list[SearchResult]
    source_labels: list[str]
    warnings: list[str]
    top_score: float
    retrieval_seconds: float
    generation_seconds: float | None
    used_chat_model: bool


class LocalRAGService:
    """Foundry yöneticisini paylaşır; model kullanımını kilitle seri hale getirir."""

    def __init__(self, manager):
        self.manager = manager
        self._lock = threading.Lock()

    @classmethod
    def create_default(cls, project_root: Path, model_cache_dir: Path | None = None):
        from foundry_local_sdk import Configuration, FoundryLocalManager

        app_data = project_root.resolve() / "data" / "foundry"
        cache = model_cache_dir.resolve() if model_cache_dir else app_data / "cache" / "models"
        FoundryLocalManager.initialize(Configuration(
            app_name="offline_assistant", app_data_dir=str(app_data), model_cache_dir=str(cache)
        ))
        return cls(FoundryLocalManager.instance)

    def answer(
        self,
        question: str,
        database: Path,
        top_k: int = 3,
        min_score: float = 0.35,
        max_score_drop: float = 0.15,
        chat_model_alias: str = "qwen2.5-0.5b",
        max_tokens: int = 256,
    ) -> AnswerResult:
        question = question.strip()
        if not question:
            raise ValueError("Soru boş olamaz.")
        if top_k < 1 or max_tokens < 1:
            raise ValueError("Sonuç ve token sınırları sıfırdan büyük olmalıdır.")

        # Foundry model yükleme/çıkarma aynı servis üzerinde eşzamanlı çalıştırılmaz.
        with self._lock:
            metadata, chunks = load_index(database)
            catalog = self.manager.catalog
            embedding_model = catalog.get_model_variant(metadata.model_id)
            if embedding_model is None or not embedding_model.is_cached:
                raise ValueError("İndeksin embedding modeli bu önbellekte bulunamadı.")

            embedding_loaded = False
            try:
                retrieval_start = perf_counter()
                embedding_model.load()
                embedding_loaded = True
                response = embedding_model.get_embedding_client().generate_embedding(question)
                if len(response.data) != 1 or response.data[0].index != 0:
                    raise RuntimeError("Model sorgu için beklenen tek embedding'i döndürmedi.")
                results = search_chunks(response.data[0].embedding, chunks, metadata.dimension, top_k)
                embedding_model.unload()
                embedding_loaded = False
                retrieval_seconds = perf_counter() - retrieval_start
            finally:
                if embedding_loaded:
                    embedding_model.unload()

            if not has_sufficient_context(results, min_score):
                return AnswerResult(
                    FALLBACK_ANSWER, [], [], [], results[0].score,
                    retrieval_seconds, None, False,
                )

            context = select_context(results, min_score, max_score_drop)
            chat_model = catalog.get_model(chat_model_alias)
            if chat_model is None:
                raise ValueError(f"Sohbet modeli katalogda bulunamadı: {chat_model_alias}")
            if not chat_model.is_cached:
                raise ValueError("Sohbet modeli önbellekte bulunamadı.")
            chat_loaded = False
            try:
                chat_model.load()
                chat_loaded = True
                client = chat_model.get_chat_client()
                client.settings.max_tokens = max_tokens
                client.settings.temperature = 0.1
                start = perf_counter()
                completion = client.complete_chat(build_messages(question, context))
                generation_seconds = perf_counter() - start
                if not completion.choices or not (completion.choices[0].message.content or "").strip():
                    raise RuntimeError("Sohbet modeli boş cevap döndürdü.")
                answer = completion.choices[0].message.content.strip()
                chat_model.unload()
                chat_loaded = False
            finally:
                if chat_loaded:
                    chat_model.unload()

            return AnswerResult(
                answer=answer,
                sources=context,
                source_labels=source_lines(context),
                warnings=citation_warnings(answer, len(context)),
                top_score=results[0].score,
                retrieval_seconds=retrieval_seconds,
                generation_seconds=generation_seconds,
                used_chat_model=True,
            )
