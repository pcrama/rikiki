import unittest.mock as mock

import pytest

from app.models import (
    IllegalStateError,
    ModelError,
    OutOfTurnError,
    Player,
    Round,
)

from .helpers import *


@pytest.fixture()
def mock_confirmed_players():
    mock_players = [mock.create_autospec(Player) for _ in range(3)]
    for m in mock_players:
        m.configure_mock(is_confirmed=True)
    return mock_players


@pytest.fixture
def round_with_mock_confirmed_players(mock_confirmed_players):
    return Round(mock_confirmed_players, 4)


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


def test_Round__init__starts_in_bidding_state(
        round_with_mock_confirmed_players):
    assert round_with_mock_confirmed_players._state == Round.State.BIDDING


def test_Round__place_bid__validates_bid_origin(
        mock_confirmed_players):
    round_ = Round(mock_confirmed_players, 5)
    for player in mock_confirmed_players:
        # before player has placed a bit, no other player may bid
        for other_player in mock_confirmed_players:
            if player is not other_player:
                with pytest.raises(OutOfTurnError) as excinfo:
                    round_.place_bid(other_player, 3)
                assert excinfo.value.operation == "bid"
                assert excinfo.value.current_player is player
                assert excinfo.value.offending_player is other_player
        round_.place_bid(player, 3)
        # once player has bid, he can't bid again, last player is
        # special case, see other test case:
        if player is not mock_confirmed_players[-1]:
            with pytest.raises(OutOfTurnError) as excinfo:
                round_.place_bid(player, 3)
            assert excinfo.value.operation == "bid"
            assert excinfo.value.offending_player is player


def test_Round__place_bid__goes_to_playing_state_after_last_bid(
        mock_confirmed_players):
    round_ = Round(mock_confirmed_players, 5)
    for player in mock_confirmed_players:
        round_.place_bid(player, 3)
    assert round_.current_player is mock_confirmed_players[0]
    assert round_._state == Round.State.PLAYING
    with pytest.raises(IllegalStateError):
        # It is the first player's turn, but she should play_card, not
        # place_bid:
        round_.place_bid(mock_confirmed_players[0], 3)
