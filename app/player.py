"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, json,
                   redirect, render_template, request, url_for)

from . import models

bp = Blueprint('player', __name__, url_prefix='/player')


def with_valid_game(f):
    """Decorate controller to check that a game has already been created."""
    @functools.wraps(f)
    def work(*args, **kwargs):
        try:
            game = current_app.game
        except RuntimeError:
            abort(403)
        else:
            return f(*args, **kwargs, game=game)
    return work


def get_player(current_app, request, secret_id):
    """Return Player matching the secret ID.

    NB: if request.method == 'POST', secret_id is disregarded and
    taken from request.form.
    """
    if request.method == 'POST':
        secret_id = request.form.get('secret_id', '')
    try:
        return current_app.game.player_by_secret_id(secret_id)
    except StopIteration:
        abort(403)


@bp.route('/confirm/', methods=('GET', 'POST',))
@bp.route('/confirm/<secret_id>/')
@with_valid_game
def confirm(secret_id='', game=None):
    """Render player confirmation page and handle confirmation process."""
    player = get_player(current_app, request, secret_id)
    if player.is_confirmed:
        return redirect(url_for('player.player',
                                secret_id=player.secret_id,
                                _method='GET'))
    if game.state != game.State.CONFIRMING:
        return render_template('player/too-late.html',
                               player_name=player.name)
    if request.method == 'POST':
        player.confirm(request.form.get('player_name', ''))
        return redirect(url_for('player.player',
                                secret_id=player.secret_id,
                                _method='GET'))
    else:  # request.method == 'GET'
        return render_template('player/confirm.html',
                               unconfirmed_name=player.name,
                               secret_id=secret_id)


@bp.route('/', methods=('GET', 'POST',))
@bp.route('/<secret_id>/')
@with_valid_game
def player(secret_id='', game=None):
    """Control Player model for the players."""
    player = get_player(current_app, request, secret_id)
    if not player.is_confirmed:
        return redirect(url_for('player.confirm',
                                secret_id=player.secret_id,
                                _method='GET'))
    return render_template('player/player.html', game=game, player=player)


def other_player_status(p: models.Player):
    """Gather information about other Players."""
    return {'id': p.id,
            'name': p.name,
            'tricks': p.tricks,
            'cards': p.card_count,
            'bid': p.bid}


@bp.route('/<secret_id>/api/status')
@with_valid_game
def api_status(secret_id='', game=None):
    """Return JSON formatted status for Player."""
    player = get_player(current_app, request, secret_id)
    result = {
        'game_state': game.state,
        'cards': player.cards,
        'other_players': [other_player_status(p)
                          for p
                          in (game.players
                              if game.state == game.State.CONFIRMING
                              else game.confirmed_players)
                          if p.is_confirmed and p is not player],
        'bid': player.bid,
        'tricks': player.tricks,
    }
    try:
        result['current_player'] = game.round.current_player.id
    except ModelError:
        pass
    return json.dumps(result).encode('utf-8')
