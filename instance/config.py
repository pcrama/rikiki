# https://scotch.io/tutorials/build-a-restful-api-with-flask-the-tdd-way
import os


class Config(object):
    """Parent configuration class."""
    DEBUG = False
    # Enable protection agains *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED = True
    # Use a secure, unique and absolutely secret key for
    # signing the data.
    CSRF_SESSION_KEY = os.urandom(16)
    CSRF_ENABLED = True
    # Secret key for signing cookies
    SECRET_KEY = os.urandom(16)


class DevelopmentConfig(Config):
    """Configurations for Development."""
    DEBUG = True
    SECRET_KEY = b"development-secret"


class TestingConfig(Config):
    """Configurations for Testing, with a separate test database."""
    # Bcrypt algorithm hashing rounds (reduced for testing purposes only!)
    BCRYPT_LOG_ROUNDS = 4
    TESTING = True
    DEBUG = True
    SECRET_KEY = b"development-secret"


class StagingConfig(Config):
    """Configurations for Staging."""
    DEBUG = True


class ProductionConfig(Config):
    """Configurations for Production."""
    DEBUG = False
    TESTING = False


app_config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
}
