"""Controllers for the organizer."""

import functools
import os
from typing import List, Optional, Set

from flask import (Blueprint, abort, current_app, flash, jsonify,
                   redirect, render_template, request, session, url_for)
import jinja2
from flask_babel import _  # type: ignore
from flask_babel import lazy_gettext as _l  # type: ignore

from . import USER_COOKIE, models

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
        flash(_('Your name is already confirmed as %(n)s', n=player.name),
              'error')
        return redirect(url_for('player.player',
                                secret_id=player.secret_id,
                                _method='GET'))
    if game.state != game.State.CONFIRMING:
        return render_template('player/too-late.html',
                               player_name=player.name)
    if request.method == 'POST':
        player.confirm(request.form.get('player_name', ''))
        session[USER_COOKIE] = player.cookie
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
        flash(_('You must confirm your participation first'), 'error')
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
    '</li>')

WINNER_FRAGMENT = JINJA2_ENV.from_string('  {{name}} {{i18n}}')

i18n_card = _l("card")
i18n_trick = _l("trick")

PLAYER_LI_FRAGMENT = JINJA2_ENV.from_string(
    '<li id="{{ player.id }}" class="{{ player_class }}">'
    '<span class="player_name">{{ player.name }}</span> '
    '{{i18n}}.</li>')


def bidding_player_li_fragment(player, player_class):
    """Render PLAYER_LI_FRAGMENT for Player that did not bid yet."""
    return PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        i18n=_("has %(cards)s and has not bid yet",
               cards=pluralize(player.card_count, i18n_card)))


def has_bid_player_li_fragment(player, player_class):
    """Render PLAYER_LI_FRAGMENT for Player that bid but did not play yet."""
    return PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        i18n=_("has %(cards)s and bid for %(tricks)s",
               cards=pluralize(player.card_count, i18n_card),
               tricks=pluralize(player.bid, i18n_trick)))


def is_playing_player_li_fragment(player, player_class):
    """Render PLAYER_LI_FRAGMENT for Player while making tricks."""
    return PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        i18n=_("has %(cards)s, bid for %(tricks)s and won %(won_tricks)s",
               cards=pluralize(player.card_count, i18n_card),
               tricks=pluralize(player.bid, i18n_trick),
               won_tricks=pluralize(player.tricks, i18n_trick)))


def between_rounds_player_li_fragment(player, player_class):
    """Render description of Player between rounds."""
    i18n = _('bid for %(tricks)s and won %(won_tricks)s',
             tricks=pluralize(player.bid, i18n_trick),
             won_tricks=pluralize(player.tricks, i18n_trick))
    if player.bid == player.tricks:
        i18n += _(', the right amount of tricks')
    elif player.bid < player.tricks:
        i18n += _(', %(extra_tricks)s too many',
                  extra_tricks=pluralize(player.tricks - player.bid,
                                         i18n_trick))
    else:
        i18n += _(': there are %(missing_tricks)s missing',
                  missing_tricks=pluralize(player.bid - player.tricks,
                                           i18n_trick))
    return PLAYER_LI_FRAGMENT.render(
        player=player,
        player_class=player_class,
        i18n=i18n)


PLAYER_CARD_FRAGMENT = JINJA2_ENV.from_string(
    '<div class="playing_card_column">'
    '<div class="playing_card" id="{{ card_id }}">'
    '<img src="{{ card_url }}" title="{{ player_name }}" style="width:100%">'
    '</div>'
    '{{ player_name }}'
    '</div>')


SIMPLE_CARD_FRAGMENT = JINJA2_ENV.from_string(
    '<span class="playing_card" id="{{ card_id }}"><img src="'
    '{{ card_url }}"></span>')


FINISH_ROUND_FRAGMENT = JINJA2_ENV.from_string(
    '<div id="finishRound"><div '
    'id="finishRoundError"></div><input type="button" '
    'id="finishRoundSubmit" value="{{i18n}}" '
    'onclick="submitFinishRound('
    ''''{{ player.secret_id }}')"></div>''')


def finish_round_fragment(player):
    """Render FINISH_ROUND_FRAGMENT."""
    return FINISH_ROUND_FRAGMENT.render(player=player, i18n=_('Finish Round'))


