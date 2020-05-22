import random

import flask
from jinja2 import escape

import pytest  # type: ignore

import app  # type: ignore
from app.organizer import parse_playerlist  # type: ignore
from app.player import organizer_url_for_player
from app import models

from .helper import (
    CONFIRMED_1ST_NAME,
    FLASH_ERROR,
    client,
    confirmed_first_player,
    confirmed_last_player,
    first_player,
    game,
    game_with_started_round,
    rendered_template,
    rikiki_app,
    started_game,
)


def test_player_confirm__no_game_created_so_no_players__get_with_wrong_secret(
        rikiki_app, client):
    response = client.get('/player/confirm/wrong_secret',
                          follow_redirects=True)
    assert response.status_code == 403


def test_player_confirm__no_game_created_so_no_players__post_without_secret(
        rikiki_app, client):
    response = client.post('/player/confirm/', follow_redirects=True)
    assert response.status_code == 403


def test_player_confirm__game_exists__get_without_valid_secret(client, game):
    response = client.get('/player/confirm/')
    assert response.status_code == 403
    response = client.get('/player/confirm', follow_redirects=True)
    assert response.status_code == 403
    response = client.get('/player/confirm/wrong_secret/')
    assert response.status_code == 403


def test_player_confirm_game_exists__get_with_secret(first_player, client):
    response = client.get(
        f'/player/confirm/{first_player.secret_id}', follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert rendered_template(response, 'player.confirm')
    response = client.get(
        f'/player/confirm/{first_player.secret_id}/')
    assert response.status_code == 200


def test_player_confirm__game_exists__post_confirmation_without_valid_secret(first_player, client):
    for invalid_secret_data in [
            {},
            {'secret_id': 'wrong_secret'},
            {'player_name': 'confirmed_name'},
            {'secret_id': 'wrong_secret',
             'player_name': 'confirmed_name'}
    ]:
        response = client.post(
            '/player/confirm/', data=invalid_secret_data)
        assert response.status_code == 403


def test_player_confirm__game_exists__post_valid_confirmation(first_player, client):
    NEW_NAME = "new name"
    response = client.post(
        '/player/confirm/',
        data={'secret_id': first_player.secret_id, 'player_name': NEW_NAME},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert first_player.is_confirmed
    assert first_player.name == NEW_NAME
    assert rendered_template(response, 'player.player')
    # check that template contains placeholders for data.  They will
    # be filled in by Javascript.
    assert b'id="players"' in response.data
    assert b'id="stats"' in response.data
    assert b'id="cards"' in response.data
    assert b'setTimeout(' in response.data
    assert b'updatePlayerDashboard' in response.data
    assert bytes(
        f'/player/{first_player.secret_id}/api/status/',
        'utf-8') in response.data


def test_player_confirm__game_started__renders_player_too_late(first_player, client, game):
    for p in game.players:
        if p is not first_player:
            p.confirm('')
    game.start_game()
    response = client.get(f'player/confirm/{first_player.secret_id}/')
    assert response.status_code == 200
    assert rendered_template(response, 'player.too-late')
    assert first_player.name.encode('utf-8') in response.data


def test_player_confirm__already_confirmed__redirects_to_player_dashboard(confirmed_first_player, client):
    response = client.post(
        f'/player/confirm/',
        data={'secret_id': confirmed_first_player.secret_id,
              'confirmed_name': 'yet another name'},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert confirmed_first_player.name == CONFIRMED_1ST_NAME
    assert rendered_template(response, 'player.player')
    response = client.get(
        f'/player/confirm/{confirmed_first_player.secret_id}', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'player.player')
    assert FLASH_ERROR in response.data


def test_player__player__validates_secret_id(confirmed_first_player, client):
    response = client.get('/player/wrong_secret/', follow_redirects=True)
    assert response.status_code == 403
    response = client.get('/player/', follow_redirects=True)
    assert response.status_code == 405


def test_player__unconfirmed__redirects_to_confirmation(first_player, client):
    response = client.get(
        f'/player/{first_player.secret_id}/', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'player.confirm')
    assert FLASH_ERROR in response.data


def test_player__confirmation__invalidates_confirmation_link(first_player, client):
    unconfirmed_secret_id = first_player.secret_id
    confirmation_link = f'/player/confirm/{unconfirmed_secret_id}/'
    response = client.get(confirmation_link, follow_redirects=True)
    assert response.status_code == 200
    response = client.post(f'/player/confirm/',
                           data={'secret_id': first_player.secret_id,
                                 'confirmed_name': 'confirmation name'},
                           follow_redirects=True)
    assert response.status_code == 200
    response = client.get(confirmation_link, follow_redirects=True)
    assert response.status_code == 403
    response = client.post(f'/player/confirm/',
                           data={'secret_id': unconfirmed_secret_id,
                                 'confirmed_name': 'confirmation name'},
                           follow_redirects=True)
    assert response.status_code == 403


def test_place_bid__post_only(first_player, client):
    response = client.get('/player/place/bid/', follow_redirects=True)
    assert response.status_code == 405
    first_player.confirm('')
    response = client.get('/player/place/bid/', follow_redirects=True)
    assert response.status_code == 405


def test_place_bid__player_must_be_confirmed(started_game, client):
    unconfirmed_player = next(
        p for p in started_game.players if not p.is_confirmed)
    response = client.post('/player/place/bid/',
                           data={'secret_id': unconfirmed_player.secret_id},
                           follow_redirects=True)
    assert response.status_code == 404


def test_place_bid__game_or_round_bad_state__404(confirmed_first_player, game, client):
    response = client.post('/player/place/bid/',
                           data={'secret_id': confirmed_first_player.secret_id},
                           follow_redirects=True)
    assert response.status_code == 404
    for p in game.players:
        if not p.is_confirmed:
            p.confirm('')
    game.start_game()
    for p in game.confirmed_players:
        p.place_bid(0)
    for p in game.confirmed_players:
        response = client.post('/player/place/bid/',
                               data={'secret_id': p.secret_id},
                               follow_redirects=True)
        assert response.status_code == 404


def test_place_bid__bad_secret__403(confirmed_first_player, game, client):
    response = client.post(
        '/player/place/bid/',
        data={'secret_id': 'bad_secret'},
        follow_redirects=True)
    assert response.status_code == 403
    response = client.post(
        '/player/place/bid/',
        data={},
        follow_redirects=True)
    assert response.status_code == 403


def test_place_bid__happy_path(started_game, client):
    round_ = started_game.round
    assert round_.state == models.Round.State.BIDDING
    while round_.state == models.Round.State.BIDDING:
        p = round_.current_player
        response = client.post(
            '/player/place/bid/',
            data={'secret_id': p.secret_id, 'bidInput': 1})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert status['ok']
        assert len(status) == 1
        assert p.bid == 1


def test_place_bid__out_of_order(started_game, client):
    round_ = started_game.round
    assert round_.state == models.Round.State.BIDDING
    tested = 0
    for p in started_game.confirmed_players:
        if p is round_.current_player:
            continue
        tested += 1
        response = client.post(
            '/player/place/bid/',
            data={'secret_id': p.secret_id, 'bidInput': 1})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert not status['ok']
        assert round_.current_player.name in status['error']
        assert p.name in status['error']
    assert tested > 0


def test_play_card__post_only(first_player, client):
    response = client.get('/player/play/card/', follow_redirects=True)
    assert response.status_code == 405
    first_player.confirm('')
    response = client.get('/player/play/card/', follow_redirects=True)
    assert response.status_code == 405


def test_play_card__player_must_be_confirmed(started_game, client):
    unconfirmed_player = next(
        p for p in started_game.players if not p.is_confirmed)
    response = client.post('/player/play/card/',
                           data={'secret_id': unconfirmed_player.secret_id},
                           follow_redirects=True)
    assert response.status_code == 404


def test_play_card__game_or_round_bad_state__404(confirmed_first_player, game, client):
    for p in game.players:
        if not p.is_confirmed:
            p.confirm('')
        response = client.post('/player/play/card/',
                               data={'secret_id': p.secret_id,
                                     'card': '0'},
                               follow_redirects=True)
        assert response.status_code == 404
    game.start_game()
    players = game.confirmed_players
    round_ = game.round
    for idx, p in enumerate(players):
        p.place_bid(0)
        if idx < len(players) - 1:
            response = client.post('/player/play/card/',
                                   data={'secret_id': p.secret_id,
                                         'card': int(p.cards[0])},
                                   follow_redirects=True)
            assert response.status_code == 404


def test_play_card__bad_secret__403(confirmed_first_player, game_with_started_round, client):
    response = client.post(
        '/player/play/card/',
        data={'secret_id': 'bad_secret',
              'card': int(confirmed_first_player.cards[0])},
        follow_redirects=True)
    assert response.status_code == 403
    response = client.post(
        '/player/play/card/',
        data={'card': int(confirmed_first_player.cards[0])},
        follow_redirects=True)
    assert response.status_code == 403


def test_play_card__happy_path(game_with_started_round, client):
    round_ = game_with_started_round.round
    assert round_.state == models.Round.State.PLAYING, "Test case precondition not met"
    for p in game_with_started_round.confirmed_players:
        card = p.playable_cards[0]
        response = client.post(
            '/player/play/card/',
            data={'secret_id': p.secret_id, 'card': int(card)})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert status['ok']
        assert len(status) == 1
        assert card not in p.cards
    assert round_.state == models.Round.State.BETWEEN_TRICKS, "Test case precondition not met"
    p = round_.current_player
    card = p.playable_cards[0]
    response = client.post(
        '/player/play/card/',
        data={'secret_id': p.secret_id, 'card': int(card)})
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert status['ok']
    assert len(status) == 1
    assert card not in p.cards


def test_play_card__out_of_order(game_with_started_round, client):
    round_ = game_with_started_round.round
    assert round_.state == models.Round.State.PLAYING
    tested = 0
    for p in game_with_started_round.confirmed_players:
        if p is round_.current_player:
            continue
        tested += 1
        response = client.post(
            '/player/play/card/',
            data={'secret_id': p.secret_id, 'card': int(p.cards[0])})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert not status['ok']
        assert round_.current_player.name in status['error']
        assert p.name in status['error']
    assert tested > 0


def test_finish_round__post_only(first_player, client):
    response = client.get('/player/finish/round/', follow_redirects=True)
    assert response.status_code == 405
    first_player.confirm('')
    response = client.get('/player/finish/round/', follow_redirects=True)
    assert response.status_code == 405


def test_finish_round__player_must_be_confirmed(started_game, client):
    unconfirmed_player = next(
        p for p in started_game.players if not p.is_confirmed)
    response = client.post('/player/finish/round/',
                           data={'secret_id': unconfirmed_player.secret_id},
                           follow_redirects=True)
    assert response.status_code == 200
    assert response.is_json
    j = response.get_json()
    assert not j['ok']
    assert isinstance(j['error'], str)


def test_finish_round__game_or_round_bad_state__404(confirmed_first_player, game, client):
    for p in game.players:
        if not p.is_confirmed:
            p.confirm('')
        response = client.post('/player/finish/round/',
                               data={'secret_id': p.secret_id},
                               follow_redirects=True)
        assert response.status_code == 200
        assert response.is_json
        j = response.get_json()
        assert not j['ok']
        assert isinstance(j['error'], str)
    game.start_game()
    players = game.confirmed_players
    round_ = game.round
    round_._state = models.Round.State.DONE
    response = client.post('/player/finish/round/',
                           data={'secret_id': p.secret_id},
                           follow_redirects=True)
    assert response.status_code == 200
    assert response.is_json
    j = response.get_json()
    assert not j['ok']
    assert isinstance(j['error'], str)


def test_finish_round__bad_secret__403(confirmed_first_player, game_with_started_round, client):
    response = client.post(
        '/player/finish/round/',
        data={'secret_id': 'bad_secret'},
        follow_redirects=True)
    assert response.status_code == 403
    response = client.post(
        '/player/finish/round/', data={}, follow_redirects=True)
    assert response.status_code == 403


def test_finish_round__last_round(game_with_started_round, client):
    game = game_with_started_round
    round_ = game.round
    assert round_.state == models.Round.State.PLAYING, "Precondition for test not met"
    # Speed up test by pretending it's the last Round
    game._current_card_count = 1
    for p in game.confirmed_players:
        # Speed up test by removing all player's cards but 1
        p._cards = [p.cards[0]]
    for p in game.confirmed_players:
        p.play_card(p.cards[0])
    assert round_.state == models.Round.State.DONE, "Precondition for test not met"
    assert game.state == models.Game.State.PAUSED_BETWEEN_ROUNDS, "Precondition for test not met"
    # any player may go to next trick, so there are going to be races.
    # Just ignore the /player/finish/round/ POST if we are playing
    # already.
    for p in game_with_started_round.confirmed_players:
        response = client.post(
            '/player/finish/round/', data={'secret_id': p.secret_id})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert status['ok']
        assert len(status) == 1
        assert game.state == models.Game.State.DONE


def test_finish_round__happy_path(game_with_started_round, client):
    game = game_with_started_round
    round_ = game.round
    assert round_.state == models.Round.State.PLAYING, "Precondition for test not met"
    for p in game.confirmed_players:
        # Speed up test by removing all player's cards but 1
        p._cards = [p.cards[0]]
    for p in game.confirmed_players:
        p.play_card(p.cards[0])
    assert round_.state == models.Round.State.DONE, "Precondition for test not met"
    # any player may go to next trick, so there are going to be races.
    # Just ignore the /player/finish/round/ POST if we are playing
    # already.
    for p in game_with_started_round.confirmed_players:
        response = client.post(
            '/player/finish/round/', data={'secret_id': p.secret_id})
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert status['ok']
        assert len(status) == 1
        assert game.round is not round_
        assert game.round.state == models.Round.State.BIDDING


def test_api_status__wrong_secret__403(confirmed_first_player, client):
    response = client.get(
        f'/player/wrong_secret/api/status/', follow_redirects=True)
    assert response.status_code == 403


def test_api_status__unconfirmed__404(first_player, client):
    response = client.get(
        f'/player/{first_player.secret_id}/api/status/', follow_redirects=True)
    assert response.status_code == 404


def test_api_status__confirmed_no_other_players_yet__returns_correct_json(confirmed_first_player, game, client):
    response = client.get(
        f'/player/{confirmed_first_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['players'] == [
        {'id': confirmed_first_player.id,
         'h': f'<li id="{confirmed_first_player.id}" class="self_player">{escape(confirmed_first_player.name)}</li>'}]


def test_api_status__confirmed_one_other_player__returns_correct_json(confirmed_first_player, game, client):
    game.players[2].confirm('<confirmed&tested>')
    response = client.get(
        f'/player/{confirmed_first_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['id'] == confirmed_first_player.id
    assert status['players'] == [
        {'id': confirmed_first_player.id,
         'h': f'<li id="{confirmed_first_player.id}" class="self_player">{escape(confirmed_first_player.name)}</li>'},
        {'id': game.players[2].id,
         'h': f'<li id="{game.players[2].id}" class="other_player">{escape(game.players[2].name)}</li>'}]
    game.players[1].confirm('api status test')
    response = client.get(
        f'/player/{confirmed_first_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['id'] == confirmed_first_player.id
    assert status['players'] == [
        {'id': confirmed_first_player.id,
         'h': f'<li id="{confirmed_first_player.id}" class="self_player">{escape(confirmed_first_player.name)}</li>'},
        {'id': game.players[1].id,
         'h': f'<li id="{game.players[1].id}" class="other_player">api status test</li>'},
        {'id': game.players[2].id,
         'h': f'<li id="{game.players[2].id}" class="other_player">{escape(game.players[2].name)}</li>'}]


def test_api_status__several_confirmed_players__lists_players_in_order(confirmed_last_player, game, client):
    game.players[2].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[2].id,
         'h': f'<li id="{game.players[2].id}" class="other_player">{escape(game.players[2].name)}</li>'},
        {'id': confirmed_last_player.id,
         'h': f'<li id="{confirmed_last_player.id}" class="self_player">{escape(confirmed_last_player.name)}</li>'}]
    game.players[0].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[0].id,
         'h': f'<li id="{game.players[0].id}" class="other_player">{escape(game.players[0].name)}</li>'},
        {'id': game.players[2].id,
         'h': f'<li id="{game.players[2].id}" class="other_player">{escape(game.players[2].name)}</li>'},
        {'id': confirmed_last_player.id,
         'h': f'<li id="{confirmed_last_player.id}" class="self_player">{escape(confirmed_last_player.name)}</li>'}]
    game.players[-2].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 4
    assert status['summary'] == game.status_summary()
    assert 'Waiting' in status['game_state']
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[0].id,
         'h': f'<li id="{game.players[0].id}" class="other_player">{escape(game.players[0].name)}</li>'},
        {'id': game.players[2].id,
         'h': f'<li id="{game.players[2].id}" class="other_player">{escape(game.players[2].name)}</li>'},
        {'id': game.players[-2].id,
         'h': f'<li id="{game.players[-2].id}" class="other_player">{escape(game.players[-2].name)}</li>'},
        {'id': confirmed_last_player.id,
         'h': f'<li id="{confirmed_last_player.id}" class="self_player">{escape(confirmed_last_player.name)}</li>'}]


