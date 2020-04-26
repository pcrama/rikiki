"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request)

from . import models

bp = Blueprint('player', __name__, url_prefix='/player')


def with_valid_game(f):
    """Decorate controller to check that a game has already been created."""
    @functools.wraps(f)
    def work(*args, **kwargs):
        try:
            current_app.game
        except RuntimeError:
            abort(403)
        else:
            return f(*args, **kwargs)
    return work


@bp.route('/confirm/', methods=('GET', 'POST',))
@bp.route('/confirm/<secret_id>/')
@with_valid_game
def confirm(secret_id=''):
    """Render player confirmation page and handle confirmation process."""
    secret_id = secret_id.strip()
    try:
        player = next(p for p in current_app.game.players
                      if p.secret_id == secret_id)
    except StopIteration:
        abort(403)
    return render_template('player/confirm.html',
                           unconfirmed_name=player.name,
                           secret_id=secret_id), 200


@bp.route('/', methods=('GET', 'POST',))
@bp.route('/<secret_id>/')
def player(secret_id=''):
    """Control Player model for the players."""
    abort(404)
