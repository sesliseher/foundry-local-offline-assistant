"""Model indirmeden matematik ve yanıt eşleştirmesi kontrolleri."""

from types import SimpleNamespace

import pytest

from scripts.embedding_demo import cosine_similarity, ordered_vectors


def test_cosine_geometry():
    assert cosine_similarity([1, 0], [9, 0]) == pytest.approx(1)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0)
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1)


@pytest.mark.parametrize("left,right", [
    ([], []), ([1], [1, 2]), ([0, 0], [1, 0]),
    ([float("nan")], [1]), ([1], [float("inf")]),
])
def test_invalid_vectors_are_rejected(left, right):
    with pytest.raises(ValueError):
        cosine_similarity(left, right)


def test_shuffled_response_preserves_document_mapping():
    response = SimpleNamespace(data=[
        SimpleNamespace(index=1, embedding=[0, 1]),
        SimpleNamespace(index=0, embedding=[1, 0]),
    ])
    assert ordered_vectors(response, 2) == [[1, 0], [0, 1]]


def test_duplicate_response_indices_are_rejected():
    response = SimpleNamespace(data=[
        SimpleNamespace(index=0, embedding=[1]),
        SimpleNamespace(index=0, embedding=[2]),
    ])
    with pytest.raises(RuntimeError):
        ordered_vectors(response, 2)
