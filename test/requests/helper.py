"""Helpers for request tests."""
# -*- coding: utf-8 -*-

from contextlib import contextmanager
from typing import AnyStr, Union

import pytest  # type: ignore

import flask

import app  # type: ignore

FLASH_ERROR = b"flash error"
"""CSS class of error message in rendered output

Use like 'assert FLASH_ERROR in response.data' if no error message
should be shown.
"""


@pytest.fixture  # was module scope, but I don't trust it with my app
def client(rikiki_app):
    # Heavily simplified from
    # https://flask.palletsprojects.com/en/1.1.x/testing/
    #
    # db_fd, flaskr.app.config['DATABASE'] = tempfile.mkstemp()
    # flaskr.app.config['TESTING'] = True

    with rikiki_app.test_client() as client:
        # with flaskr.app.app_context():
        #     flaskr.init_db()
        yield client

    # os.close(db_fd)
    # os.unlink(flaskr.app.config['DATABASE'])


@pytest.fixture
def first_player(game):
    return game.players[0]


CONFIRMED_1ST_NAME = 'Confirmed "in" <fixture>'


@pytest.fixture
def confirmed_first_player(first_player):
    first_player.confirm(CONFIRMED_1ST_NAME)
    return first_player


CONFIRMED_LAST_NAME = 'Fixture-confirmed & too'


@pytest.fixture
def confirmed_last_player(game):
    last_player = game.players[-1]
    last_player.confirm(CONFIRMED_LAST_NAME)
    return last_player


@pytest.fixture
def rikiki_app():
    return app.create_app('testing')


@pytest.fixture
def organizer_secret(rikiki_app):
    return rikiki_app.organizer_secret


@pytest.fixture
def game(rikiki_app):
    SPECIAL_NAME_PLAYERS = {
        3: "Günther",
        5: "Φιλιππε",
    }
    return rikiki_app.create_game(
        [app.models.Player(
            SPECIAL_NAME_PLAYERS.get(i, f"P{i}"),
            f"Secret{i}") for i in range(7)])


@pytest.fixture
def started_game(game):
    for (idx, p) in enumerate(game.players):
        if idx != 3:
            p.confirm(f'{p.name} <{idx}>')
    game.start_game()
    return game


@pytest.fixture
def game_with_started_round(started_game):
    for (idx, p) in enumerate(started_game.confirmed_players):
        p.place_bid(idx % min(3, started_game.current_card_count + 1))
    return started_game


def rendered_template(response, t):
    """Return True if a template was rendered."""
    marker = {
        'setup_game': b'!!setup_game!-810856715183258229!!',
        'wait_for_users': b'!!wait_for_users!-1517857306451128469!!',
        'organizer.dashboard': b'!!organizer.dashboard!-1306330636811940615!!',
        'player.confirm': b'!!player.confirm!1473724732052034803!!',
        'player.player': b'!!player.player!1598872951605016181!!',
        'player.too-late': b'!!player.too-late!-1938575116592361607!!',
        'player.restore_link': b'!!player.restore_link!982130456353280665!!',
    }[t]
    return marker in response.data


def minimal_HTML_escaping(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


@contextmanager
def player_session(client, player: Union[app.Player, None, str]):
    """Helper for setup_player_session."""
    # normalize parameter to a secret_id:
    if player is None:
        secret_id = None
    else:
        if isinstance(player, str):
            secret_id = player
        else:
            secret_id = player.secret_id

    with client.session_transaction() as session:
        # save current session cookie
        try:
            old_cookie = session[app.USER_COOKIE]
        except KeyError:
            has_cookie = False
        else:
            has_cookie = True

        # change session
        if secret_id is None:
            if has_cookie:
                session.pop(app.USER_COOKIE)
        else:
            session[app.USER_COOKIE] = secret_id

        # execute code in modified session
        yield session


def setup_player_session(client, player):
    """Setup session with player's secret."""
    with player_session(client, player):
        pass
