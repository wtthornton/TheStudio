"""Tests for production context packs (Story 6.2)."""

from src.context.service_context_pack import get_registry


class TestProductionPacks:
    """Tests for the two production context packs."""

    def setup_method(self):
        get_registry().clear()
        from src.context.packs import register_production_packs
        register_production_packs()

    def teardown_method(self):
        get_registry().clear()

    def test_fastapi_pack_registered(self):
        from src.context.packs import FASTAPI_SERVICE_PACK
        assert FASTAPI_SERVICE_PACK in get_registry().all_packs

    def test_data_pipeline_pack_registered(self):
        from src.context.packs import DATA_PIPELINE_PACK
        assert DATA_PIPELINE_PACK in get_registry().all_packs

    def test_fastapi_pack_has_content(self):
        from src.context.packs import FASTAPI_SERVICE_PACK
        assert len(FASTAPI_SERVICE_PACK.conventions) > 0
        assert len(FASTAPI_SERVICE_PACK.api_patterns) > 0
        assert len(FASTAPI_SERVICE_PACK.constraints) > 0
        assert len(FASTAPI_SERVICE_PACK.testing_notes) > 0

    def test_data_pipeline_pack_has_content(self):
        from src.context.packs import DATA_PIPELINE_PACK
        assert len(DATA_PIPELINE_PACK.conventions) > 0
        assert len(DATA_PIPELINE_PACK.api_patterns) > 0
        assert len(DATA_PIPELINE_PACK.constraints) > 0
        assert len(DATA_PIPELINE_PACK.testing_notes) > 0

    def test_fastapi_pack_matches_api_repos(self):
        from src.context.packs import FASTAPI_SERVICE_PACK
        assert FASTAPI_SERVICE_PACK.matches_repo("api-gateway")
        assert FASTAPI_SERVICE_PACK.matches_repo("svc-auth")
        assert FASTAPI_SERVICE_PACK.matches_repo("service-billing")

    def test_data_pipeline_pack_matches_data_repos(self):
        from src.context.packs import DATA_PIPELINE_PACK
        assert DATA_PIPELINE_PACK.matches_repo("pipeline-etl")
        assert DATA_PIPELINE_PACK.matches_repo("etl-orders")
        assert DATA_PIPELINE_PACK.matches_repo("data-warehouse")
        assert DATA_PIPELINE_PACK.matches_repo("ingest-events")

    def test_packs_do_not_cross_match(self):
        from src.context.packs import DATA_PIPELINE_PACK, FASTAPI_SERVICE_PACK
        assert not FASTAPI_SERVICE_PACK.matches_repo("pipeline-etl")
        assert not DATA_PIPELINE_PACK.matches_repo("api-gateway")

    def test_get_packs_returns_fastapi_for_svc_repo(self):
        from src.context.service_context_pack import get_context_packs
        packs = get_context_packs("svc-users")
        names = [p.name for p in packs]
        assert "fastapi-service" in names
