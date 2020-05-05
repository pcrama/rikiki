from .helper import ff_driver as driver, organizer_secret

from .player.test_player_confirmation import happy_path as test_player_confirmation_happy_path

from .player.test_player_dashboard import while_others_confirm as test_player_dashboard_while_others_confirm
from .player.test_player_dashboard import while_bidding as test_player_dashboard_while_bidding


from .organizer.test_game_setup import define_players as test_game_setup_define_player
from .organizer.test_game_setup import dashboard as test_game_setup_dashboard
