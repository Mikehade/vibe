from dependency_injector import containers, providers

from src.config.base import get_settings
from src.infrastructure.db.session import Database


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
        ]
    )

    # ── Config ──────────────────────────────────────────
    config = providers.Singleton(get_settings)

    # ── Database ────────────────────────────────────────
    database = providers.Singleton(
        Database,
        database_url=config.provided.DATABASE_URL,
        # echo=providers.Callable(lambda cfg: cfg.ENV == "development", config),
        echo=False,
    )

    session_factory = providers.Factory(
        lambda db: db.session_factory,
        database,
    )

    # ── Repositories ────────────────────────────────────
    device_repository = providers.Singleton(
        "src.infrastructure.repository.user.DeviceRepository",
        session_factory=session_factory,
    )

    taste_profile_repository = providers.Singleton(
        "src.infrastructure.repository.taste_profile.TasteProfileRepository",
        session_factory=session_factory,
    )

    session_plan_repository = providers.Singleton(
        "src.infrastructure.repository.session_plan.SessionPlanRepository",
        session_factory=session_factory,
    )

    feedback_repository = providers.Singleton(
        "src.infrastructure.repository.feedback.FeedbackRepository",
        session_factory=session_factory,
    )

    # ── External Clients ────────────────────────────────
    tmdb_client = providers.Singleton(
        "src.infrastructure.clients.tmdb.TMDBClient",
        api_key=config.provided.TMDB_API_KEY,
        base_url=config.provided.TMDB_BASE_URL,
    )

    justwatch_client = providers.Singleton(
        "src.infrastructure.clients.justwatch.JustWatchClient",
        country=config.provided.JUSTWATCH_COUNTRY,
        tmdb_client=tmdb_client,
    )

    # ── Language Model ──────────────────────────────────
    bedrock_model = providers.Singleton(
        "src.infrastructure.language_models.bedrock.BedrockModel",
        model_id=config.provided.BEDROCK_MODEL_ID,
        region=config.provided.AWS_REGION,
        max_tool_iterations=config.provided.MAX_TOOL_ITERATIONS,
    )

    # ── Tools ───────────────────────────────────────────
    content_tools = providers.Singleton(
        "src.core.tools.content_tools.ContentTools",
        tmdb_client=tmdb_client,
    )

    profile_tools = providers.Singleton(
        "src.core.tools.profile_tools.ProfileTools",
        taste_profile_repository=taste_profile_repository,
        session_factory=session_factory,
    )

    availability_tools = providers.Singleton(
        "src.core.tools.availability_tools.AvailabilityTools",
        justwatch_client=justwatch_client,
    )

    tool_registry = providers.Singleton(
        "src.core.tools.base.ToolRegistry",
        tools=providers.List(content_tools, profile_tools, availability_tools),
    )

    # ── Core Engine ─────────────────────────────────────
    session_architect = providers.Singleton(
        "src.core.engine.session_architect.SessionArchitect",
        llm=bedrock_model,
        tool_registry=tool_registry,
    )

    # ── Services ────────────────────────────────────────
    session_service = providers.Singleton(
        "src.infrastructure.services.session.SessionService",
        session_architect=session_architect,
        session_plan_repository=session_plan_repository,
        taste_profile_repository=taste_profile_repository,
        device_repository=device_repository,
        session_factory=session_factory,
    )

    mood_service = providers.Singleton(
        "src.infrastructure.services.mood.MoodService",
        llm=bedrock_model,
        session_factory=session_factory,
    )

    content_service = providers.Singleton(
        "src.infrastructure.services.content.ContentService",
        tmdb_client=tmdb_client,
        justwatch_client=justwatch_client,
    )

    profile_service = providers.Singleton(
        "src.infrastructure.services.profile.ProfileService",
        taste_profile_repository=taste_profile_repository,
        device_repository=device_repository,
        session_factory=session_factory,
    )

    feedback_service = providers.Singleton(
        "src.infrastructure.services.feedback.FeedbackService",
        feedback_repository=feedback_repository,
        taste_profile_repository=taste_profile_repository,
        session_plan_repository=session_plan_repository,
        session_factory=session_factory,
    )
