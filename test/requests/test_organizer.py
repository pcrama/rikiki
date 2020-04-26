import json
import pytest  # type: ignore
from flask import current_app
import app                      # type: ignore

from app.organizer import parse_playerlist  # type: ignore

from helper import client, game, rendered_template, rikiki_app


def test_organizer_get_with_wrong_secret(client):
    response = client.get('/organizer/wrong_secret', follow_redirects=True)
    assert response.status_code == 403


def test_organizer_get_without_secret(client):
    response = client.get('/organizer/')
    assert response.status_code == 403
    response = client.get('/organizer', follow_redirects=True)
    assert response.status_code == 403


def test_organizer_get_with_secret(rikiki_app, client):
    response = client.get(
        f'/organizer/{rikiki_app.organizer_secret}', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    response = client.get(f'/organizer/{rikiki_app.organizer_secret}/')
    assert response.status_code == 200


def test_organizer_post_with_secret_without_data(rikiki_app, client):
    response = client.post(
        f'/organizer/', data={'organizer_secret': rikiki_app.organizer_secret})
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    assert b"No player list provided" in response.data


def test_organizer_post_with_blank_playerlist(rikiki_app, client):
    response = client.post(
        f'/organizer/', data={'organizer_secret': rikiki_app.organizer_secret,
                              'playerlist': '  \n   \r\t'})
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    assert b"No player list provided" in response.data


def test_organizer_post_with_overlong_playerlist(rikiki_app, client):
    response = client.post(
        f'/organizer/', data={'organizer_secret': rikiki_app.organizer_secret,
                              'playerlist': 'a' * 50000})
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    assert b"Player list too large" in response.data


def test_organizer_post_with_too_many_players(rikiki_app, client):
    response = client.post(
        '/organizer/', data={'organizer_secret': rikiki_app.organizer_secret,
                             'playerlist': '\n'.join(f'P{i}' for i in range(27))})
    assert response.status_code == 200
    assert rendered_template(response, 'organizer')
    assert b"Too many players" in response.data


def test_organizer_post_with_players(rikiki_app, client):
    PLAYER_NAMES = ['riri', 'fifi', 'lulu']
    response = client.post(
        '/organizer/',
        data={'organizer_secret': rikiki_app.organizer_secret,
              'playerlist': '\n'.join(PLAYER_NAMES)},
        follow_redirects=True)
    assert response.status_code == 200
    assert b'flash error' not in response.data
    assert [p.name for p in rikiki_app.game.players] == PLAYER_NAMES


def test_parse_playerlist_simple_examples():
    assert parse_playerlist('riri\nfifi\nlulu') == ['riri', 'fifi', 'lulu']
    assert parse_playerlist(' riri\n\r\tfifi \n\tlulu\t') == [
        'riri', 'fifi', 'lulu']
    assert parse_playerlist('\n riri, fifi, lulu, baba  et  rome\n') == [
        'riri', 'fifi', 'lulu', 'baba  et  rome']
    assert parse_playerlist('\n riri, \nfifi, lulu,\r baba  et  rome\n') == [
        'riri,', 'fifi, lulu,', 'baba  et  rome']


def test_parse_playerlist_filter_doubles():
    assert parse_playerlist('riri\nfifi\nriri \nlulu\n  fifi  \nlulu') == [
        'riri', 'fifi', 'lulu']
    assert parse_playerlist('riri\nFifi\nriRi \n\nRIRI \nLULU\n  fifi  \nlulu') == [
        'riri', 'Fifi', 'LULU']


def test_wait_for_users_with_wrong_organizer_secret(client):
    response = client.get('/organizer/wait_for_users/wrong_secret',
                          follow_redirects=True)
    assert response.status_code == 403


def test_wait_for_users_with_correct_organizer_secret(rikiki_app, client, game):
    response = client.get(
        f'/organizer/wait_for_users/{rikiki_app.organizer_secret}',
        follow_redirects=True)
    assert response.status_code == 200
    for p in game.players:
        assert p.name.encode('utf-8') in response.data
        assert p.secret_id.encode('ascii') in response.data
        assert p.id.encode('ascii') in response.data


def test_api_game_status__no_game_started__get_returns_404(rikiki_app, client):
    response = client.get(
        f'/organizer/{rikiki_app.organizer_secret}/api/game_status/')
    assert response.status_code == 404


def test_api_game_status__game_started_wrong_secret__get_returns_404(client, game):
    response = client.get('/organizer/wrong_secret/api/game_status/')
    assert response.status_code == 403


def test_api_game_status__game_started__get_returns_json(rikiki_app, client, game):
    response = client.get(
        f'/organizer/{rikiki_app.organizer_secret}/api/game_status/')
    assert response.status_code == 200
    status = json.loads(response.data)
    status_state = status['state']
    assert status_state == app.models.Game.State.CONFIRMING
    status_players = status['players']
    assert len(status_players) == 0  # no players confirmed yet
    with pytest.raises(KeyError):
        status['current_card_count']

    # confirm some players:
    NEW_NAME = "new name"
    CP1, CP2 = 0, -1
    game.players[CP1].confirm(NEW_NAME)
    game.players[CP2].confirm("")
    response = client.get(
        f'/organizer/{rikiki_app.organizer_secret}/api/game_status/')
    assert response.status_code == 200
    status = json.loads(response.data)
    status_state = status['state']
    assert status_state == app.models.Game.State.CONFIRMING
    status_players = status['players']
    assert len(status_players) == 2
    assert game.players[CP1].id in status_players
    assert game.players[CP2].id in status_players
    assert status_players[game.players[CP1].id] == NEW_NAME
    assert status_players[game.players[CP2].id] == game.players[CP2].name
    with pytest.raises(KeyError):
        status['current_card_count']
