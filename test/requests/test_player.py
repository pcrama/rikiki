import random
import app  # type: ignore

import pytest  # type: ignore

from app.organizer import parse_playerlist  # type: ignore
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
    # only one key yet: empty other_players list
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['players'] == [
        {'id': confirmed_first_player.id, 'name': confirmed_first_player.name}]


def test_api_status__confirmed_one_other_player__returns_correct_json(confirmed_first_player, game, client):
    game.players[2].confirm('')
    response = client.get(
        f'/player/{confirmed_first_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['id'] == confirmed_first_player.id
    assert status['players'] == [
        {'id': confirmed_first_player.id, 'name': confirmed_first_player.name},
        {'id': game.players[2].id, 'name': game.players[2].name}]
    game.players[1].confirm('api status test')
    response = client.get(
        f'/player/{confirmed_first_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['id'] == confirmed_first_player.id
    assert status['players'] == [
        {'id': confirmed_first_player.id, 'name': confirmed_first_player.name},
        {'id': game.players[1].id, 'name': 'api status test'},
        {'id': game.players[2].id, 'name': game.players[2].name}]


def test_api_status__several_confirmed_players__lists_players_in_order(confirmed_last_player, game, client):
    game.players[2].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[2].id, 'name': game.players[2].name},
        {'id': confirmed_last_player.id, 'name': confirmed_last_player.name}]
    game.players[0].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[0].id, 'name': game.players[0].name},
        {'id': game.players[2].id, 'name': game.players[2].name},
        {'id': confirmed_last_player.id, 'name': confirmed_last_player.name}]
    game.players[-2].confirm('')
    response = client.get(
        f'/player/{confirmed_last_player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 3
    assert status['game_state'] == game.state
    assert status['id'] == confirmed_last_player.id
    assert status['players'] == [
        {'id': game.players[0].id, 'name': game.players[0].name},
        {'id': game.players[2].id, 'name': game.players[2].name},
        {'id': game.players[-2].id, 'name': game.players[-2].name},
        {'id': confirmed_last_player.id, 'name': confirmed_last_player.name}]


def test_api_status__game_started__lists_players_in_order(started_game, client):
    player = started_game.confirmed_players[0]
    response = client.get(f'/player/{player.secret_id}/api/status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    assert len(status) == 5
    assert status['game_state'] == models.Game.State.PLAYING
    assert status['round'] == {
        'state': models.Round.State.BIDDING,
        'current_player': started_game.confirmed_players[0].id}
    assert status['cards'] == player.cards
    assert status['id'] == player.id
    for (idx, player_info) in enumerate(status['players']):
        assert len(player_info) == 5
        assert player_info['id'] == started_game.confirmed_players[idx].id
        assert player_info['name'] == started_game.confirmed_players[idx].name
        assert player_info['tricks'] == 0  # start of game!
        # everybody has the same amount of cards at the start:
        assert player_info['cards'] == len(player.cards)
        assert player_info['bid'] is None  # no bids placed yet
