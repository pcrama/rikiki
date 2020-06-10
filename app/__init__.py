"""Web application to play rikiki over the web."""
import datetime
import os
from typing import List, Optional


import flask
from flask_babel import Babel  # type: ignore

from instance.config import app_config

from .models import Game, Player


def create_app(config_name):
    """Create new application instance."""
    class RikikiApp(flask.Flask):
        def __init__(self, *args, **kwarg):
            super().__init__(*args, **kwarg)
            self._game: Optional[Game] = None
            self.config['ORGANIZER_SECRET'] = "".join(
                f"{x:02X}" for x in os.urandom(16))

        @property
        def organizer_secret(self) -> str:
            return self.config['ORGANIZER_SECRET']

        @property
        def game(self) -> Game:
            if self._game is None:
                raise RuntimeError("Game not initialized.")
            return self._game

        def create_game(self, players: List[Player]) -> Game:
            self._game = Game(players)
            return self.game

    app = RikikiApp(__name__, instance_relative_config=True)
    app.config.from_object(
        app_config[config_name
                   if isinstance(config_name, str)
                   else os.environ.get("FLASK_ENV", "development")])
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(403, access_denied)
    from . import organizer
    from . import player
    app.register_blueprint(organizer.bp)
    app.register_blueprint(player.bp)
    log_organizer_secret_to_console(app)

    @app.before_request
    def before_request():
        flask.session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(minutes=120)
        flask.session.modified = True

    # Setup i18n
    babel = Babel(app)
    @babel.localeselector
    def get_locale():
        return flask.request.accept_languages.best_match(
            list(app.config['SUPPORTED_LANGUAGES'].keys()))

    @babel.timezoneselector
    def get_timezone():
        return app.config['BABEL_DEFAULT_TIMEZONE']
    return app


def log_organizer_secret_to_console(app):
    """Print the organizer secret link to the console."""
    if not app.testing:
        try:
            url = flask.url_for('organizer.setup_game',
                                organizer_secret=app.organizer_secret,
                                _method='GET')
            print(f'Organizer URL: {url}')
        except Exception as e:
            print(f'Ignore {e}.  organizer_secret={app.organizer_secret}')


def access_denied(_):
    """Render the access denied page."""
    log_organizer_secret_to_console(flask.current_app)
    return flask.render_template('403.html'), 403


def page_not_found(_):
    """Render the page not found page."""
    log_organizer_secret_to_console(flask.current_app)
    return flask.render_template('404.html'), 404


USER_COOKIE = 'rikiki_session_id'
"""Name of the key where user secret is stored in session cookie."""
