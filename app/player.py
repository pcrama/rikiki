"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, jsonify,
                   redirect, render_template, request, url_for)
import jinja2

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


@bp.route('/place/bid/', methods=('POST',))
@with_valid_game
def place_bid(secret_id='', previous_status_summary='', game=None):
    """Control Player model for the players: place a bid."""
    player = get_player(current_app, request, secret_id)
    if (not player.is_confirmed or
        (game is None) or
        (game.state != models.Game.State.PLAYING) or
        (game.round is None) or
            (game.round.state != models.Round.State.BIDDING)):
        abort(404)
    # just let it crash if form data is invalid (missing or not a number)
    bid = int(request.form.get('bidInput'))
    try:
        player.place_bid(bid)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    else:
        return jsonify({'ok': True})


@bp.route('/play/card/', methods=('POST',))
@with_valid_game
def play_card(secret_id='', previous_status_summary='', game=None):
    """Control Player model for the players: place a bid."""
    player = get_player(current_app, request, secret_id)
    # TODO: this logic belongs in the model?
    if (not player.is_confirmed or
        (game is None) or
        (game.state != models.Game.State.PLAYING) or
        (game.round is None) or
            (game.round.state not in [
                models.Round.State.PLAYING,
                models.Round.State.BETWEEN_TRICKS])):
        abort(404)
    # just let it crash if form data is invalid (missing, not a number
    # or out of card range): normal UI usage should only send a
    # corrrect card number
    card = models.Card(int(request.form.get('card')))
    try:
        player.play_card(card)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    else:
        return jsonify({'ok': True})


@bp.route('/finish/round/', methods=('POST',))
@with_valid_game
def finish_round(secret_id='', previous_status_summary='', game=None):
    """Control Player model for the players: place a bid."""
    player = get_player(current_app, request, secret_id)
    # # TODO: this logic belongs in the model?
    # if (not player.is_confirmed or
    #     (game is None) or
    #     (game.state != models.Game.State.PLAYING) or
    #     (game.round is None) or
    #         (game.round.state not in [
    #             models.Round.State.PLAYING,
    #             models.Round.State.BETWEEN_TRICKS])):
    #     abort(404)
    try:
        if player.is_confirmed:
            game.start_next_round()
        else:
            raise Exception(f'{player.name} should be confirmed to do this')
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})
    else:
        return jsonify({'ok': True})


def other_player_status(p: models.Player):
    """Gather information about other Players."""
    return {'id': p.id,
            'name': p.name,
            'tricks': p.tricks,
            'cards': p.card_count,
            'bid': p.bid}


JINJA2_ENV = jinja2.Environment(autoescape=jinja2.select_autoescape(
    enabled_extensions=('html', 'xml'),
    default_for_string=True,
))
CONFIRMING_PLAYER_LI_FRAGMENT = JINJA2_ENV.from_string(
    '<li id="{{ player.id }}" class="{{ player_class }}">'
    '{{ player.name }}'
    '</li>'
)
BIDDING_PLAYER_LI_FRAGMENT = JINJA2_ENV.from_string(
    '<li id="{{ player.id }}" class="{{ player_class }}">'
    '<span class="player_name">{{ player.name }}</span> has '
    '{{ player_count_cards }} and has not bid yet.'
    '</li>'
)


def bidding_player_li_fragment(player, player_class):
    """Render BIDDING_PLAYER_LI_FRAGMENT."""
    return BIDDING_PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        player_count_cards=pluralize(player.card_count, "card"))


HAS_BID_PLAYER_LI_FRAGMENT = JINJA2_ENV.from_string(
    '<li id="{{ player.id }}" class="{{ player_class }}">'
    '<span class="player_name">{{ player.name }}</span> has '
    '{{player_count_cards}} and bid for {{player_bid_tricks}}.</li>')


def has_bid_player_li_fragment(player, player_class):
    """Render HAS_BID_PLAYER_LI_FRAGMENT."""
    return HAS_BID_PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        player_count_cards=pluralize(player.card_count, "card"),
        player_bid_tricks=pluralize(player.bid, "trick"))


IS_PLAYING_PLAYER_LI_FRAGMENT = JINJA2_ENV.from_string(
    '<li id="{{ player.id }}" class="{{ player_class }}">'
    '<span class="player_name">{{ player.name }}</span> has '
    '{{ player_count_cards }}, bid for {{player_bid_tricks}} '
    'and won {{player_won_tricks}}.</li>')


def is_playing_player_li_fragment(player, player_class):
    """Render IS_PLAYING_PLAYER_LI_FRAGMENT."""
    return IS_PLAYING_PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        player_count_cards=pluralize(player.card_count, "card"),
        player_bid_tricks=pluralize(player.bid, "trick"),
        player_won_tricks=pluralize(player.tricks, "trick"))


PLAYER_CARD_FRAGMENT = JINJA2_ENV.from_string(
    '<span class="playing_card" id="{{ card_id }}"><img src="'
    '{{ card_url }}"></span>')
FINISH_ROUND_FRAGMENT = JINJA2_ENV.from_string(
    '<form id="finishRound" onsubmit="submitFinishRound()"><div '
    'id="finishRoundError"></div><input type="submit" '
    'id="finishRoundSubmit" value="Finish '
    'Round"><input type="hidden" name="secret_id" '
    'value="{{ player.secret_id }}"></form>')


