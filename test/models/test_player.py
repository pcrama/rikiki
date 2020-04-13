import unittest.mock as mock

import pytest

from app.models import (IllegalStateException, Player, Round)

from .helpers import *


@pytest.fixture
def mock_round_with_players(confirmed_player):
    players = [confirmed_player] + [Player(PROVISIONAL_NAME if i == 0 else f"P{i}",
                                           f"secret{i}")
                                    for i in range(1, 3)]
    for (i, p) in enumerate(players):
        p.confirm(CONFIRMED_NAME if i == 0 else None)
    round_ = mock.create_autospec(Round)
    for (p, c) in [(p, [3 * i, 3 * i + 1, 3 * i + 2])
                   for (i, p) in enumerate(players)]:
        p.accept_cards(round_, c)
    return (round_, players)


@pytest.fixture
def player_with_cards(mock_round_with_players):
    (_, [p, *_]) = mock_round_with_players
    return p


@pytest.fixture
def player_with_cards_and_bid(player_with_cards):
    player_with_cards.place_bid(1)
    return player_with_cards


def test_Player__init__name_is_provisional_name(new_player):
    assert new_player.name == PROVISIONAL_NAME


def test_Player__init__secret_id_is_recorded(new_player):
    assert new_player.secret_id == "secret id"


def test_Player__init__not_confirmed_yet(new_player):
    assert not new_player.is_confirmed


def test_Player__init__no_bid_placed(new_player):
    assert not new_player.has_bid


def test_Player__unconfirmed__takes_provisional_name_with_None(new_player):
    new_player.confirm(None)
    assert new_player._confirmed_name == PROVISIONAL_NAME


def test_Player__unconfirmed__takes_provisional_name_with_blanks(new_player):
    new_player.confirm("  ")
    assert new_player._confirmed_name == PROVISIONAL_NAME


def test_Player__unconfirmed__does_not_accept_cards(new_player):
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.accept_cards(mock_round(), [1, 2, 3])
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_without_cards__will_not_bid(new_player):
    new_player.confirm(CONFIRMED_NAME)
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.place_bid(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_not_bid_more_than_amount_of_cards(player_with_cards):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards.place_bid(4)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards_in_round__will_bid(mock_round_with_players):
    (round_, [player_with_cards, *_]) = mock_round_with_players
    player_with_cards.place_bid(1)
    assert player_with_cards.bid == 1
    round_.place_bid.assert_called_with(player_with_cards, 1)


def test_Player__unconfirmed__will_not_play_card(new_player):
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.play_card(2)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_without_cards__will_not_play_card(new_player):
    new_player.confirm(CONFIRMED_NAME)
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.play_card(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_not_play_before_bidding(player_with_cards):
    with pytest.raises(IllegalStateException) as excinfo:
        player_with_cards.play_card(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_play_one_of_his_cards(mock_round_with_players):
    (round_, [player_with_cards, *_]) = mock_round_with_players
    player_with_cards.place_bid(2)
    before = len(player_with_cards._cards)
    assert player_with_cards.play_card(2) == 2
    assert len(player_with_cards._cards) + 1 == before
    assert 2 not in player_with_cards._cards
    round_.play_card.assert_called_with(player_with_cards, 2)


def test_Player__confirmed_with_cards_and_bid__will_play_only_his_cards(player_with_cards_and_bid):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards_and_bid.play_card(101)


# def test_Round__init__validates_Players(confirmed_player):
#     with pytest.raises(ValueError):
#         Round([confirmed_player, Player("Other player", "other secret")], 3)


# def test_Round__init__validates_Player_count(confirmed_player):
#     with pytest.raises(ValueError):
#         Round([confirmed_player], 3)


# def test_Round__init_0_cards_to_deal__raises(confirmed_player):
#     with pytest.raises(ValueError):
#         Round([confirmed_player], 0)


# def test_Round__init_too_many_cards_to_deal__raises(confirmed_player):
#     with pytest.raises(ValueError):
#         Round([confirmed_player], 53)


# def test_Round__init__deals_cards(mock_confirmed_players):
#     HOW_MANY_CARDS = 5
#     round_ = Round(mock_confirmed_players, HOW_MANY_CARDS)
#     observed_deck = set()  # all cards must be different from each other
#     for m in mock_confirmed_players:
#         assert len(m.accept_cards.mock_calls) == 1
#         # import pdb
#         # pdb.set_trace()
#         ((observed_round, observed_cards), _) = m.accept_cards.call_args
#         assert observed_round is round_
#         assert len(observed_cards) == HOW_MANY_CARDS
#         observed_deck.update(observed_cards)
#     assert len(observed_deck) == len(mock_confirmed_players) * HOW_MANY_CARDS
