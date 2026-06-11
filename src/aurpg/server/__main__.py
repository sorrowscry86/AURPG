"""Entry point: ``python -m aurpg.server`` or ``aurpg-server`` CLI."""

from __future__ import annotations


def main() -> None:
    import uvicorn  # noqa: PLC0415

    from aurpg.server._settings import get_app_settings  # noqa: PLC0415

    port = get_app_settings().port
    uvicorn.run(
        "aurpg.server.app:app",
        host="127.0.0.1",
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