def card_html_id(card):
    """Return HTML id for element containing given card."""
    return f'c{card:02d}'


def render_player_card_fragment(card):
    """Render PLAYER_CARD_FRAGMENT."""
    return PLAYER_CARD_FRAGMENT.render(
        card_id=card_html_id(card),
        card_url=url_for('static',
                         filename=f'cards/card{card:02d}.png'))


def player_css_class(p1, p2, cp=None):
    """Get CSS classes for player.

    For each page, there is a reference player (p2, associated to the
    secret in the URL).  Information for that player should be styled
    with 'self_player'.  All other players get 'other_player'.

    If cp is defined, it indicates which p1 should get the
    'current_player' class extra.
    """
    return ("self_player" if p1 is p2 else "other_player") + (
        " current_player" if p1 is cp else "")


def player_html(
        subject: models.Player,
        viewer: models.Player,
        current_player: models.Player,
        round_state: models.Round.State
) -> str:
    """Return HTML content describing the Player's status."""
    if subject.bid is None:
        return bidding_player_li_fragment(
            player=subject,
            player_class=player_css_class(
                subject, viewer, current_player))
    if round_state == models.Round.State.BIDDING:
        return has_bid_player_li_fragment(
            player=subject,
            player_class=player_css_class(
                subject, viewer, current_player))
    return is_playing_player_li_fragment(
        player=subject,
        player_class=player_css_class(
            subject,
            viewer,
            None
            if round_state == models.Round.State.DONE
            else current_player))


@bp.route('/<secret_id>/api/status/')
@bp.route('/<secret_id>/api/status/<previous_status_summary>/')
@with_valid_game
def api_status(secret_id='', previous_status_summary='', game=None):
    """Return JSON formatted status for Player."""
    player = get_player(current_app, request, secret_id)
    if not player.is_confirmed:
        abort(404)

    status_summary = game.status_summary()
    if (status_summary == previous_status_summary) and (
            previous_status_summary != ''):
        return jsonify({'summary': status_summary})
    elif game.state == game.State.CONFIRMING:
        return jsonify({
            'summary': status_summary,
            'game_state': game_state(game, player),
            'id': player.id,
            'players': [
                {'id': p.id,
                 'h': CONFIRMING_PLAYER_LI_FRAGMENT.render(
                     player=p,
                     player_class=player_css_class(p, player, None))}
                for p in game.players if p.is_confirmed]})
    elif game.state in [models.Game.State.PLAYING,
                        models.Game.State.PAUSED_BETWEEN_ROUNDS,
                        models.Game.State.DONE]:
        total_bids = sum((p.bid or 0) for p in game.confirmed_players)
        cards = [render_player_card_fragment(card) for card in player.cards]
        cards.sort(reverse=True)
        result = {
            'summary': status_summary,
            'game_state': game_state(game, player, total_bids=total_bids),
            'id': player.id,
            'cards': ''.join(cards),
            'trump': ('No trump'
                      if game.round.trump is None
                      else ('Trump: '
                            + render_player_card_fragment(game.round.trump))),
            'round': {'state': game.round.state,
                      'current_player': game.round.current_player.id},
            'players': [
                {'id': p.id,
                 'h': player_html(
                     subject=p,
                     viewer=player,
                     current_player=game.round.current_player,
                     round_state=game.round.state)}
                for p in game.confirmed_players]}
        if game.round.state in [models.Round.State.PLAYING,
                                models.Round.State.BETWEEN_TRICKS]:
            result['table'] = ''.join(render_player_card_fragment(c)
                                      for c in game.round.current_trick)
            result['playable_cards'] = [
                card_html_id(card) for card in player.playable_cards
            ] if player is game.round.current_player \
                else []
        elif game.round.state == models.Round.State.DONE:
            result['table'] = ''.join(render_player_card_fragment(c)
                                      for c in game.round.current_trick)
            result['playable_cards'] = []
        return jsonify(result)
    abort(500, "Should not be reached")


def pluralize(n, s):
    """Return a count of objects."""
    if n == 1:
        return f'1 {s}'
    else:
        return f'{n} {s}s'


def game_state(
        game: models.Game,
        player: models.Player,
        total_bids: Optional[int] = None
) -> str:
    """Return HTML fragment describing game state for Player's dashboard."""
    if game.state == game.State.CONFIRMING:
        return ('Waiting for other players to join and '
                'organizer to start the game')
    card_count = f' with {pluralize(game.current_card_count, "card")}'
    bid_count = (''
                 if total_bids is None
                 else f' and {pluralize(total_bids, "trick")} bid')
    if game.round.state == models.Round.State.BIDDING:
        return 'Bidding' + card_count + bid_count + ' so far.'
    elif game.round.state == models.Round.State.PLAYING:
        return 'Playing' + card_count + bid_count + '.'
    elif game.round.state in [
            models.Round.State.BETWEEN_TRICKS,
            models.Round.State.DONE]:
        winner = f'{game.round.current_player.name} won the trick.'
        if game.state == models.Game.State.PAUSED_BETWEEN_ROUNDS:
            return 'Round finished.  ' + winner + \
                FINISH_ROUND_FRAGMENT.render(player=player)
        else:
            return 'Playing' + card_count + bid_count + '.  ' + \
                winner
    return (f'NOT REACHED game.state={game.state}, round:'
            f'{"No Round" if game._round is None else game._round.state}')
