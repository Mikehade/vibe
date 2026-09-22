import logging
import sys

try:
    import colorlog

    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

_configured = False


def get_logger(name: str | None = None) -> logging.Logger:
    global _configured
    logger = logging.getLogger(name or "vibe")

    if not _configured:
        from src.config.base import get_settings

        settings = get_settings()
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.DEBUG)
        root = logging.getLogger("vibe")
        root.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        if settings.ENV == "production":
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"module":"%(name)s","message":"%(message)s"}',
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        elif HAS_COLORLOG:
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s%(levelname)-8s%(reset)s "
                "%(cyan)s%(asctime)s%(reset)s "
                "%(white)s%(name)s%(reset)s — %(message)s",
                datefmt="%H:%M:%S",
                log_colors={
                    "DEBUG": "white",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
        else:
            formatter = logging.Formatter(
                "%(levelname)-8s %(asctime)s %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )

        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.propagate = False
        _configured = True

    return logger
