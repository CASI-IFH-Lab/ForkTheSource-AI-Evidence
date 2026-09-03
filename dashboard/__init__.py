"""A2 - the reviewer dashboard. Owner: Arsha.

``theme.py`` holds every colour, label and icon, defined once. ``app.py``
holds the layout and the pure functions the layout reads from, so the
numbers on screen can be tested without Streamlit running.

This package depends on ``src.contract`` and ``src.settings`` - tier-1
shared infrastructure - and on nothing in Ritik's or Roy's lane. In
particular it does NOT import ``src.pipeline``: the dashboard renders a
``Ledger`` that already exists, and A3 is the one moment a live run is
wired in. ``tests/test_layout.py`` enforces that in both directions.
"""