def card_html_id(card):
    """Return HTML id for element containing given card."""
    return f'c{card:02d}'


def render_player_card_fragment(card, player=None):
    """Render PLAYER_CARD_FRAGMENT."""
    card_id = card_html_id(card)
    card_url = url_for('static', filename=f'cards/card{card:02d}.png')
    if player is None:
        return SIMPLE_CARD_FRAGMENT.render(card_id=card_id, card_url=card_url)
    else:
        return PLAYER_CARD_FRAGMENT.render(
            player_name=player.name, card_id=card_id, card_url=card_url)


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
    if round_state == models.Round.State.DONE:
        return between_rounds_player_li_fragment(
            player=subject,
            player_class=player_css_class(subject, viewer, None))
    player_class = player_css_class(subject, viewer, current_player)
    if subject.bid is None:
        return bidding_player_li_fragment(
            player=subject, player_class=player_class)
    if round_state == models.Round.State.BIDDING:
        return has_bid_player_li_fragment(
            player=subject, player_class=player_class)
    return is_playing_player_li_fragment(
        player=subject, player_class=player_class)


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
            'trump': (_('No trump')
                      if game.round.trump is None
                      else (_('Trump: ')
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
            result['table'] = render_table(game)
            result['playable_cards'] = [
                card_html_id(card) for card in player.playable_cards
            ] if player is game.round.current_player \
                else []
        elif game.round.state == models.Round.State.DONE:
            result['table'] = render_table(game)
            result['playable_cards'] = []
        return jsonify(result)
    abort(500, "Should not be reached")


def render_table(game):
    """Render current cards on table as HTML fragment."""
    return ''.join(render_player_card_fragment(c, player=p)
                   for p, c in game.round.current_trick)


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
        return _('Waiting for other players to join and '
                 'organizer to start the game.')
    card_count = _(' with %(cards)s',
                   cards=pluralize(game.current_card_count, i18n_card))
    bid_count = (''
                 if total_bids is None
                 else (_('1 trick bid')
                       if total_bids == 1
                       else _('%(tricks)s bid',
                              tricks=pluralize(total_bids, i18n_trick))))
    if game.round.state == models.Round.State.BIDDING:
        return _('Bidding %(card_count)s, %(bid_count)s so far.',
                 card_count=card_count,
                 bid_count=bid_count)
    elif game.round.state == models.Round.State.PLAYING:
        return _('Playing %(card_count)s, %(bid_count)s.',
                 card_count=card_count,
                 bid_count=bid_count)
    elif game.round.state in [
            models.Round.State.BETWEEN_TRICKS,
            models.Round.State.DONE]:
        winner = WINNER_FRAGMENT.render(name=game.round.current_player.name,
                                        i18n=_(' won the trick.'))
        if game.state == models.Game.State.PAUSED_BETWEEN_ROUNDS:
            return _('Round finished.') + winner + \
                finish_round_fragment(player=player)
        else:
            return _('Playing %(card_count)s, %(bid_count)s.',
                     card_count=card_count,
                     bid_count=bid_count
                     ) + winner
    return (f'NOT REACHED game.state={game.state}, round:'
            f'{"No Round" if game._round is None else game._round.state}')


@bp.route('/restore/link/', methods=('GET', 'POST',))
@with_valid_game
def restore_link(game=None):
    """Control player's link restore operation.

    GET: return page with simple submit button and hidden CSRF token
    POST: if CSRF token is right, restore player.
    """
    try:
        cookie = session[USER_COOKIE]
    except KeyError:
        abort(403)
    try:
        player = game.player_by_cookie(cookie)
    except StopIteration:
        abort(403)
    if not player.is_confirmed:
        abort(403)
    if request.method == 'GET':
        return render_template(
            'player/restore_link.html', game=game, player=player)
    elif request.method == 'POST':
        if request.form.get('csrf_token', '') != game.csrf_token:
            abort(404)
        player.update_secret()
        session[USER_COOKIE] = player.cookie
        return redirect(url_for('player.player',
                                secret_id=player.secret_id,
                                _method='GET'))
    else:
        abort(405)  # NOT REACHED
