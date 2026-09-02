from types import SimpleNamespace

from src.offline_assistant.documents import Chunk
from src.offline_assistant.service import LocalRAGService
from src.offline_assistant.storage import save_index


class FakeEmbeddingClient:
    def __init__(self, vector):
        self.vector = vector

    def generate_embedding(self, _question):
        return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=self.vector)])


class FakeChatClient:
    def __init__(self):
        self.settings = SimpleNamespace(max_tokens=None, temperature=None)
        self.messages = None

    def complete_chat(self, messages):
        self.messages = messages
        message = SimpleNamespace(content="Kütüphane saat 18.00'de kapanır. [K1]")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeModel:
    def __init__(self, client):
        self.client = client
        self.is_cached = True
        self.load_count = 0
        self.unload_count = 0

    def load(self):
        self.load_count += 1

    def unload(self):
        self.unload_count += 1

    def get_embedding_client(self):
        return self.client

    def get_chat_client(self):
        return self.client


class FakeCatalog:
    def __init__(self, embedding_model, chat_model):
        self.embedding_model = embedding_model
        self.chat_model = chat_model

    def get_model_variant(self, _model_id):
        return self.embedding_model

    def get_model(self, _alias):
        return self.chat_model


def make_service(tmp_path, query_vector):
    database = tmp_path / "assistant.db"
    chunks = [
        Chunk("kutuphane.txt", 1, "Kütüphane saat 18.00'de kapanır."),
        Chunk("yemekhane.txt", 1, "Öğle yemeği saat 12.00'de başlar."),
    ]
    save_index(database, tmp_path, "embedding:1", 600, chunks, [[1, 0], [0, 1]])
    embedding_model = FakeModel(FakeEmbeddingClient(query_vector))
    chat_client = FakeChatClient()
    chat_model = FakeModel(chat_client)
    manager = SimpleNamespace(catalog=FakeCatalog(embedding_model, chat_model))
    return LocalRAGService(manager), database, embedding_model, chat_model, chat_client


def test_service_runs_retrieval_then_grounded_chat(tmp_path):
    service, database, embedding_model, chat_model, chat_client = make_service(tmp_path, [1, 0])
    result = service.answer("Kütüphane kaçta kapanır?", database)
    assert result.answer.endswith("[K1]")
    assert [source.source for source in result.sources] == ["kutuphane.txt"]
    assert result.source_labels[0].startswith("[K1] kutuphane.txt")
    assert result.warnings == []
    assert result.used_chat_model
    assert embedding_model.load_count == embedding_model.unload_count == 1
    assert chat_model.load_count == chat_model.unload_count == 1
    assert "Kütüphane saat 18.00'de kapanır." in chat_client.messages[0]["content"]


def test_low_score_skips_chat_model(tmp_path):
    service, database, embedding_model, chat_model, chat_client = make_service(tmp_path, [0.7, 0.7])
    result = service.answer("İlgisiz soru", database, min_score=0.9)
    assert result.answer == "Bu bilgi mevcut belgelerde bulunamadı."
    assert not result.used_chat_model
    assert result.sources == []
    assert embedding_model.load_count == embedding_model.unload_count == 1
    assert chat_model.load_count == chat_model.unload_count == 0
    assert chat_client.messages is None
