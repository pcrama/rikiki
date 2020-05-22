import unittest.mock as mock

import pytest                   # type: ignore

from app.models import (
    Game,
    IllegalStateError,
    MAX_CARDS,
    ModelError,
    OutOfTurnError,
    Player,
    PlayerRetryableError,
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


def test_Game__round_finished__pauses_game(new_game_with_confirmed_players):
    first_round = new_game_with_confirmed_players.start_game()
    confirmed_players = new_game_with_confirmed_players.confirmed_players
    initial_card_count = new_game_with_confirmed_players.current_card_count
    new_game_with_confirmed_players.round_finished()
    assert all(p.card_count == initial_card_count
               for p in confirmed_players)
    assert new_game_with_confirmed_players.state == Game.State.PAUSED_BETWEEN_ROUNDS
    assert new_game_with_confirmed_players.current_card_count == initial_card_count


def test_Game__start_next_round__reduces_card_count(new_game_with_confirmed_players):
    first_round = new_game_with_confirmed_players.start_game()
    confirmed_players = new_game_with_confirmed_players.confirmed_players
    initial_card_count = new_game_with_confirmed_players.current_card_count
    # reset all players hands, so that they can join a new round
    for p in confirmed_players:
        p._cards = []
    new_game_with_confirmed_players.round_finished()
    new_game_with_confirmed_players.start_next_round()
    assert all(p.card_count == (initial_card_count - 1)
               for p in confirmed_players)
    assert new_game_with_confirmed_players.current_card_count == (
        initial_card_count - 1)


def test_Game__start_next_round__rotates_confirmed_players(new_game_with_confirmed_players):
    game = new_game_with_confirmed_players
    first_round = game.start_game()
    # reset all players hands, so that they can join a new round
    for p in game.confirmed_players:
        p._cards = []
    game.round_finished()
    old_confirmed_players = [p for p in game.confirmed_players]
    game.start_next_round()
    new_confirmed_players = game.confirmed_players
    assert new_confirmed_players == (
        old_confirmed_players[1:] + [old_confirmed_players[0]])


def test_Game__player_by_id__returns_player(new_game_with_confirmed_players):
    for p in new_game_with_confirmed_players.players:
        by_id = new_game_with_confirmed_players.player_by_id(p.id)
        assert p is by_id
    with pytest.raises(StopIteration):
        new_game_with_confirmed_players.player_by_id(
            'this public ID does not exist')


def test_Game__player_by_secret_id__returns_player(new_game_with_confirmed_players):
    for p in new_game_with_confirmed_players.players:
        by_id = new_game_with_confirmed_players.player_by_secret_id(
            p.secret_id)
        assert p is by_id
    with pytest.raises(StopIteration):
        new_game_with_confirmed_players.player_by_secret_id(
            'this public ID does not exist')


def test_Game__full_scenario():
    PLAYER_DOES_NOT_SHOW_UP = 3
    players = [Player(f"P{i}", f"Secret {i}") for i in range(5)]
    game = Game(players)
    assert game.state == Game.State.CONFIRMING
    for (idx, p) in enumerate(players):
        if idx != PLAYER_DOES_NOT_SHOW_UP:
            p.confirm("")
    game.start_game()
    assert game.round is not None
    assert game.state == Game.State.PLAYING
    assert game.confirmed_players == [
        p for (idx, p) in enumerate(players) if idx != PLAYER_DOES_NOT_SHOW_UP]
    round_count = 0
    previous_card_count = None
    confirmed_players = list(game.confirmed_players)
    # Needed to select a slice covering all players, but starting at
    # the right player for the trick in the given round
    full_range = confirmed_players + confirmed_players
    while game.state == Game.State.PLAYING and round_count < MAX_CARDS:
        round_ = game.round
        if previous_card_count is not None:
            assert game.current_card_count == previous_card_count - 1
        previous_card_count = game.current_card_count
        round_count += 1
        assert round_._state == Round.State.BIDDING
        for p in game.confirmed_players:
            assert p.card_count == game.current_card_count
            assert not p.has_bid
            p.place_bid(0)
            assert p.has_bid
        for cards_played in range(game.current_card_count):
            assert round_._state == (
                Round.State.PLAYING if cards_played == 0 else Round.State.BETWEEN_TRICKS)
            assert sum(p.tricks for p in confirmed_players) == cards_played
            idx = 0
            for p in confirmed_players:
                if p is round_.current_player:
                    break
                else:
                    # while we're at it, check that round_ will not let others play
                    with pytest.raises(OutOfTurnError):
                        p.play_card(p._cards[0])
                    assert p.card_count == game.current_card_count - cards_played
                    idx += 1
            for p in full_range[idx:(idx + len(confirmed_players))]:
                assert p.card_count == game.current_card_count - cards_played
                for c in p.cards:
                    try:
                        p.play_card(c)
                    except PlayerRetryableError:
                        pass
                    else:
                        break
                if game.current_card_count > cards_played + 1:
                    assert p.card_count == game.current_card_count - cards_played - 1
        assert round_._state == Round.State.DONE
        assert game.state == Game.State.PAUSED_BETWEEN_ROUNDS
        # Round must remain accessible so that Players can see last
        # Round's last trick's last card:
        assert game.round is round_
        assert sum(p.tricks for p in confirmed_players) == game.current_card_count
        game.start_next_round()
    assert game.current_card_count == 0
    assert game.state == Game.State.DONE


def test_Game__status_summary(new_game_waiting_room):
    game = new_game_waiting_room
    summaries = [game.status_summary()]
    assert summaries[0] == game.status_summary()
    game.players[1].confirm('a')
    summaries.append(game.status_summary())
    assert len(set(summaries)) == len(summaries)
    game.players[0].confirm('abcdefgh')
    summaries.append(game.status_summary())
    assert len(set(summaries)) == len(summaries)
    for p in game.players:
        if not p.is_confirmed:
            p.confirm('')
            summaries.append(game.status_summary())
            assert len(set(summaries)) == len(summaries)
    round_ = game.start_game()
    summaries.append(game.status_summary())
    assert len(set(summaries)) == len(summaries)
    for p in game.confirmed_players:
        p.place_bid(0)
        summaries.append(game.status_summary())
        assert len(set(summaries)) == len(summaries)
