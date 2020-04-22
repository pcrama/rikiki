"""Controllers for the organizer."""

import functools

from flask import Blueprint, abort, flash, redirect, render_template, request

from . import ORGANIZER_SECRET, GAME

bp = Blueprint('organizer', __name__, url_prefix='/organizer')


@bp.route('/', methods=('GET', 'POST',))
@bp.route('/<organizer_secret>/')
def organizer(organizer_secret=''):
    """Control Game model for the organizer."""
    def render(playerlist):
        return render_template('organizer/organizer.html',
                               playerlist=playerlist,
                               organizer_secret=ORGANIZER_SECRET)

    if request.method == 'POST':
        organizer_secret = request.form.get('organizer_secret', '')
        if organizer_secret != ORGANIZER_SECRET:
            abort(403)
        playerlist = request.form.get('playerlist', '').strip()
        if playerlist == '':
            flash('No player list provided', 'error')
            return render(playerlist)
        flash('Creating a Game not yet implemented', 'error')
        return render(playerlist)
    else:
        if organizer_secret != ORGANIZER_SECRET:
            abort(403)
        return render('')
