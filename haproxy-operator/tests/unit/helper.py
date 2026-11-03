# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for unit tests."""

import re
from pathlib import Path
from unittest.mock import MagicMock


def rendered_file_content(render_file_mock: MagicMock, path: Path | None = None) -> str:
    """Return the content passed to a mocked ``render_file`` call.

    Prefers the ``content`` keyword argument and falls back to the second
    positional argument so the helper keeps working if the call style changes.

    Args:
        render_file_mock: Mock standing in for ``render_file``.
        path: Optional path used to select a specific rendered file.

    Returns:
        The rendered file content.

    Raises:
        AssertionError: If no matching ``render_file`` call was made.
    """
    calls = list(render_file_mock.call_args_list)
    if path is not None:
        calls = [
            call
            for call in calls
            if (call.kwargs.get("path") or (call.args[0] if call.args else None)) == path
        ]
    assert calls, f"No render_file call found for path {path!r}"
    call = calls[0]
    if "content" in call.kwargs:
        return call.kwargs["content"]
    assert len(call.args) > 1, "render_file call does not contain content"
    return call.args[1]


class RegexMatcher:
    """Regex matcher for unittest mocks."""

    def __init__(self, pattern):
        """Initialize with the regex pattern."""
        self.pattern = re.compile(pattern)

    def __eq__(self, other):
        """Compare the str argument against the regex."""
        return bool(self.pattern.search(other))

    def __repr__(self):
        """Representation of the matcher."""
        return f"<RegexMatcher {self.pattern.pattern!r}>"
