# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Helper methods for unit tests."""

import re


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
