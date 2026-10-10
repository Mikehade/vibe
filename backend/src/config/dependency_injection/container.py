from dependency_injector import containers, providers

from src.config.base import get_settings
from src.infrastructure.db.session import Database


def _content_client(settings):
    if settings.FAKE_SERVICES:
        from src.infrastructure.fakes.content import FakeContentClient

        return FakeContentClient()
    from src.infrastructure.clients.tmdb import TMDBClient

    return TMDBClient(api_key=settings.TMDB_API_KEY, base_url=settings.TMDB_BASE_URL)


def _language_model(settings):
    if settings.FAKE_SERVICES:
        from src.infrastructure.fakes.llm import FakeLanguageModel

        return FakeLanguageModel()
    from src.infrastructure.language_models.bedrock import BedrockModel

    return BedrockModel(
        model_id=settings.BEDROCK_MODEL_ID,
        region=settings.AWS_REGION,
        max_tool_iterations=settings.MAX_AGENT_TURNS,
        fast_model_id=settings.BEDROCK_FAST_MODEL_ID,
    )


class Container(containers.DeclarativeContainer):
    """DI container — wires every repo, service, client, and engine."""

    wiring_config = containers.WiringConfiguration(
        modules=[
            "src.api.health.router",
            "src.api.session.router",
            "src.api.mood.router",
            "src.api.profile.router",
            "src.api.content.router",
            "src.api.feedback.router",
            "src.api.couch.router",
            "src.api.tv.router",
        ]
    )

    config = providers.Singleton(get_settings)

    database = providers.Singleton(Database, database_url=config.provided.DATABASE_URL, echo=False)
    session_factory = providers.Factory(lambda db: db.session_factory, database)

    # ── Repositories ────────────────────────────────────
    device_repository = providers.Singleton(
        "src.infrastructure.repository.user.DeviceRepository", session_factory=session_factory
    )
    taste_profile_repository = providers.Singleton(
        "src.infrastructure.repository.taste_profile.TasteProfileRepository", session_factory=session_factory
    )
    session_plan_repository = providers.Singleton(
        "src.infrastructure.repository.session_plan.SessionPlanRepository", session_factory=session_factory
    )
    feedback_repository = providers.Singleton(
        "src.infrastructure.repository.feedback.FeedbackRepository", session_factory=session_factory
    )

    # ── External ────────────────────────────────────────
    content_client = providers.Singleton(_content_client, config)
    language_model = providers.Singleton(_language_model, config)

    # ── Engine ──────────────────────────────────────────
    pool_builder = providers.Singleton("src.core.engine.candidate_pool.CandidatePoolBuilder", content=content_client)
    session_architect = providers.Singleton(
        "src.core.engine.session_architect.SessionArchitect",
        llm=language_model,
        content=content_client,
        pool_builder=pool_builder,
        timeout_seconds=config.provided.PLAN_TIMEOUT_SECONDS,
        max_turns=config.provided.MAX_AGENT_TURNS,
        fast_model_id=config.provided.BEDROCK_FAST_MODEL_ID,
    )

    # ── Services ────────────────────────────────────────
    live_hub = providers.Singleton("src.infrastructure.services.live.LiveHub")
    couch_service = providers.Singleton("src.infrastructure.services.couch.CouchService")
    tv_link_service = providers.Singleton("src.infrastructure.services.tv_link.TvLinkService")

    session_service = providers.Singleton(
        "src.infrastructure.services.session.SessionService",
        session_architect=session_architect,
        session_plan_repository=session_plan_repository,
        taste_profile_repository=taste_profile_repository,
        device_repository=device_repository,
        session_factory=session_factory,
        live_hub=live_hub,
        default_region=config.provided.DEFAULT_REGION,
    )
    mood_service = providers.Singleton(
        "src.infrastructure.services.mood.MoodService",
        llm=language_model,
        session_factory=session_factory,
        fast_model_id=config.provided.BEDROCK_FAST_MODEL_ID,
    )
    content_service = providers.Singleton(
        "src.infrastructure.services.content.ContentService",
        tmdb_client=content_client,
        default_region=config.provided.DEFAULT_REGION,
    )
    profile_service = providers.Singleton(
        "src.infrastructure.services.profile.ProfileService",
        taste_profile_repository=taste_profile_repository,
        device_repository=device_repository,
        session_factory=session_factory,
        default_region=config.provided.DEFAULT_REGION,
    )
    feedback_service = providers.Singleton(
        "src.infrastructure.services.feedback.FeedbackService",
        feedback_repository=feedback_repository,
        taste_profile_repository=taste_profile_repository,
        session_plan_repository=session_plan_repository,
        session_factory=session_factory,
    )
