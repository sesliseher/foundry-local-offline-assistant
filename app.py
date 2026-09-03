"""Streamlit kullanıcı arayüzü."""

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from offline_assistant.service import AnswerResult, LocalRAGService


st.set_page_config(page_title="Yerel Belge Asistanı", page_icon="📚", layout="centered")


@st.cache_resource(show_spinner=False)
def get_service() -> LocalRAGService:
    return LocalRAGService.create_default(PROJECT_ROOT)


def show_response(result: AnswerResult) -> None:
    st.markdown(result.answer)
    if result.warnings:
        for warning in result.warnings:
            st.warning(warning)
    if result.citation_added_by_app:
        st.caption("Kaynak etiketi doğrulanan retrieval sonucundan uygulama tarafından eklendi.")
    timing = f"Arama: {result.retrieval_seconds:.2f} sn"
    if result.generation_seconds is not None:
        timing += f" · Cevap: {result.generation_seconds:.2f} sn"
    st.caption(f"En iyi skor: {result.top_score:.4f} · Kaynak farkı: {result.source_margin:.4f} · {timing}")
    if not result.used_chat_model:
        st.info("Benzerlik eşiği aşılmadığı için sohbet modeli çağrılmadı.")
        return
    with st.expander(f"Kullanılan kaynaklar ({len(result.sources)})", expanded=True):
        for label, source in zip(result.source_labels, result.sources):
            st.markdown(f"**{label}**")
            st.write(source.text)


st.title("📚 Yerel Belge Asistanı")
st.write("Sorularını bilgisayarındaki SQLite indeksine ve yerel modellere dayanarak yanıtlar.")
st.caption("Örnek belgeler kurgusaldır. Model cevaplarını önemli kararlar için doğrula.")

with st.sidebar:
    st.header("Ayarlar")
    database_text = st.text_input(
        "SQLite indeksi", value=str(PROJECT_ROOT / "data" / "database" / "assistant.db")
    )
    top_k = st.slider("Aranacak parça sayısı", 1, 10, 3)
    min_score = st.slider("Minimum benzerlik", -1.0, 1.0, 0.35, 0.01)
    min_source_margin = st.slider("Minimum kaynak farkı", 0.0, 1.0, 0.05, 0.01)
    max_score_drop = st.slider("En iyi skordan izin verilen fark", 0.0, 1.0, 0.15, 0.01)
    max_tokens = st.slider("En fazla cevap tokenı", 32, 512, 256, 16)
    chat_model = st.text_input("Sohbet modeli", value="qwen2.5-1.5b")
    if st.button("Sohbet geçmişini temizle", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.caption("Modeller otomatik indirilmez. İndeks veya model eksikse arayüz hata gösterir.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for item in st.session_state.messages:
    with st.chat_message("user"):
        st.markdown(item["question"])
    with st.chat_message("assistant"):
        show_response(item["result"])

question = st.chat_input("Belgeler hakkında bir soru sor…")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Yerel modeller çalışıyor…"):
                service = get_service()
                result = service.answer(
                    question=question,
                    database=Path(database_text),
                    top_k=top_k,
                    min_score=min_score,
                    min_source_margin=min_source_margin,
                    max_score_drop=max_score_drop,
                    chat_model_alias=chat_model.strip(),
                    max_tokens=max_tokens,
                )
            show_response(result)
            st.session_state.messages.append({"question": question, "result": result})
        except Exception as exc:
            st.error(f"Soru yanıtlanamadı: {exc}")
            st.caption("Önce belge indeksini ve model önbelleğini kontrol et.")
