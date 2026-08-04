import pytest
from tests.secret_sources.conformance import SecretSourceConformance

from infisical_source import InfisicalSource


class TestInfisicalSourceConformance(SecretSourceConformance):
    @pytest.fixture
    def source(self):
        return InfisicalSource()
