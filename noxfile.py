"""Run tests with nox."""

from __future__ import annotations

import nox
from nox import Session


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
def tests(session: Session) -> None:
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest", "--doctest-modules")
