"""Helpers for request tests."""
# -*- coding: utf-8 -*-

import pytest  # type: ignore

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
            p.confirm('')
    game.start_game()
    return game


def rendered_template(response, t):
    """Return True if a template was rendered."""
    marker = {
        'setup_game': b'!!setup_game!-810856715183258229!!',
        'wait_for_users': b'!!wait_for_users!-1517857306451128469!!',
        'organizer.dashboard': b'!!organizer.dashboard!-1306330636811940615!!',
        'player.confirm': b'!!player.confirm!1473724732052034803!!',
        'player.player': b'!!player.player!1598872951605016181!!',
        'player.too-late': b'!!player.too-late!-1938575116592361607!!',
    }[t]
    return marker in response.data
