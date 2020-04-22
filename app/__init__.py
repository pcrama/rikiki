"""Web application to play rikiki over the web."""
import os
from typing import Optional


import flask
from instance.config import app_config

from .models import Game


ORGANIZER_SECRET: str = "".join(f"{x:02X}" for x in os.urandom(16))

GAME: Optional[Game] = None

APP: Optional[flask.Flask] = None


def create_app(config_name):
    """Create new application instance."""
    global APP
    APP = flask.Flask(__name__, instance_relative_config=True)
    APP.config.from_object(
        app_config[config_name
                   if isinstance(config_name, str)
                   else os.environ.get("FLASK_ENV", "development")])
    APP.register_error_handler(404, page_not_found)
    APP.register_error_handler(403, access_denied)
    from . import controllers
    APP.add_url_rule('/organizer/',
                     view_func=controllers.organizer,
                     methods=('GET', 'POST',))
    APP.add_url_rule('/organizer/<organizer_secret>/',
                     view_func=controllers.organizer)
    with APP.test_request_context():
        log_organizer_secret_to_console()
    return APP


def log_organizer_secret_to_console():
    """Print the organizer secret link to the console."""
    if not APP.testing:
        print(
            "Organizer URL: "
            f"{flask.url_for('organizer', organizer_secret=ORGANIZER_SECRET)}")


def access_denied(_):
    """Render the access denied page."""
    log_organizer_secret_to_console()
    return flask.render_template('403.html'), 403


def page_not_found(_):
    """Render the page not found page."""
    log_organizer_secret_to_console()
    return flask.render_template('404.html'), 404
