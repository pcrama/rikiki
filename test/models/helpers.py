"""Helper functions for model tests."""
import unittest.mock as mock

import pytest

from app.models import (Game, Player, Round)

PROVISIONAL_NAME = "provisional name"
CONFIRMED_NAME = "Abcdef"


def mock_game():
    """Return a mock of a Game."""
    return mock.create_autospec(Game)


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


@pytest.fixture
def confirmed_player(new_player):
    """Fixture: Return a new Player who confirmed her name."""
    new_player.confirm(CONFIRMED_NAME)
    return new_player


@pytest.fixture
def new_game_waiting_room():
    """Fixture: Return a new Game with 3 unconfirmed Players."""
    players = [Player(PROVISIONAL_NAME, "secret id")] + \
        [Player(f"P{i}", f"secret {i}") for i in range(2)]
    return Game(players)


@pytest.fixture
def new_game_with_confirmed_players(new_game_waiting_room):
    """Fixture: Return a new Game with 3 confirmed Players."""
    for (i, p) in enumerate(new_game_waiting_room._players):
        p.confirm(CONFIRMED_NAME if i == 0 else "")
    return new_game_waiting_room
