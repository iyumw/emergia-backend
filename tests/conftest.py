import pytest
from app.application.emergy_calculator import EmergyCalculator
from app.domain.entities import Edge, GraphData, Node

@pytest.fixture
def calculator():
    return EmergyCalculator()