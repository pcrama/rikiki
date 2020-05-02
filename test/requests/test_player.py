import random
import app  # type: ignore

import pytest  # type: ignore

from app.organizer import parse_playerlist  # type: ignore

from .helper import FLASH_ERROR, client, first_player, game, rikiki_app, rendered_template


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


def test_player_confirm__game_started__renders_player_too_late(first_player, client, game):
    for p in game.players:
        if p is not first_player:
            p.confirm('')
    game.start_game()
    response = client.get(f'player/confirm/{first_player.secret_id}/')
    assert response.status_code == 200
    assert rendered_template(response, 'player.too-late')
    assert first_player.name.encode('utf-8') in response.data


def test_player_confirm__already_confirmed__redirects_to_player_dashboard(first_player, client):
    first_player.confirm('already confirmed')
    response = client.post(
        f'/player/confirm/',
        data={'secret_id': first_player.secret_id,
              'confirmed_name': 'yet another name'},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert first_player.name == 'already confirmed'
    assert rendered_template(response, 'player.player')
    response = client.get(
        f'/player/confirm/{first_player.secret_id}', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'player.player')
    assert FLASH_ERROR in response.data


def test_player__player__validates_secret_id(first_player, client):
    first_player.confirm('needs to be confirmed')
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
