"""
Processor tests.
"""

import pytest

import fitz

from app.processors.pdf_extractor import PDFExtractor
from app.processors.embedder import TextEmbedder


class DummyModel:
    def get_sentence_embedding_dimension(self):
        return 384

    def encode(self, texts, normalize_embeddings=True):
        if isinstance(texts, str):
            return [0.1] * 384
        return [[0.1] * 384 for _ in texts]


class TestPDFExtractor:
    def test_extract_valid_pdf(self, tmp_path):
        pdf_path = tmp_path / "sample.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Hello PDF")
        doc.save(pdf_path)
        doc.close()

        extractor = PDFExtractor()
        text = extractor.extract_text(str(pdf_path))
        assert text is not None
        assert "Hello PDF" in text

    def test_extract_missing_file(self):
        extractor = PDFExtractor()
        result = extractor.extract_text("/nonexistent/path.pdf")
        assert result is None

    def test_text_cleaning(self):
        extractor = PDFExtractor()
        dirty_text = "Test\n\n\nPage 1\n\nContent"
        clean = extractor._clean_text(dirty_text)
        assert "Page 1" not in clean
        assert "\n\n\n" not in clean


class TestEmbedder:
    def test_embed_text(self, monkeypatch):
        embedder = TextEmbedder()
        monkeypatch.setattr(embedder, "_load_model", lambda: DummyModel())
        embedding = embedder.embed("Test text for embedding")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_empty_text(self):
        embedder = TextEmbedder()
        embedding = embedder.embed("")

        assert len(embedding) == 384
        assert all(x == 0.0 for x in embedding)

    def test_embed_batch(self, monkeypatch):
        embedder = TextEmbedder()
        monkeypatch.setattr(embedder, "_load_model", lambda: DummyModel())
        texts = ["Text one", "Text two", "Text three"]
        embeddings = embedder.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == 384 for e in embeddings)
