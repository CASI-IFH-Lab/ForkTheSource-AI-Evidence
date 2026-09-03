"""One shared client for the OpenAI-compatible gateway.

Credentials come from the environment (see .env.example) and never from code.
Model names come from config.yaml via src.config - never from here, and never
from a caller's hardcoded string.

Nothing calls this yet: M0 is the skeleton and makes no model requests.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

_MISSING = (
    "{name} is not set. Copy .env.example to .env and paste your own values in.\n"
    "Never commit .env - each teammate uses their own credentials."
)


def get_client() -> OpenAI:
    """Build a client pointed at the gateway named by AIR_BASE_URL."""
    load_dotenv()
    base_url = os.getenv("AIR_BASE_URL")
    api_key = os.getenv("AIR_API_KEY")
    if not base_url:
        raise RuntimeError(_MISSING.format(name="AIR_BASE_URL"))
    if not api_key:
        raise RuntimeError(_MISSING.format(name="AIR_API_KEY"))
    return OpenAI(base_url=base_url, api_key=api_key)
