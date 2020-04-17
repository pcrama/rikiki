import unittest.mock as mock

import pytest

from app.models import (
    Game,
    IllegalStateError,
    MAX_CARDS,
    ModelError,
    OutOfTurnError,
    Player,
    Round,
)

from .helpers import *


def test_Game__init__has_players(new_game_waiting_room):
    assert new_game_waiting_room.players is not None


def test_Game__init__has_no_confirmed_players_yet(new_game_waiting_room):
    assert new_game_waiting_room.confirmed_players == []


def test_Game__init__is_in_confirming_state(new_game_waiting_room):
    assert new_game_waiting_room.state == Game.State.CONFIRMING


def test_Game__start_game_not_enough_players_confirmed__raises(new_game_waiting_room):
    # Can't start a Game without any confirmed player
    with pytest.raises(IllegalStateError):
        new_game_waiting_room.start_game()
    assert new_game_waiting_room.state == Game.State.CONFIRMING
    # Can't start a Game with only one confirmed player
    new_game_waiting_room.players[0].confirm("P0")
    with pytest.raises(IllegalStateError):
        new_game_waiting_room.start_game()
    assert new_game_waiting_room.state == Game.State.CONFIRMING
    # Can start a Game with at least 2 players
    new_game_waiting_room.players[1].confirm("P1")
    new_game_waiting_room.start_game()
    assert new_game_waiting_room.state == Game.State.PLAYING


def test_Game__start_game__keeps_only_confirmed_players(new_game_waiting_room):
    unconfirmed_players = new_game_waiting_room.players
    unconfirmed_players[0].confirm("P0")
    unconfirmed_players[1].confirm("P1")
    assert any(
        not player.is_confirmed for player in unconfirmed_players
    ), "Test makes no sense if there isn't at least one unconfirmed player"
    new_game_waiting_room.start_game()
    assert new_game_waiting_room.state == Game.State.PLAYING
    assert len(new_game_waiting_room.confirmed_players) == 2
    unconfirmed_players[2].confirm("P2 confirmed too late")
    assert len(new_game_waiting_room.confirmed_players) == 2


def test_Game__confirm_1_player__no_confirmed_players_because_game_not_started(new_game_waiting_room):
    players = new_game_waiting_room.players
    players[1].confirm("P1")
    assert new_game_waiting_room.confirmed_players == []


def test_Game__confirm_2_players__no_confirmed_players_until_game_started(new_game_waiting_room):
    players = new_game_waiting_room.players
    players[1].confirm("P1")
    players[0].confirm("P0")
    assert new_game_waiting_room.confirmed_players == []
    new_game_waiting_room.start_game()
    assert new_game_waiting_room.confirmed_players == [players[0], players[1]]


def test_Game__start_game__sets_card_count(new_game_with_confirmed_players):
    first_round = new_game_with_confirmed_players.start_game()
    confirmed_players = new_game_with_confirmed_players.confirmed_players
    # All players have received their cards (that is actually a Round
    # property/test):
    assert all(p.card_count == new_game_with_confirmed_players.current_card_count
               for p in confirmed_players)
    # The Game started a Round with the maximum amount of cards possible
    assert MAX_CARDS < ((confirmed_players[0].card_count + 1) *
                        len(confirmed_players))


def test_Game__round_finished__reduces_card_count(new_game_with_confirmed_players):
    first_round = new_game_with_confirmed_players.start_game()
    confirmed_players = new_game_with_confirmed_players.confirmed_players
    initial_card_count = new_game_with_confirmed_players.current_card_count
    # reset all players hands, so that they can join a new game
    for p in confirmed_players:
        p._cards = []
    new_game_with_confirmed_players.round_finished()
    assert all(p.card_count == (initial_card_count - 1)
               for p in confirmed_players)
    assert new_game_with_confirmed_players.current_card_count == (
        initial_card_count - 1)
