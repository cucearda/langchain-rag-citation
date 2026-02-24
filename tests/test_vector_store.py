# tests/test_vector_store.py
from unittest.mock import patch, MagicMock


def test_get_vector_store_passes_namespace():
    with patch("vector_store.Pinecone") as mock_pc_cls, \
         patch("vector_store.VoyageAIEmbeddings"), \
         patch("vector_store.PineconeVectorStore") as mock_vs_cls:
        mock_pc = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pc_cls.return_value = mock_pc

        from vector_store import get_vector_store
        get_vector_store(namespace="my-namespace")

        call_kwargs = mock_vs_cls.call_args.kwargs
        assert call_kwargs["namespace"] == "my-namespace"


def test_get_vector_store_default_namespace_is_empty():
    with patch("vector_store.Pinecone") as mock_pc_cls, \
         patch("vector_store.VoyageAIEmbeddings"), \
         patch("vector_store.PineconeVectorStore") as mock_vs_cls:
        mock_pc = MagicMock()
        mock_pc.has_index.return_value = True
        mock_pc_cls.return_value = mock_pc

        from vector_store import get_vector_store
        get_vector_store()

        call_kwargs = mock_vs_cls.call_args.kwargs
        assert call_kwargs.get("namespace", "") == ""