def test_api_status__game_started__lists_players_in_order(started_game, client):
    player = started_game.confirmed_players[0]
    response = client.get(f'/player/{player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 7
    assert status['summary'] == started_game.status_summary()
    assert 'Bidding' in status['game_state']
    assert f'with {started_game.current_card_count} cards' in status['game_state']
    assert f' 0 tricks bid so far' in status['game_state']
    assert f'cards/card{started_game.round.trump:02d}' in status['trump']
    assert status['round'] == {
        'state': models.Round.State.BIDDING,
        'current_player': started_game.confirmed_players[0].id}
    # check player's hand display:
    cards_positions = [(c, p)
                       for (c, p) in (
        (c, status['cards'].find(f'cards/card{c:02d}.png'))
        for c in player.cards)
        if p > -1]
    # ... all cards are there ...
    assert len(cards_positions) == len(player.cards)
    # ... and displayed in sorted order (from highest to lowest)
    cards_positions.sort(key=lambda cp: cp[1])
    assert all(c1 > c2 for ((c1, _), (c2, _)) in zip(
        cards_positions[:-1], cards_positions[1:]))
    assert status['id'] == player.id
    for (idx, player_info) in enumerate(status['players']):
        assert len(player_info) == 2
        assert player_info['id'] == started_game.confirmed_players[idx].id
        assert escape(
            started_game.confirmed_players[idx].name) in player_info['h']
        assert f'<li id="{escape(started_game.confirmed_players[idx].id)}"' in player_info['h']
        assert str(started_game.confirmed_players[idx].card_count
                   ) in player_info['h']
        assert 'not bid' in player_info['h']
        if idx == 0:
            assert 'current_player' in player_info['h']
            assert 'self_player' in player_info['h']
            assert 'other_player' not in player_info['h']
        else:
            assert 'current_player' not in player_info['h']
            assert 'other_player' in player_info['h']
            assert 'self_player' not in player_info['h']


def test_api_status__save_bandwidth(started_game, client):
    player = started_game.confirmed_players[0]
    full_response = client.get(f'/player/{player.secret_id}/api/status/')
    assert full_response.status_code == 200
    assert full_response.is_json
    full_status = full_response.get_json()
    small_response = client.get(
        f'/player/{player.secret_id}/api/status/{full_status["summary"]}/')
    assert small_response.status_code == 200
    assert small_response.is_json
    small_status = small_response.get_json()
    assert len(small_status) == 1
    assert small_status['summary'] == full_status['summary']
    player.place_bid(2)
    next_response = client.get(
        f'/player/{player.secret_id}/api/status/{full_status["summary"]}/')
    assert next_response.status_code == 200
    assert next_response.is_json
    next_status = next_response.get_json()
    assert len(next_status) > 1
    assert next_status['summary'] != small_status['summary']
    assert next_status['summary'] == started_game.status_summary()


def test_api_status__bidding_process(started_game, client):
    players = started_game.confirmed_players
    for (idx, p) in enumerate(players):
        p.place_bid(1)
        response = client.get(f'/player/{p.secret_id}/api/status/')
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        if idx < len(players) - 1:
            # still at least one more player has to bid -> we are
            # still in Round.State.BIDDING
            assert 'Bidding' in status['game_state']
            assert len(status) == 7
            assert f' {idx + 1} tricks bid so far' in status['game_state']
        else:
            # now in Round.State.PLAYING state.  More detailed
            # validations should be in another test.
            assert 'Playing' in status['game_state']
        assert status['summary'] == started_game.status_summary()
        assert f'with {started_game.current_card_count} cards' in status['game_state']
        assert f'cards/card{started_game.round.trump:02d}' in status['trump']
        if idx < len(players) - 1:
            assert status['round'] == {
                'state': int(models.Round.State.BIDDING),
                'current_player': started_game.confirmed_players[idx + 1].id}
        else:
            assert status['round'] == {
                'state': int(models.Round.State.PLAYING),
                'current_player': started_game.confirmed_players[0].id}
        assert all(
            f'cards/card{c:02d}.png' in status['cards'] for c in p.cards)
        assert status['id'] == p.id
        for (idx2, player_info) in enumerate(status['players']):
            assert len(player_info) == 2
            assert player_info['id'] == started_game.confirmed_players[idx2].id
            assert escape(
                started_game.confirmed_players[idx2].name) in player_info['h']
            assert f'<li id="{escape(started_game.confirmed_players[idx2].id)}"' in player_info['h']
            assert str(started_game.confirmed_players[idx2].card_count
                       ) in player_info['h']
            if idx2 <= idx:
                assert f'bid for {started_game.confirmed_players[idx2].bid} tricks' in player_info['h']
            else:
                assert 'not bid yet' in player_info['h']


def test_api_status__playing(game_with_started_round, client):
    game = game_with_started_round
    round_ = game.round
    players = game.confirmed_players
    all_cards_at_start = [c for p in players for c in p.cards]
    # Verify preconditions
    assert game.state == models.Game.State.PLAYING and round_.state == models.Round.State.PLAYING
    # Verify response for all players while all players play the first
    # trick of the first round.  One property must hold: all cards of
    # the players + all cards in the current trick must always be the
    # same set.
    for (idx, card_placer) in enumerate(players):
        observed_table = []  # overwritten later
        all_cards_in_hands = []
        for p in players:
            response = client.get(f'/player/{p.secret_id}/api/status/')
            assert response.status_code == 200
            assert response.is_json
            status = response.get_json()
            assert 'summary' in status
            assert 'playing' in status['game_state'].lower()
            assert status['id'] == p.id
            for (idx2, player_info) in enumerate(status['players']):
                assert len(player_info) == 2
                assert player_info['id'] == players[idx2].id
                assert escape(players[idx2].name) in player_info['h']
                assert f'<li id="{escape(players[idx2].id)}"' in player_info['h']
                assert str(players[idx2].card_count) in player_info['h']
            all_cards_in_hands.append(status['cards'])
            if p is card_placer:
                assert status['playable_cards'] != []
                assert all(card_id in status['cards']
                           for card_id in status['playable_cards'])
            else:
                assert status['playable_cards'] == []
            assert all(
                f'cards/card{c:02d}.png' in status['cards'] for c in p.cards)
            assert f'cards/card{game.round.trump:02d}' in status['trump']
            assert status['round'] == {'state': int(models.Round.State.PLAYING),
                                       'current_player': players[idx].id}
            if p is players[0]:
                observed_table = status['table']
            else:
                # all players see the same table
                assert status['table'] == observed_table
            all_cards_in_hands += status['cards']
            # no we know all keys we need are there, check there is nothing extra:
            assert len(status) == 9
        # check that no card was lost:
        all_cards_html = observed_table + ''.join(all_cards_in_hands)
        assert all(
            f'cards/card{c:02d}.png' in all_cards_html for c in all_cards_at_start)
        card = 0
        while True:
            try:
                card_placer.play_card(card_placer.cards[card])
            except models.ModelError:
                card += 1
            else:
                break
    # now we should be in BETWEEN_TRICKS state, see test_api_status__between_tricks


def test_api_status__between_tricks(game_with_started_round, client):
    def find_by_id(status, id_):
        return next(p for p in status['players'] if p['id'] == id_)
    game = game_with_started_round
    round_ = game.round
    players = game.confirmed_players
    for (idx, card_placer) in enumerate(players):
        if idx == len(players) - 1:
            # record last player status to observe differences between
            # Round.State.PLAYING & Round.State.BETWEEN_TRICKS
            response = client.get(
                f'/player/{card_placer.secret_id}/api/status/')
            last_status = response.get_json()
        # play any card
        card_idx = 0
        while True:
            card = card_placer.cards[card_idx]
            try:
                card_placer.play_card(card)
            except models.ModelError:
                card_idx += 1
            else:
                break
    response = client.get(f'/player/{players[-1].secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == len(last_status)
    assert len(status['round']) == len(last_status['round'])
    assert status['round']['state'] == int(models.Round.State.BETWEEN_TRICKS)
    trick_winner_id = status['round']['current_player']
    trick_winner = game.player_by_id(trick_winner_id)
    assert len(status['cards']) < len(last_status['cards'])
    assert status['trump'] == last_status['trump']
    assert status['game_state'].startswith(last_status['game_state'])
    assert status['game_state'] != last_status['game_state']
    assert trick_winner.name in status['game_state']
    assert status['id'] == last_status['id']
    assert len(status['players']) == len(last_status['players'])
    if trick_winner_id == players[-1].id:
        # trick winner is also last player with changed number of cards -> -1
        assert sum(old == new
                   for old, new in zip(last_status['players'], status['players'])
                   ) == len(status['players']) - 1
        assert len(status['playable_cards']) == len(
            status['cards'].split('<img ')) - 1
    else:
        # assume that the difference is due to the trick count being increased
        assert find_by_id(status, trick_winner_id) != find_by_id(
            last_status, trick_winner_id)
        assert sum(old == new
                   for old, new in zip(last_status['players'], status['players'])
                   ) == len(status['players']) - 2  # trick winner + last player with changed number of cards
        assert status['playable_cards'] == []
    assert status['summary'] != last_status['summary']
    # the table contains as many cards as players ...
    assert len(status['table'].split('<img ')) - 1 == len(status['players'])
    # ... with all player's cards ...
    assert status['table'].startswith(last_status['table'])
    # ... even last player's:
    assert f'card{card:02}.png"' in status['table'].split('<img ')[-1]
    if trick_winner_id is not players[-1]:
        # first player may play anything, already tested if
        # trick_winner is current_player
        response = client.get(f'/player/{trick_winner.secret_id}/api/status/')
        assert response.status_code == 200
        assert response.is_json
        status = response.get_json()
        assert len(status['playable_cards']) == len(
            status['cards'].split('<img ')) - 1


def test_api_status__between_rounds(started_game, client):
    def find_by_id(status, id_):
        return next(p for p in status['players'] if p['id'] == id_)
    game = started_game
    round_ = game.round
    players = game.confirmed_players
    # speed up test by moving to last round and restricting the number of cards
    game._current_card_count = 1
    for p in players:
        assert p.is_confirmed, "Precondition for test not met"
        p._cards = [p.cards[0]]
        p.place_bid(0)
    assert round_.state == models.Round.State.PLAYING, "Precondition for test not met"
    assert game.state == models.Game.State.PLAYING, "Precondition for test not met"
    for idx, p in enumerate(players):
        if idx == len(players) - 1:
            # Record last status to compare before & after
            response = client.get(f'/player/{p.secret_id}/api/status/')
            assert response.status_code == 200, "Precondition for test not met"
            assert response.is_json, "Precondition for test not met"
            last_status = response.get_json()
        p.play_card(p.playable_cards[0])
    assert round_.state == models.Round.State.DONE, "Precondition for test not met"
    assert game.state == models.Game.State.PAUSED_BETWEEN_ROUNDS, "Precondition for test not met"
    response = client.get(f'/player/{p.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert status['playable_cards'] == []
    assert status['cards'] == ''
    assert status['game_state'].startswith(last_status['game_state'])
    assert status['game_state'] != last_status['game_state']
    assert all(fragment in status['game_state']
               for fragment in ('<form ', players[-1].secret_id))
    assert status['id'] == last_status['id']
    assert len(status['players']) == len(last_status['players'])
    assert status['round']['state'] == int(models.Round.State.DONE)
    assert status['summary'] != last_status['summary']
    assert len(status['table'].split('<img ')
               ) == len(last_status['table'].split('<img ')) + 1
    assert status['trump'] == last_status['trump']
    assert len(status) == len(last_status)
    assert not any('current_player' in p['h'] for p in status['players'])
    trick_winner_id = status['round']['current_player']
    trick_winner = game.player_by_id(trick_winner_id)
    if trick_winner_id == status['id']:
        # trick winner is also last player with changed number of cards -> -1
        assert sum(old == new
                   for old, new in zip(last_status['players'], status['players'])
                   ) == len(status['players']) - 1
        assert len(status['playable_cards']) == len(
            status['cards'].split('<img ')) - 1
    else:
        # assume that the difference is due to the trick count being increased
        assert find_by_id(status, trick_winner_id) != find_by_id(
            last_status, trick_winner_id)
        assert sum(old == new
                   for old, new in zip(last_status['players'], status['players'])
                   ) == len(status['players']) - 2  # trick winner + last player with changed number of cards
        assert status['playable_cards'] == []


def test_organizer_url_for_unconfirmed_player(rikiki_app, first_player):
    with rikiki_app.test_request_context():
        assert organizer_url_for_player(first_player
                                        ) == f'/player/confirm/{first_player.secret_id}/'


def test_organizer_url_for_confirmed_player(rikiki_app, confirmed_first_player):
    with rikiki_app.test_request_context():
        assert organizer_url_for_player(confirmed_first_player
                                        ) == f'/player/{confirmed_first_player.secret_id}/'
