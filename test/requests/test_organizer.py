import pytest  # type: ignore
from flask import current_app, url_for

import app

from app.organizer import parse_playerlist
from app.player import organizer_url_for_player

from .helper import (
    FLASH_ERROR,
    client,
    game,
    game_with_started_round,
    minimal_HTML_escaping,
    organizer_secret,
    rendered_template,
    rikiki_app,
    started_game,
)


def test_organizer_get_with_wrong_secret(client):
    response = client.get('/organizer/wrong_secret/setup/game',
                          follow_redirects=True)
    assert response.status_code == 403


def test_organizer_get_without_secret(client):
    response = client.get('/organizer/setup/game/')
    assert response.status_code == 405
    response = client.get('/organizer/setup/game', follow_redirects=True)
    assert response.status_code == 405


def test_organizer_get_with_secret(organizer_secret, client):
    response = client.get(
        f'/organizer/{organizer_secret}/setup/game', follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'setup_game')
    response = client.get(
        f'/organizer/{organizer_secret}/setup/game/')
    assert response.status_code == 200


def test_organizer_post_with_secret_without_data(organizer_secret, client):
    response = client.post(
        f'/organizer/setup/game/', data={'organizer_secret': organizer_secret})
    assert response.status_code == 200
    assert rendered_template(response, 'setup_game')
    assert b"No player list provided" in response.data


def test_organizer_post_with_blank_playerlist(organizer_secret, client):
    response = client.post(
        f'/organizer/setup/game/', data={'organizer_secret': organizer_secret,
                                         'playerlist': '  \n   \r\t'})
    assert response.status_code == 200
    assert rendered_template(response, 'setup_game')
    assert b"No player list provided" in response.data


def test_organizer_post_with_overlong_playerlist(organizer_secret, client):
    response = client.post(
        f'/organizer/setup/game/', data={'organizer_secret': organizer_secret,
                                         'playerlist': 'a' * 50000})
    assert response.status_code == 200
    assert rendered_template(response, 'setup_game')
    assert b"Player list too large" in response.data


def test_organizer_post_with_too_many_players(organizer_secret, client):
    response = client.post(
        '/organizer/setup/game/', data={'organizer_secret': organizer_secret,
                                        'playerlist': '\n'.join(f'P{i}' for i in range(27))})
    assert response.status_code == 200
    assert rendered_template(response, 'setup_game')
    assert b"Too many players" in response.data


