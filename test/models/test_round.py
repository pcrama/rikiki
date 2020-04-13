import unittest.mock as mock

import pytest

from app.models import (IllegalStateException, Player, Round)

from .helpers import *


@pytest.fixture()
def mock_confirmed_players():
    mock_players = [mock.create_autospec(Player) for _ in range(3)]
    for m in mock_players:
        m.configure_mock(is_confirmed=True)
    return mock_players


def test_Round__init__validates_Players(confirmed_player):
    with pytest.raises(ValueError):
        Round([confirmed_player, Player("Other player", "other secret")], 3)


def test_Round__init__validates_Player_count(confirmed_player):
    with pytest.raises(ValueError):
        Round([confirmed_player], 3)


def test_Round__init_0_cards_to_deal__raises(confirmed_player):
    with pytest.raises(ValueError):
        Round([confirmed_player], 0)


def test_Round__init_too_many_cards_to_deal__raises(confirmed_player):
    with pytest.raises(ValueError):
        Round([confirmed_player], 53)


def test_Round__init__deals_cards(mock_confirmed_players):
    HOW_MANY_CARDS = 5
    round_ = Round(mock_confirmed_players, HOW_MANY_CARDS)
    observed_deck = set()  # all cards must be different from each other
    for m in mock_confirmed_players:
        assert len(m.accept_cards.mock_calls) == 1
        # import pdb
        # pdb.set_trace()
        ((observed_round, observed_cards), _) = m.accept_cards.call_args
        assert observed_round is round_
        assert len(observed_cards) == HOW_MANY_CARDS
        observed_deck.update(observed_cards)
    assert len(observed_deck) == len(mock_confirmed_players) * HOW_MANY_CARDS
