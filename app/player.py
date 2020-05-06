"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, jsonify,
                   redirect, render_template, request, url_for)

from . import models

bp = Blueprint('player', __name__, url_prefix='/player')


def organizer_url_for_player(player, _method='GET'):
    """Get Player's URL to show in organizer dashboard.

    This URL differs for confirmed and unconfirmed players.  This
    allows the Player model to have 2 secrets:

      1. for confirming, that is destroyed as soon as the Player is
         confirmed

      2. for confirmed Player usage.  So even if 2 persons see the
         same Player confirmation URL, only the first person to
         confirm will be able to use the Player.  Otherwise, the
         second person would be able to look at the first person's
         cards.
    """
    return url_for(
        'player.player' if player.is_confirmed else 'player.confirm',
        secret_id=player.secret_id,
        _method=_method)


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
        flash(f'Your name is already confirmed as {player.name}', 'error')
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


@bp.route('/', methods=('POST',))
@bp.route('/<secret_id>/')
@with_valid_game
def player(secret_id='', game=None):
    """Control Player model for the players."""
    player = get_player(current_app, request, secret_id)
    if not player.is_confirmed:
        flash('You must confirm your participation first', 'error')
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


@bp.route('/<secret_id>/api/status/')
@with_valid_game
def api_status(secret_id='', game=None):
    """Return JSON formatted status for Player."""
    player = get_player(current_app, request, secret_id)
    if not player.is_confirmed:
        abort(404)

    if game.state == game.State.CONFIRMING:
        return jsonify({
            'game_state': game.state,
            'id': player.id,
            'players': [{'id': p.id, 'name': p.name}
                        for p in game.players if p.is_confirmed]})
    elif game.state == game.State.PLAYING:
        return jsonify({
            'game_state': game.state,
            'id': player.id,
            'cards': player.cards,
            'round': {'state': game.round.state,
                      'current_player': game.round.current_player.id},
            'players': [
                {'id': p.id, 'name': p.name, 'cards': p.card_count,
                 'bid': p.bid, 'tricks': p.tricks}
                for p in game.confirmed_players]})
    result = {
        'cards': player.cards,
        'bid': player.bid,
        'tricks': player.tricks,
        'other_players': [other_player_status(p)
                          for p
                          in (game.players
                              if game.state == game.State.CONFIRMING
                              else game.confirmed_players)
                          if p.is_confirmed and p is not player],
    }
    try:
        result['current_player'] = game.round.current_player.id
    except models.ModelError:
        pass
    return jsonify(result)
