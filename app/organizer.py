"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, json,
                   redirect, render_template, request, url_for)

from . import models

bp = Blueprint('organizer', __name__, url_prefix='/organizer')


@bp.route('/setup/game/', methods=('POST',))
@bp.route('/<organizer_secret>/setup/game/')
def setup_game(organizer_secret=''):
    """Control Game model for the organizer."""
    def render(playerlist: str, error: Optional[str] = None):
        if error is not None:
            flash(error, 'error')
        return render_template('organizer/setup_game.html',
                               playerlist=playerlist,
                               organizer_secret=current_app.organizer_secret)
    if request.method == 'POST':
        organizer_secret = request.form.get('organizer_secret', '')
        if organizer_secret != current_app.organizer_secret:
            abort(403)
        playerlist = request.form.get('playerlist', '').strip()
        if playerlist == '':
            return render(playerlist, error='No player list provided')
        elif len(playerlist) > 32768:
            return render(playerlist, error='Player list too large')
        # First validations OK, now parse the list
        player_names = parse_playerlist(playerlist)
        if len(player_names) < 3:
            return render(playerlist, error='Not enough players in list')
        elif len(player_names) > 26:
            return render(playerlist, error='Too many players in list')
        current_app.create_game(
            [models.Player(p, "".join(f"{x:02X}" for x in os.urandom(16)))
             for p in player_names])
        return redirect(url_for('organizer.wait_for_users',
                                organizer_secret=organizer_secret))
    else:
        if organizer_secret != current_app.organizer_secret:
            abort(403)
        return render('')


def parse_playerlist(playerlist: str) -> List[str]:
    """Split playerlist input text into a list of players."""
    playerlist = playerlist.strip()
    if ('\n' in playerlist) or ('\r' in playerlist):
        playersplit = playerlist.replace('\r', '\n').split('\n')
    else:
        # all on one line => split by ','
        playersplit = playerlist.split(',')
    result = []
    result_as_set: Set[str] = set()
    for x in playersplit:
        x = x.strip()
        if x == '' or x.lower() in result_as_set:
            continue
        result.append(x)
        result_as_set.add(x.lower())
    return result


@bp.route('/<organizer_secret>/wait_for_users/')
def wait_for_users(organizer_secret: str):
    """Present a dashboard for the game to the organizer."""
    if organizer_secret != current_app.organizer_secret:
        abort(403)
    else:
        return render_template('organizer/wait_for_users.html',
                               organizer_secret=organizer_secret,
                               players=current_app.game.players)


@bp.route('/start_game/', methods=('POST',))
def start_game():
    """Start the first round of the game at organizer's request."""
    if request.method != 'POST':
        abort(405)
    organizer_secret = request.form.get('organizer_secret', '')
    if organizer_secret != current_app.organizer_secret:
        abort(403)
    return b"start the game", 200


@bp.route('/<organizer_secret>/api/game_status/')
def api_game_status(organizer_secret):
    """Return Game status for AJAX API."""
    if current_app.organizer_secret != organizer_secret:
        abort(403)
    try:
        game = current_app.game
    except RuntimeError:
        abort(404)
    return json.dumps(
        {'players': {p.id: p.name
                     for p
                     in (game.confirmed_players
                         if game.state != game.state.CONFIRMING
                         # in CONFIRMING game.state, players are still
                         # adding themselves, game.confirmed_players
                         # is not valid yet.
                         else (_p for _p in game.players if _p.is_confirmed))},
         'state': game.state
         }).encode('utf-8')
