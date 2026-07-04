"""Entrypoint kept thin so `uvicorn main:app` works locally and in Docker."""

from dotenv import load_dotenv

load_dotenv()

from graphrag.api import create_app  # noqa: E402  (needs env loaded first)

app = create_app()
