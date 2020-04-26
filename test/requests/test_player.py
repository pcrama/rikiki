import random
import app  # type: ignore

import pytest  # type: ignore

from app.organizer import parse_playerlist  # type: ignore

from helper import client, first_player, game, rikiki_app, rendered_template


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
    assert rendered_template(response, 'player.confirm')
    response = client.get(
        f'/player/confirm/{first_player.secret_id}/')
    assert response.status_code == 200


def test_player_confirm_game_exists__post_confirmation_without_valid_secret(first_player, client):
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
