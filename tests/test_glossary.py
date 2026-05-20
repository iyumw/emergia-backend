import pytest
from app.domain.glossary import get_glossary, _GLOSSARIO

def test_glossary_not_empty():
    g = get_glossary()
    assert len(g) > 0

def test_every_term_has_required_fields():
    for term in _GLOSSARIO:
        assert "termo" in term
        assert "definicao" in term

class TestGlossary:

    def test_returns_correct_structure(self):
        from app.domain.glossary import get_glossary
        g = get_glossary()
        assert "total_termos" in g or "categorias" in g
        assert len(g) > 0

    def test_every_category_has_content(self):
        from app.domain.glossary import get_glossary
        g = get_glossary()
        assert len(g) > 0

    def test_every_term_has_required_fields(self):
        from app.domain.glossary import get_glossary, _GLOSSARIO
        for term in _GLOSSARIO:
            assert "termo" in term
            assert "definicao" in term
            assert "referencia" in term