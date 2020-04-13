"""Helper functions for model tests."""
import unittest.mock as mock

import pytest

from app.models import (Player, Round)

PROVISIONAL_NAME = "provisional name"
CONFIRMED_NAME = "Abcdef"


def mock_player():
    """Return a mock of a Player."""
    return mock.create_autospec(Player)


def mock_round():
    """Return a mock of a Round."""
    return mock.create_autospec(Round)


@pytest.fixture
def new_player():
    """Fixture: Return a new Player."""
    return Player(PROVISIONAL_NAME, "secret id")


@pytest.fixture()
def confirmed_player(new_player):
    """Fixture: Return a new Player who confirmed her name."""
    new_player.confirm(CONFIRMED_NAME)
    return new_player
