import pytest

from app.models import (Player, IllegalStateException)

PROVISIONAL_NAME = "provisional name"
CONFIRMED_NAME = "Abcdef"


@pytest.fixture
def new_player():
    return Player(PROVISIONAL_NAME, "secret id")


@pytest.fixture
def player_with_cards_and_bid(new_player):
    new_player.confirm(CONFIRMED_NAME)
    new_player.accept_cards([2, 3, 4])
    new_player.place_bid(1)
    return new_player


def test_Player__init__name_is_provisional_name(new_player):
    assert new_player.name == PROVISIONAL_NAME


def test_Player__init__secret_id_is_recorded(new_player):
    assert new_player.secret_id == "secret id"


def test_Player__init__not_confirmed_yet(new_player):
    assert not new_player.is_confirmed


def test_Player__init__no_bid_placed(new_player):
    assert not new_player.has_bid


def test_Player__not_confirmed__does_not_accept_cards(new_player):
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.accept_cards([1, 2, 3])
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_without_cards__will_not_bid(new_player):
    new_player.confirm(CONFIRMED_NAME)
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.place_bid(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_not_bid_more_than_amount_of_cards(player_with_cards):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards_and_bid.place_bid(4)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_not_bid_more_than_amount_of_cards(player_with_cards_and_bid):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards_and_bid.place_bid(4)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_bid(player_with_cards_and_bid):
    player_with_cards_and_bid.place_bid(3)
    assert player_with_cards_and_bid.bid == 3


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


def test_Player__confirmed_without_cards__will_not_play_before_bidding(new_player):
    new_player.confirm(CONFIRMED_NAME)
    new_player.accept_cards([1, 2, 3, 4])
    with pytest.raises(IllegalStateException) as excinfo:
        new_player.play_card(2)
    assert excinfo.value.args[0].startswith(CONFIRMED_NAME)
    assert PROVISIONAL_NAME in excinfo.value.args[0]


def test_Player__confirmed_with_cards__will_play_one_of_his_cards(player_with_cards_and_bid):
    before = len(player_with_cards_and_bid._cards)
    assert player_with_cards_and_bid.play_card(2) == 2
    assert len(player_with_cards_and_bid._cards) + 1 == before
    assert 2 not in player_with_cards_and_bid._cards


def test_Player__confirmed_with_cards__will_play_only_his_cards(player_with_cards_and_bid):
    with pytest.raises(ValueError) as excinfo:
        player_with_cards_and_bid.play_card(101)
