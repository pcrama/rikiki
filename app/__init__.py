"""Web application to play rikiki over the web."""
import flask
from instance.config import app_config


def create_app(config_name: str):
    """Create new application instance."""
    app = flask.Flask(__name__, instance_relative_config=True)
    import pdb
    pdb.set_trace()
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('config.py')

    return app
