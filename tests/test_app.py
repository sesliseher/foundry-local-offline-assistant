from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_initial_screen_renders_without_loading_models():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
    app.run(timeout=15)
    assert not app.exception
    assert app.title[0].value == "📚 Yerel Belge Asistanı"
    assert app.chat_input[0].placeholder == "Belgeler hakkında bir soru sor…"
    assert app.sidebar.slider[0].value == 600
    assert app.sidebar.slider[1].value == 3
    assert app.sidebar.slider[2].value == 0.35
    assert app.sidebar.slider[3].value == 0.02
    assert app.sidebar.slider[4].value == 0.15
    assert any(button.label == "İndeksi oluştur / yenile" for button in app.sidebar.button)
    assert any("SQLite indeksi" in caption.value for caption in app.sidebar.caption)
