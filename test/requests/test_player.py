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
        assert len(status) == 7
        assert status['summary'] == started_game.status_summary()
        assert ('Bidding' if idx < (len(players) - 1)
                else 'Playing') in status['game_state']
        assert f'with {started_game.current_card_count} cards' in status['game_state']
        assert f' {idx + 1} tricks bid so far' in status['game_state']
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


def test_organizer_url_for_unconfirmed_player(rikiki_app, first_player):
    with rikiki_app.test_request_context():
        assert organizer_url_for_player(first_player
                                        ) == f'/player/confirm/{first_player.secret_id}/'


def test_organizer_url_for_confirmed_player(rikiki_app, confirmed_first_player):
    with rikiki_app.test_request_context():
        assert organizer_url_for_player(confirmed_first_player
                                        ) == f'/player/{confirmed_first_player.secret_id}/'
