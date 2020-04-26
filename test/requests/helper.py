"""Helpers for request tests."""
# -*- coding: utf-8 -*-

import pytest  # type: ignore

import app  # type: ignore


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
def game(rikiki_app):
    SPECIAL_NAME_PLAYERS = {
        3: "Günther",
        5: "Φιλιππε",
    }
    return rikiki_app.create_game(
        [app.models.Player(
            SPECIAL_NAME_PLAYERS.get(i, f"P{i}"),
            f"Secret{i}") for i in range(7)])


def rendered_template(response, t):
    """Return True if a template was rendered."""
    marker = {
        'organizer': b'!!organizer!-810856715183258229!!',
        'game_dashboard': b'!!game_dashboard!-1517857306451128469!!',
        'player.confirm': b'!!player.confirm!1473724732052034803!!',
    }[t]
    return marker in response.data
