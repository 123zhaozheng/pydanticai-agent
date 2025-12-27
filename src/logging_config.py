"""Logfire logging configuration for the application.

This module provides centralized logging configuration using Logfire,
a structured logging and observability platform from the Pydantic team.

Usage:
    from src.logging_config import configure_logging
    
    # Call once at startup, before creating FastAPI app
    configure_logging()
    
    # Then in any module:
    import logfire
    logfire.info("Hello {name}", name="World")
"""

import os
import logfire


def configure_logging(
    service_name: str = "pydantic-deep",
    environment: str | None = None,
    console_output: bool = True,
) -> None:
    """Configure Logfire for the entire application.
    
    This function:
    1. Configures logfire console output
    2. Instruments PydanticAI (Agent runs, model calls, tool execution)
    3. Instruments httpx (LLM HTTP requests)
    
    Args:
        service_name: Service name for tracing
        environment: Environment name (development/staging/production).
                    If None, reads from APP_ENV or defaults to 'development'.
        console_output: Whether to output to console
    """
    env = environment or os.environ.get("APP_ENV", "development")
    is_dev = env == "development"
    
    # 1. Configure logfire base settings
    logfire.configure(
        service_name=service_name,
        send_to_logfire=False,  # Set to True to send to Logfire cloud
        console=logfire.ConsoleOptions(
            colors='auto',
            span_style='indented',
            verbose=is_dev,
            include_timestamps=True,
            min_log_level='debug' if is_dev else 'info',
        ) if console_output else False,
    )
    
    # 2. Instrument PydanticAI (Agent runs, model calls, tool execution)
    logfire.instrument_pydantic_ai()
    
    # 3. Instrument httpx (LLM HTTP requests)
    logfire.instrument_httpx(capture_all=True)


def instrument_fastapi(app):
    """Instrument FastAPI app with logfire.
    
    Call this after creating the FastAPI app instance.
    
    Args:
        app: FastAPI application instance
    """
    logfire.instrument_fastapi(app)
