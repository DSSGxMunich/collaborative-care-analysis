"""Shared fixtures for the test suite."""

import pytest
from loguru import logger


@pytest.fixture
def captured_logs():
    """Collect loguru output for the duration of a test.

    The package logs through loguru, which does not pass through pytest's
    ``caplog``. This attaches a sink that appends formatted messages to a list
    and removes it again afterwards, so tests can assert on what was reported
    without depending on the global handler configuration.
    """
    messages: list[str] = []
    sink_id = logger.add(lambda message: messages.append(str(message)), level="DEBUG")
    yield messages
    logger.remove(sink_id)
