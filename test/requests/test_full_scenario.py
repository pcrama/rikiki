import itertools
import random

import flask
from jinja2 import escape

import pytest  # type: ignore

import app  # type: ignore
from app.organizer import parse_playerlist
from app.player import organizer_url_for_player
from app import models

from .helper import (
    FLASH_ERROR,
    client,
    organizer_secret,
    rendered_template,
    rikiki_app,
)


def test_full_scenario(rikiki_app, organizer_secret, client):
    PLAYER_NAMES = [
        'riri', 'fifi', 'lulu', 'toto', 'momo', 'mama', 'papa']
    response = client.post(
        '/organizer/setup/game/',
        data={'organizer_secret': organizer_secret,
              'playerlist': '\n'.join(PLAYER_NAMES)},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    game = rikiki_app.game
    for p in game.players:
        response = client.post(
            '/player/confirm/',
            data={'secret_id': p.secret_id, 'player_name': ''},
            follow_redirects=True)
        assert response.status_code == 200
        assert FLASH_ERROR not in response.data
        assert p.is_confirmed
    response = client.post(
        '/organizer/start_game/',
        data={'organizer_secret': organizer_secret},
        follow_redirects=True)
    assert response.status_code == 200
    assert FLASH_ERROR not in response.data
    for cards_to_play in itertools.chain(
            # first cards count downwards: 7, 6, 5, 4, 3, 2, 1 ...
            range(game.current_card_count, 0, -1),
            # ... then upwards again: 2, 3, 4, 5, 6, 7
            range(2, game.current_card_count + 1)):
        assert game.state == models.Game.State.PLAYING
        assert game.round.state == models.Round.State.BIDDING
        for (idx, p) in enumerate(game.confirmed_players):
            response = client.get(organizer_url_for_player(p))
            assert response.status_code == 200
            assert FLASH_ERROR not in response.data
            assert rendered_template(response, 'player.player')
            response = client.post(
                '/player/place/bid/',
                data={'secret_id': p.secret_id,
                      'bidInput': str(idx % min(4, cards_to_play + 1))})
            assert response.status_code == 200
            assert response.is_json
            status = response.get_json()
            assert status['ok']
        assert game.round.state == models.Round.State.PLAYING
        for cards_played in range(cards_to_play):
            for cards_on_table in range(len(game.confirmed_players)):
                player = game.round.current_player
                response = client.get(
                    f'/player/{player.secret_id}/api/status/')
                assert response.status_code == 200
                assert response.is_json
                response = client.post(
                    '/player/play/card/',
                    data={'secret_id': player.secret_id,
                          'card': str(player.playable_cards[0])})
                assert response.status_code == 200
                assert response.is_json
                status = response.get_json()
                assert status['ok']
                if cards_on_table < len(game.confirmed_players) - 1:
                    assert game.round.state == models.Round.State.PLAYING
            if cards_played < cards_to_play - 1:
                assert game.round.state == models.Round.State.BETWEEN_TRICKS
                assert game.state == models.Game.State.PLAYING
            else:
                assert game.state == models.Game.State.PAUSED_BETWEEN_ROUNDS
                assert game.round.state == models.Round.State.DONE
                for player in game.confirmed_players:
                    response = client.get(
                        f'/player/{player.secret_id}/api/status/')
                    assert response.status_code == 200
                    assert response.is_json
                # NB: when last Round of Game finishes, an explicit
                # /player/finish/round/ is still needed to push the
                # Game to Game.State.DONE.  One player would be
                # enough, but they can all have a go if they want,
                # test with only 2:
                for finisher in game.confirmed_players[:2]:
                    response = client.post(
                        f'/player/finish/round/',
                        data={'secret_id': finisher.secret_id})
                    assert response.status_code == 200
                    assert response.is_json
                    status = response.get_json()
                    assert status['ok']
                    for player in game.confirmed_players:
                        response = client.get(
                            f'/player/{player.secret_id}/api/status/')
                        assert response.status_code == 200
                        assert response.is_json
    # game never stops
    assert game.state == models.Game.State.DONE
