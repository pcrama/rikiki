import unittest.mock as mock

import pytest

from app.models import (IllegalStateError, Player, Round)

from .helpers import *


@pytest.fixture
def mock_round_with_players(confirmed_player):
    players = [
        confirmed_player
    ] + [
        Player(PROVISIONAL_NAME if i == 0 else f"P{i}",
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


def test_Player__init__has_no_tricks(new_player):
    assert new_player.tricks == 0


def test_Player__unconfirmed__takes_provisional_name_with_None(new_player):
    new_player.confirm(None)
    assert new_player._confirmed_name == PROVISIONAL_NAME


def test_Player__unconfirmed__takes_provisional_name_with_blanks(new_player):
    new_player.confirm("  ")
    assert new_player._confirmed_name == PROVISIONAL_NAME


def test_Player__unconfirmed__does_not_accept_cards(new_player):
    with pytest.raises(IllegalStateError) as excinfo:
        new_player.accept_cards(mock_round(), [1, 2, 3])
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_without_cards__will_not_bid(new_player):
    new_player.confirm(CONFIRMED_NAME)
    with pytest.raises(IllegalStateError) as excinfo:
        new_player.place_bid(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_accepting_cards__has_right_amount_of_cards(
        confirmed_player):
    round_ = mock_round()
    confirmed_player.accept_cards(round_, [1, 2, 3])
    assert confirmed_player.card_count == 3


def test_Player__confirmed_accepting_cards__resets_trick_count(
        confirmed_player):
    round_ = mock_round()
    confirmed_player.accept_cards(round_, [1])
    confirmed_player.place_bid(1)
    confirmed_player.play_card(1)
    confirmed_player.add_trick()
    assert confirmed_player.tricks == 1, "Test setup failed"
    confirmed_player.accept_cards(round_, [1, 2, 3])
    confirmed_player.add_trick()


def test_Player__confirmed_with_cards__will_not_bid_more_than_amount_of_cards(
        player_with_cards):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards.place_bid(4)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards_in_round__will_bid(
        mock_round_with_players):
    (round_, [player_with_cards, *_]) = mock_round_with_players
    player_with_cards.place_bid(1)
    assert player_with_cards.bid == 1
    round_.place_bid.assert_called_with(player_with_cards, 1)


def test_Player__unconfirmed__will_not_play_card(new_player):
    with pytest.raises(IllegalStateError) as excinfo:
        new_player.play_card(2)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_without_cards__will_not_play_card(new_player):
    new_player.confirm(CONFIRMED_NAME)
    with pytest.raises(IllegalStateError) as excinfo:
        new_player.play_card(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_not_play_before_bidding(
        player_with_cards):
    with pytest.raises(IllegalStateError) as excinfo:
        player_with_cards.play_card(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_play_one_of_his_cards(
        mock_round_with_players):
    (round_, [player_with_cards, *_]) = mock_round_with_players
    before = player_with_cards.card_count
    player_with_cards.place_bid(2)
    assert player_with_cards.card_count == before
    assert player_with_cards.play_card(2) == 2
    assert player_with_cards.card_count + 1 == before
    assert 2 not in player_with_cards._cards
    round_.play_card.assert_called_with(player_with_cards, 2)


def test_Player__confirmed_with_cards_and_bid__will_play_only_his_cards(
        player_with_cards_and_bid):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards_and_bid.play_card(101)


def test_Player__confirmed_with_cards_and_bid__will_accept_trick_attribution(
        player_with_cards_and_bid):
    # Start at 0
    assert player_with_cards_and_bid.tricks == 0
    player_with_cards_and_bid.add_trick()
    assert player_with_cards_and_bid.tricks == 1
    player_with_cards_and_bid.add_trick()
    assert player_with_cards_and_bid.tricks == 2


def test_Player__init__accepts_no_tricks(new_player):
    with pytest.raises(IllegalStateError):
        new_player.add_trick()


def test_Player__confirmed_without_cards__accepts_no_trick(confirmed_player):
    with pytest.raises(IllegalStateError):
        confirmed_player.add_trick()