def test_organizer_post_with_players(organizer_secret, client, rikiki_app):
    PLAYER_NAMES = ['riri', 'fifi', 'lulu']
    response = client.post(
        '/organizer/setup/game/',
        data={'organizer_secret': organizer_secret,
              'playerlist': '\n'.join(PLAYER_NAMES)},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert [p.name for p in rikiki_app.game.players] == PLAYER_NAMES


def test_organizer_post_with_players_twice_overwrites_first_game(organizer_secret, client, rikiki_app):
    PLAYER_NAMES_1 = ['riri', 'fifi', 'lulu']
    response = client.post(
        '/organizer/setup/game/',
        data={'organizer_secret': organizer_secret,
              'playerlist': '\n'.join(PLAYER_NAMES_1)},
        follow_redirects=True)
    try:
        game_1 = rikiki_app.game
        assert [p.name for p in game_1.players] == PLAYER_NAMES_1
    except Exception as e:
        assert e is None, "Test precondition not met"
    PLAYER_NAMES_2 = ['toto', 'momo', 'lili']
    response = client.post(
        '/organizer/setup/game/',
        data={'organizer_secret': organizer_secret,
              'playerlist': ', '.join(PLAYER_NAMES_2)},
        follow_redirects=True)
    assert rikiki_app.game is not game_1
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert [p.name for p in rikiki_app.game.players] == PLAYER_NAMES_2


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


def test_wait_for_users__game_not_initialized_yet__redirects_to_setup_game(organizer_secret, client):
    response = client.get(
        f'/organizer/{organizer_secret}/wait_for_users/',
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'setup_game')


def test_wait_for_users_with_wrong_organizer_secret(client):
    response = client.get('/organizer/wrong_secret/wait_for_users',
                          follow_redirects=True)
    assert response.status_code == 403


def test_wait_for_users_with_correct_organizer_secret(organizer_secret, client, game):
    response = client.get(
        f'/organizer/{organizer_secret}/wait_for_users/',
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert rendered_template(response, 'wait_for_users')
    assert bytes(url_for('organizer.api_game_status',
                         organizer_secret=organizer_secret),
                 'utf-8') in response.data
    for p in game.players:
        assert p.name.encode('utf-8') in response.data
        assert p.secret_id.encode('ascii') in response.data
        assert p.id.encode('ascii') in response.data


def test_api_game_status__no_game_created__get_returns_404(organizer_secret, client):
    response = client.get(
        f'/organizer/{organizer_secret}/api/game_status/')
    assert response.status_code == 404


def test_api_game_status__game_created_wrong_secret__get_returns_404(client, game):
    response = client.get('/organizer/wrong_secret/api/game_status/')
    assert response.status_code == 403


def test_api_game_status__game_created__get_returns_json(organizer_secret, client, game):
    response = client.get(
        f'/organizer/{organizer_secret}/api/game_status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    status_state = status['game_state']
    assert status_state == app.models.Game.State.CONFIRMING
    status_players = status['players']
    assert len(status_players) == 0  # no players confirmed yet
    with pytest.raises(KeyError):
        status['currentCardCount']
        status['round']

    # confirm some players:
    NEW_NAME = "new name"
    CP1, CP2 = 0, -1
    game.players[CP1].confirm(NEW_NAME)
    game.players[CP2].confirm("")
    response = client.get(
        f'/organizer/{organizer_secret}/api/game_status/')
    assert response.status_code == 200
    status = response.get_json()
    status_state = status['game_state']
    assert status_state == app.models.Game.State.CONFIRMING
    status_players = status['players']
    assert len(status_players) == 2
    assert game.players[CP1].id in status_players
    assert game.players[CP2].id in status_players
    # inform organizer about updated player links in case they lose theirs
    assert status_players[game.players[CP1].id] == {
        'name': NEW_NAME, 'url': organizer_url_for_player(game.players[CP1])}
    assert status_players[game.players[CP2].id] == {
        'name': game.players[CP2].name, 'url': organizer_url_for_player(game.players[CP2])}
    with pytest.raises(KeyError):
        status['currentCardCount']
        status['round']


def test_api_game_status__game_started__get_returns_json(organizer_secret, client, started_game):
    response = client.get(
        f'/organizer/{organizer_secret}/api/game_status/')
    assert response.status_code == 200
    assert response.is_json
    status = response.get_json()
    status_state = status['game_state']
    assert status_state == app.models.Game.State.PLAYING
    status_players = status['players']
    assert len(status_players) == len(started_game.confirmed_players)
    for p in started_game.confirmed_players:
        assert p.id in status_players
        assert status_players[p.id]['bid'] == started_game.player_by_id(
            p.id).bid
        assert status_players[p.id]['cards'] == started_game.player_by_id(
            p.id).card_count
    assert status['currentCardCount'] == started_game.current_card_count
    assert status['round']['currentPlayer'] == started_game.round.current_player.id
    assert status['round']['state'] == started_game.round.state


def test_start_game__get__is_forbidden_method(client):
    response = client.get('/organizer/start_game/')
    assert response.status_code == 405


def test_start_game__with_invalid_organizer_secret(client, game):
    for p in game.players:
        p.confirm('')
    for invalid_secret in [None, 'bad_secret']:
        data = {}
        if invalid_secret is not None:
            data['organizer_secret'] = invalid_secret
        response = client.post(
            '/organizer/start_game/', data=data, follow_redirects=True)
        assert response.status_code == 403


def test_start_game__not_enough_players_confirmed__redirects_to_wait_users(organizer_secret, client, game):
    response = client.post(
        '/organizer/start_game/',
        data={'organizer_secret': organizer_secret},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'wait_for_users')


def test_start_game__ok_to_start_game__redirects_to_dashboard(organizer_secret, client, game):
    for p in game.players:
        p.confirm('')
    response = client.post(
        '/organizer/start_game/',
        data={'organizer_secret': organizer_secret},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert rendered_template(response, 'organizer.dashboard')


def test_dashboard__bad_organizer_secret__403(client):
    response = client.get('/organizer/bad_secret/dashboard/')
    assert response.status_code == 403


def test_dashboard__game_not_created__redirect_to_setup_game(organizer_secret, client):
    response = client.get(f'/organizer/{organizer_secret}/dashboard/',
                          follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'setup_game')


def test_dashboard__game_not_started__redirect_to_wait_for_users(rikiki_app, client):
    rikiki_app.create_game(
        [app.models.Player(f'P{i}', f'S{i}') for i in range(5)])
    response = client.get(f'/organizer/{rikiki_app.organizer_secret}/dashboard/',
                          follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'wait_for_users')


def test_dashboard__game_started__renders_page(organizer_secret, client, started_game):
    response = client.get(f'/organizer/{organizer_secret}/dashboard/',
                          follow_redirects=True)
    assert response.status_code == 200
    assert rendered_template(response, 'organizer.dashboard')
    assert FLASH_ERROR not in response.data
    assert bytes(url_for('organizer.api_game_status',
                         organizer_secret=organizer_secret),
                 'utf-8') in response.data


def test_restart_game__bad_organizer_secret__403(client):
    response = client.post(f'/organizer/restart/with/same/players/',
                           follow_redirects=True)
    assert response.status_code == 403
    response = client.post(f'/organizer/restart/with/same/players/',
                           data={'organizer_secret': 'bad_secret'},
                           follow_redirects=True)
    assert response.status_code == 403


def test_restart_game__get__forbidden_method(client):
    response = client.get(f'/organizer/restart/with/same/players/',
                          follow_redirects=True)
    assert response.status_code == 405


def test_restart_game__game_not_initialized_yet__redirects_to_setup_game(organizer_secret, client):
    response = client.post(f'/organizer/restart/with/same/players/',
                           data={'organizer_secret': organizer_secret},
                           follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'setup_game')


def test_restart_game__game_not_started__redirect_to_wait_for_users(rikiki_app, client):
    rikiki_app.create_game(
        [app.models.Player(f'P{i}', f'S{i}') for i in range(5)])
    response = client.post(f'/organizer/restart/with/same/players/',
                           data={'organizer_secret': rikiki_app.organizer_secret},
                           follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'wait_for_users')


def test_restart_game__game_playing__redirect_to_dashboard(rikiki_app, client, game_with_started_round):
    response = client.post(f'/organizer/restart/with/same/players/',
                           data={'organizer_secret': rikiki_app.organizer_secret},
                           follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR in response.data
    assert rendered_template(response, 'organizer.dashboard')


def test_restart_game__game_done__happy_path(rikiki_app, client, game_with_started_round):
    game = game_with_started_round
    game_players = [p for p in game.players]
    for p in game.confirmed_players:
        p._cards = []
    game._increasing = True
    game._current_card_count = game.max_cards_per_player()
    game.round_finished()
    assert game.state == game.State.PAUSED_BETWEEN_ROUNDS, "Precondition in middle of test not met"
    game.start_next_round()
    assert game.state == game.State.DONE, "Precondition in middle of test not met"
    response = client.post(f'/organizer/restart/with/same/players/',
                           data={'organizer_secret': rikiki_app.organizer_secret},
                           follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    assert rendered_template(response, 'wait_for_users')
    for p in game.players:
        assert minimal_HTML_escaping(p.name).encode('utf-8') in response.data
