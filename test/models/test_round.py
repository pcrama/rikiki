import unittest.mock as mock

import pytest

from app.models import (
    Card,
    IllegalStateError,
    MAX_CARDS,
    ModelError,
    OutOfTurnError,
    Player,
    Round,
)

from .helpers import *


@pytest.fixture
def mock_confirmed_players():
    mock_players = [mock.create_autospec(Player) for _ in range(3)]
    for m in mock_players:
        m.configure_mock(is_confirmed=True)
    return mock_players


@pytest.fixture
def round_with_mock_confirmed_players(mock_confirmed_players):
    return Round(mock_confirmed_players, 3)


@pytest.fixture
def round_with_bids_placed(mock_confirmed_players):
    HOW_MANY_CARDS = 2
    round_ = Round(mock_confirmed_players, HOW_MANY_CARDS)
    for player in mock_confirmed_players:
        round_.place_bid(player, HOW_MANY_CARDS)
        player.configure_mock(card_count=HOW_MANY_CARDS)
    return (round_, mock_confirmed_players)


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
        ((observed_round, observed_cards), _) = m.accept_cards.call_args
        assert observed_round is round_
        assert len(observed_cards) == HOW_MANY_CARDS
        observed_deck.update(observed_cards)
    assert len(observed_deck) == len(mock_confirmed_players) * HOW_MANY_CARDS


def test_Round__init__starts_in_bidding_state(
        round_with_mock_confirmed_players):
    assert round_with_mock_confirmed_players._state == Round.State.BIDDING


def test_Round__deal_cards__sets_trump_card(
        mock_confirmed_players):
    assert len(mock_confirmed_players) < MAX_CARDS, \
        f"This test only works if there are less than {MAX_CARDS} players"
    round_ = Round(mock_confirmed_players, 1)
    assert round_.trump is not None


def test_Round__deal_cards__sets_no_trump_card_when_evenly_divided():
    round_ = Round([mock_player() for _ in range(4)], 13)
    assert round_.trump is None


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


def test_Round__play_card__validates_state(round_with_mock_confirmed_players):
    with pytest.raises(IllegalStateError):
        round_with_mock_confirmed_players.play_card(
            round_with_mock_confirmed_players._players[0],
            Card.Heart3)


def test_Round__play_card__validates_card_count_of_all_players_at_end_of_round(
        round_with_bids_placed):
    (round_, mock_confirmed_players) = round_with_bids_placed
    for player in mock_confirmed_players:
        player.configure_mock(
            card_count=1 if player is mock_confirmed_players[0] else 0)
    for p in mock_confirmed_players:
        if p is mock_confirmed_players[-1]:
            p.configure_mock(card_count=1)
            with pytest.raises(IllegalStateError) as excinfo:
                round_.play_card(p, Card.Heart10)
        else:
            p.configure_mock(card_count=0)
            round_.play_card(p, Card.Heart10)
    assert "all their cards" in excinfo.value.args[0]


def test_Round__play_card__validates_player(
        round_with_bids_placed):
    (round_, mock_confirmed_players) = round_with_bids_placed
    assert round_._state == Round.State.PLAYING
    for player in mock_confirmed_players:
        for other_player in mock_confirmed_players:
            if other_player is not player:
                with pytest.raises(OutOfTurnError):
                    round_.play_card(other_player, Card.Diamond10)
        player.configure_mock(  # simulate plater.play_card
            card_count=player.card_count - 1)
        round_.play_card(player, Card.ClubAce)
    assert round_._state == Round.State.PLAYING


def test_Round__play_card__attributes_trick_after_all_played(
        mock_confirmed_players):
    HOW_MANY_CARDS = 3
    players = mock_confirmed_players[:3]
    round_ = Round(players, HOW_MANY_CARDS)
    for p in players:
        p.configure_mock(card_count=HOW_MANY_CARDS)
        round_.place_bid(p, 1)

    def mock_player_plays_card(p, card):
        p.configure_mock(  # simulate player.play_card
            card_count=p.card_count - 1)
        round_.play_card(p, card)

    mock_player_plays_card(players[0], Card.Heart3)
    for p in players:
        p.add_trick.assert_not_called()
    mock_player_plays_card(players[1], Card.Heart10)
    for p in players:
        p.add_trick.assert_not_called()
    mock_player_plays_card(players[2], Card.Heart7)
    players[0].add_trick.assert_not_called()
    players[1].add_trick.assert_called_with()
    players[2].add_trick.assert_not_called()


def test_Round__play_card__goes_to_DONE_state_after_last_card(
        round_with_bids_placed):
    (round_, mock_confirmed_players) = round_with_bids_placed
    assert round_._state == Round.State.PLAYING, \
        "Invalid initial state for test"
    for _ in range(mock_confirmed_players[0].card_count):
        for player in mock_confirmed_players:
            player.configure_mock(  # simulate plater.play_card
                card_count=player.card_count - 1)
            round_.play_card(player, Card.HeartAce)
    assert round_._state == Round.State.DONE


def test_Round__full_scenario(mock_confirmed_players):
    players = mock_confirmed_players[:3]
    round_ = Round(players, 2)
    assert round_.trump is not None
    # Simulate placing bids
    for p in players:
        assert round_._state == Round.State.BIDDING
        round_.place_bid(p, 1)
    assert round_._state == Round.State.PLAYING

    def mock_play_card(p, c, n):
        p.configure_mock(card_count=n)
        round_.play_card(p, c)

    # Simulate first trick
    mock_play_card(players[0], Card.Heart10, 1)
    mock_play_card(players[1], Card.HeartAce, 1)
    mock_play_card(players[2], Card.Heart4, 1)
    players[1].add_trick.assert_called_with()
    assert round_._state == Round.State.PLAYING

    # Simulate second trick
    mock_play_card(players[1], Card.Diamond4, 0)
    mock_play_card(players[2], Card.Diamond10, 0)
    mock_play_card(players[0], Card.DiamondAce, 0)
    players[0].add_trick.assert_called_with()
    assert round_._state == Round.State.DONE
