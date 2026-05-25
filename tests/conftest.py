import pytest
from app.application.emergy_calculator import EmergyCalculator

@pytest.fixture
def calculator():
    return EmergyCalculator()