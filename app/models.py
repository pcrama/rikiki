"""Model classes (the M in MVC)."""
import enum
import hashlib
import os
import random
from typing import (List, Optional)


class ModelError(RuntimeError):
    """Super class for all exceptions thrown by the models."""

    pass


class IllegalStateError(ModelError):
    """A model was asked to perform an illegal state transition."""

    pass


class PlayerRetryableError(ModelError):
    """A Player tried to do something forbidden, but may retry."""

    pass


class CardNotAllowedError(PlayerRetryableError):
    """A Player tried to play a card but forbidden by rules."""

    def __init__(self, offending_player, offending_card):
        """Create new CardNotallowederror."""
        self.offending_player = offending_player
        self.offending_card = offending_card


class OutOfTurnError(PlayerRetryableError):
    """A Player tried to place a bid or play a card outside his turn."""

    def __init__(self, operation, current_player, offending_player):
        """Create new OutOfTurnError."""
        self.operation = operation
        self.current_player = current_player
        self.offending_player = offending_player
        super().__init__(
            f"{offending_player} wanted to {operation}, "
            f"but it is {current_player}'s turn")


def _ensure_non_blank(s, name, message=None):
    if s is None or s.strip() == "":
        msg = (f"{name} should be a non-empty string"
               if message is None or message.strip == ()
               else message)
        raise ValueError(msg)


class Game:
    """Handle confirming of the players and sequencing the rounds."""

    @enum.unique
    class State(enum.IntEnum):
        """States of a Game."""

        # Explicit values because the client code in the web browser
        # needs them as well.
        CONFIRMING: int = 0
        PLAYING: int = 1
        PAUSED_BETWEEN_ROUNDS: int = 2
        DONE: int = 3

    def __init__(self, players: List["Player"]):
        """Create new Game instance."""
        self._players = players
        """List of players invited to the Game."""
        self._state = Game.State.CONFIRMING
        """Game state."""
        self._confirmed_players: List["Player"] = []
        """List of players that had confirmed before Game started."""
        self._current_card_count: int = 0
        """How many cards are used in the current round."""
        self._round: Optional["Round"]

    def status_summary(self) -> str:
        """Return an identifier for the current state.

        This identifier helps detect state changes and trigger redraws
        of the UI.
        """
        result = f'{self._state}+{len(self._players)}' \
            f'+{sum(p.is_confirmed for p in self._players)}' \
            f'+{len(self._confirmed_players)}' \
            f'+{"".join(chr(len(p.name) % 27 + 64) for p in self._players)}'
        try:
            result += str(self._current_card_count)
        except Exception:
            pass
        else:
            try:
                result += self.round.status_summary()
            except Exception:
                pass
        return result

    def start_game(self) -> "Round":
        """Start first Round of the Game."""
        self._ensure_state(Game.State.CONFIRMING)
        confirmed_players = [
            player for player in self.players if player.is_confirmed]
        if len(confirmed_players) < 2:
            raise IllegalStateError("At least 2 confirmed players necessary")
        self._state = Game.State.PLAYING
        self._confirmed_players = confirmed_players
        self._current_card_count = MAX_CARDS // len(confirmed_players)
        self._round = Round(self, self._current_card_count)
        return self._round

    def _ensure_state(self, state: "Game.State") -> None:
        if self._state != state:
            raise IllegalStateError(
                f"Expected {state} for game, not {self._state}")

    @property
    def players(self) -> List["Player"]:
        """Return list of Player's invited to the Game."""
        return self._players

    def player_by_id(self, _id) -> "Player":
        """Look up a Player by her public ID."""
        return next(p for p in self._players if p.id == _id)

    def player_by_secret_id(self, secret_id) -> "Player":
        """Look up a Player by her secret ID."""
        return next(p for p in self._players if p.secret_id == secret_id)

    @property
    def confirmed_players(self) -> List["Player"]:
        """Return list of Player's that confirmed their participation."""
        return self._confirmed_players

    @property
    def round(self) -> "Round":
        """Return Round that is currently being played."""
        self._ensure_state(Game.State.PLAYING)
        if self._round is None:
            raise ModelError(
                f'_round is None even though state is {self._state}')
        return self._round

    @property
    def current_card_count(self) -> int:
        """Return number of cards with which current Round is being played."""
        if self.state in [
                Game.State.PLAYING, Game.State.PAUSED_BETWEEN_ROUNDS]:
            return self._current_card_count
        elif self.state == Game.State.CONFIRMING:
            raise IllegalStateError(
                f"Game.state={self.state}, current_card_count is undefined.")
        else:
            return 0

    @property
    def state(self) -> "Game.State":
        """Return current Game.State."""
        return self._state

    def round_finished(self) -> None:
        """Call from Round when all cards have been played."""
        self._ensure_state(Game.State.PLAYING)
        self._state = Game.State.PAUSED_BETWEEN_ROUNDS

    def start_next_round(self) -> None:
        """Call to confirm previous Round is finished and start next Round."""
        self._ensure_state(Game.State.PAUSED_BETWEEN_ROUNDS)
        self._current_card_count -= 1
        if self._current_card_count > 0:
            self._state = Game.State.PLAYING
            self._round = Round(self, self._current_card_count)
        else:
            self._state = Game.State.DONE


PLAYER_COUNTER = 0


class Player:
    """Participant in the game."""

    def __init__(self, provisional_name: str, secret_id: str):
        """Initialize a new Player."""
        _ensure_non_blank(provisional_name, name="provisional_name")
        _ensure_non_blank(secret_id, name="secret_id")
        self._provisional_name = provisional_name
        """The display name of the Player as proposed by the Organizer."""
        self._secret_id = secret_id
        """A random string to authenticate the confirmation process."""
        self._confirmed_secret_id = "".join(f"{x:02X}" for x in os.urandom(16))
        """A random string to authenticate all links after confirmation."""
        global PLAYER_COUNTER
        PLAYER_COUNTER += 1
        self._id = '{0}_{1}'.format(
            PLAYER_COUNTER,
            hashlib.md5(secret_id.encode('utf-8')).hexdigest()[:8])
        """A random string, will be used as public ID in API."""
        self._confirmed_name: Optional[str] = None
        """The name the Player chose for himself."""
        self._cards: List["Card"] = []
        """The Player's hand"""
        self._bid: Optional[int] = None
        """The Player's bid: how much tricks does she believe she will make in
a Round."""
        self._round: Optional["Round"] = None
        """Reference to the Round the Player is currently participating in."""
        self._tricks = 0
        """How many tricks the Player has already won in a Round."""

    @property
    def name(self) -> str:
        """Return the display name of the Player."""
        if self._confirmed_name is None:
            return self._provisional_name
        else:
            return self._confirmed_name

    @property
    def secret_id(self) -> str:
        """Return the secret id of the Player."""
        return (self._confirmed_secret_id
                if self.is_confirmed
                else self._secret_id)

    @property
    def id(self) -> str:
        """Return the public id of the Player."""
        return self._id

    @property
    def is_confirmed(self) -> bool:
        """Flag if Player already confirmed her name, i.e. joined the game."""
        return self._confirmed_name is not None

    @property
    def has_bid(self) -> bool:
        """Flag if Player has placed a bid in the current Round."""
        return self.is_confirmed and self._bid is not None

    @property
    def bid(self) -> Optional[int]:
        """Return how many tricks the Player believes she is going to win."""
        return self._bid

    def place_bid(self, value: int) -> None:
        """Announce how many tricks the Player believes she is going to win."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        assert self._round is not None, \
            ("_ensure_has_cards() should already do that, "
             "but mypy does not see it")
        if 0 <= value <= len(self._cards):
            self._bid = value
            self._round.place_bid(self, value)
        else:
            raise ValueError(
                f"{self} can't bid {value}: outside [0, {len(self._cards)}]")

    def __str__(self) -> str:
        """Return string representation of self."""
        # if something fails here, debugging gets very difficult
        # because the debugger can't print the object we might want to
        # look at ...
        try:
            prefix = (f"{self.name}="
                      if self.name != self._provisional_name
                      else "")
            return f"{prefix}Player({self._provisional_name!r}, ...)"
        except Exception:
            # ... so we have a fallback:
            return super().__str__()

    def confirm(self, confirmed_name: str) -> None:
        """Accept invitation by confirming or updating the display name."""
        if confirmed_name is None or confirmed_name.strip() == '':
            self._confirmed_name = self._provisional_name
        else:
            self._confirmed_name = confirmed_name

    @property
    def tricks(self) -> int:
        """Return how many tricks the player took in this Round."""
        return self._tricks

    def add_trick(self) -> None:
        """Increment trick count, called by Round for winner of the trick."""
        self._ensure_confirmed()
        self._ensure_has_bid()
        self._tricks += 1

    @property
    def card_count(self) -> int:
        """Return the number of cards in the Player's hand."""
        return len(self._cards)

    @property
    def cards(self) -> List["Card"]:
        """Return cards in the Player's hand."""
        return self._cards

    @property
    def playable_cards(self) -> List["Card"]:
        """Return cards that Player may play in current Round's state."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        self._ensure_has_bid()
        if self._round is None:
            raise RuntimeError(
                "Keep mypy happy, he should already know that _round "
                "can't be None here")
        return [c for c in self._cards if self._card_allowed(c)]

    def accept_cards(
            self,
            round_: "Round",
            cards: List["Card"]
    ) -> None:
        """Accept the cards that the Round has dealt."""
        self._ensure_confirmed()
        if self._round is None or self._cards == []:
            self._round = round_
            self._cards = cards
            self._tricks = 0
            self._bid = None
        else:
            raise IllegalStateError(f"{self} can't change game round now")

    def _ensure_confirmed(self) -> None:
        if not self.is_confirmed:
            raise IllegalStateError(f"{self} not confirmed yet")

    def _ensure_has_cards(self) -> None:
        if self._cards == [] or self._round is None:
            raise IllegalStateError(
                f"{self} has no cards or not in a round")

    def _ensure_has_bid(self) -> None:
        if self._bid is None:
            raise IllegalStateError(f"{self} has not placed his bid yet")

    def _card_allowed(self, card):
        return self._round.card_allowed(card, hand=self.cards)

    def play_card(self, card):
        """Put a card down on the table."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        self._ensure_has_bid()
        if self._card_allowed(card):
            self._cards.remove(card)
            try:
                self._round.play_card(self, card)
            except Exception as e:
                # card was not accepted on table, restore player's hand ...
                self._cards.append(card)
                # ... but do not lose the exception
                raise
        else:
            raise CardNotAllowedError(
                offending_player=self, offending_card=card)
        return card


CARDS_PER_SUIT = 13
SUITS = 4
MAX_CARDS = CARDS_PER_SUIT * SUITS


@enum.unique
class Card(enum.IntEnum):
    r"""Enumeration of all cards.

    (let ((counter 0))
      (dolist (suit '("Spade" "Club" "Diamond" "Heart"))
        (dolist (value '(2 3 4 5 6 7 8 9 10 "Jack" "Queen" "King" "Ace"))
          (insert (format "\n    %s%s = %d" suit value counter))
          (incf counter))))
    """

    Spade2 = 0
    Spade3 = 1
    Spade4 = 2
    Spade5 = 3
    Spade6 = 4
    Spade7 = 5
    Spade8 = 6
    Spade9 = 7
    Spade10 = 8
    SpadeJack = 9
    SpadeQueen = 10
    SpadeKing = 11
    SpadeAce = 12
    Club2 = 13
    Club3 = 14
    Club4 = 15
    Club5 = 16
    Club6 = 17
    Club7 = 18
    Club8 = 19
    Club9 = 20
    Club10 = 21
    ClubJack = 22
    ClubQueen = 23
    ClubKing = 24
    ClubAce = 25
    Diamond2 = 26
    Diamond3 = 27
    Diamond4 = 28
    Diamond5 = 29
    Diamond6 = 30
    Diamond7 = 31
    Diamond8 = 32
    Diamond9 = 33
    Diamond10 = 34
    DiamondJack = 35
    DiamondQueen = 36
    DiamondKing = 37
    DiamondAce = 38
    Heart2 = 39
    Heart3 = 40
    Heart4 = 41
    Heart5 = 42
    Heart6 = 43
    Heart7 = 44
    Heart8 = 45
    Heart9 = 46
    Heart10 = 47
    HeartJack = 48
    HeartQueen = 49
    HeartKing = 50
    HeartAce = 51


def same_suit(card1: Card, card2: Card) -> bool:
    """Return True if 2 Card belong to the same suit."""
    return card1 // CARDS_PER_SUIT == card2 // CARDS_PER_SUIT


def card_allowed(card: Card, hand: List[Card] = [], table: List[Card] = []):
    """Check if a Card may be played."""
    if card not in hand:  # must hold the card to play it
        return False
    if table == []:
        return True  # anything goes on an empty table
    first_card = table[0]
    if same_suit(first_card, card):
        return True  # following suit of starting card is always
    # playing a different suit allowed than first card on table is
    # only allowed if no other card is present in Player's hand:
    return not any(same_suit(first_card, c) for c in hand)


def beats(card1: Card,
          card2: Card,
          first_card_in_trick: Card,
          trump: Optional[Card] = None) -> bool:
    """Return True if card1 beats card2."""
    if trump is not None:
        if same_suit(card1, trump) and same_suit(card2, trump):
            return card1 > card2
        elif same_suit(card1, trump):
            return True
        elif same_suit(card2, trump):
            return False
        else:
            # Neither card is from the same suit as the trump card:
            # the comparison rules apply as if there was no trump
            # card:
            return beats(card1, card2, first_card_in_trick, trump=None)
    else:
        if (same_suit(card1, first_card_in_trick) and
                same_suit(card2, first_card_in_trick)):
            return card1 > card2
        elif same_suit(card1, first_card_in_trick):
            return True
        elif same_suit(card2, first_card_in_trick):
            return False
        elif same_suit(card1, card2):
            return card1 > card2
        else:
            # This case does not really matter (except maybe to sort
            # the player's hand for display purposes).  When looking
            # for the winning card in a trick, the first card of the
            # trick will always trivially satisfy 'same_suit(card1,
            # first_card_in_trick)' and hence be compared with the
            # next cards and so on, looking for the maximum.
            return card1 > card2


class Round:
    """A Round deals the cards, handles the bidding and playing process."""

    @enum.unique
    class State(enum.IntEnum):
        """States of a Round."""

        # Explicit values because the client code in the web browser
        # needs them as well.
        BIDDING: int = 100
        PLAYING: int = 101
        BETWEEN_TRICKS: int = 102
        DONE: int = 103

    def __init__(self,
                 game: Game,
                 how_many_cards: int):
        """Create new instance with confirmed participating Players."""
        confirmed_players = game.confirmed_players
        if (len(confirmed_players) > 1
                and all(p.is_confirmed for p in confirmed_players)):
            self._players = confirmed_players
        else:
            raise ValueError(
                "Can't create Round without at least 2 players, all confirmed")
        if (how_many_cards > 0
                and (how_many_cards * len(confirmed_players)) <= MAX_CARDS):
            self.deal_cards(how_many_cards)
        else:
            raise ValueError(
                "how_many_cards must be > 0 but not too large either")
        self._game = game
        # type hints for mypy, but initialized by _init_new_trick
        self._current_player: int
        self._current_trick: List[Card]
        self._first_card: Optional[Card]
        self._trick_winner: Optional[int]
        self._trick_winner_card: Optional[Card]
        self._init_new_trick(0)  # start with first player
        self._current_trick = []
        self._state = Round.State.BIDDING

    @property
    def state(self) -> State:
        """Return Round's State."""
        return self._state

    def status_summary(self) -> str:
        """Return an identifier for the current state.

        This identifier helps detect state changes and trigger redraws
        of the UI.
        """
        result = f'{chr(self._state - Round.State.BIDDING + ord("0"))}' \
            f'{self._current_player}'
        if self._state == Round.State.BIDDING:
            idx = 0
            while True:
                try:
                    p = self._players[idx]
                    result += chr(p.bid + ord("A"))  # type: ignore
                except Exception:
                    break
                else:
                    idx += 1
        elif self._state == Round.State.PLAYING:
            result += ''.join(chr(p.card_count + ord("a"))
                              for p in self._players)
        return result

    @property
    def current_player(self) -> Player:
        """Return Player whose turn it is."""
        return self._players[self._current_player]

    @property
    def current_trick(self) -> List[Card]:
        """Return cards currently on the table."""
        return self._current_trick

    def play_card(self, player: Player, card: Card) -> None:
        """Call from player to notify that she put a card down."""
        self._ensure_state([Round.State.PLAYING, Round.State.BETWEEN_TRICKS])
        self._ensure_current_player(player, "play")
        # TODO: it would be nice to test that all players always have
        # a consistent number of cards... but code would be
        # complicated & hard to test

        if self._state == Round.State.BETWEEN_TRICKS:
            # previous trick was complete, 1st player is playing->reinitialize
            self._current_trick = []
            self._state = Round.State.PLAYING
        if self._current_trick == []:
            # this is the start of a new trick, track who wins the trick
            self._first_card = card
            self._trick_winner = self._current_player
            self._trick_winner_card = card
        else:
            assert (self._trick_winner_card is not None
                    and self._first_card is not None), \
                ("reassure mypy, these are set in the other branch "
                 "before getting here")
            if beats(card,
                     self._trick_winner_card,
                     first_card_in_trick=self._first_card,
                     trump=self._trump):
                self._trick_winner = self._current_player
                self._trick_winner_card = card

        self._current_trick.append(card)
        # advance to next player
        self._current_player = (self._current_player + 1) % len(self._players)
        # check if trick is complete:
        if len(self._current_trick) >= len(self._players):
            assert self._trick_winner is not None, \
                ("reassure mypy, self._trick_winner should always "
                 "be initialized when we get here")
            # trick is complete: every player put her card down on the
            # table, attribute the trick to the winner
            self._players[self._trick_winner].add_trick()
            # check if Round is complete:
            if any(p.card_count == 0 for p in self._players):
                # At the end of the Round, all players must have no
                # cards left:
                if any(p.card_count != 0 for p in self._players):
                    raise IllegalStateError(
                        "Not all players have played all their cards")
                self._state = Round.State.DONE
                self._game.round_finished()
            else:
                # Round is not complete, wait for next trick before
                # reinitializing, so that Players can see the last
                # card put down
                self._state = Round.State.BETWEEN_TRICKS
                self._init_new_trick(self._trick_winner)

    def card_allowed(self, card: Card, hand: List[Card]) -> bool:
        """Tell whether a card may be put on the table."""
        if self._state == Round.State.BETWEEN_TRICKS:
            # between tricks, _current_trick is actually the trick
            # that ended, so pass explicitly an empty table:
            return card_allowed(card, hand=hand, table=[])
        elif self._state == Round.State.PLAYING:
            return card_allowed(card, hand=hand, table=self._current_trick)
        else:
            return False

    def _init_new_trick(self, first_player: int) -> None:
        self._current_player = first_player
        self._first_card = None
        self._trick_winner = None
        self._trick_winner_card = None

    def place_bid(self, player: Player, bid: int) -> None:
        """Call from player to notify that she placed a bid."""
        self._ensure_state(Round.State.BIDDING)
        self._ensure_current_player(player, "bid")
        self._current_player += 1
        if self._current_player >= len(self._players):
            self._current_player = 0
            self._state = Round.State.PLAYING

    def _ensure_state(self, desired_state):
        if hasattr(desired_state, '__iter__'):
            if all(s != self._state for s in desired_state):
                raise IllegalStateError(
                    f"Round is in {self._state}, not one of {desired_state}")
        elif self._state != desired_state:
            raise IllegalStateError(
                f"Round is in {self._state}, not in {desired_state}")

    def _ensure_current_player(self, player, operation):
        if player is not self.current_player:
            raise OutOfTurnError(operation,
                                 current_player=self.current_player,
                                 offending_player=player)

    def deal_cards(self, how_many_cards):
        """Shuffle cards and tell each player what cards he has."""
        cards = list(range(MAX_CARDS))
        random.shuffle(cards)
        for (i, p) in enumerate(self._players):
            p.accept_cards(
                self, cards[(i * how_many_cards):((i + 1) * how_many_cards)])
        trump_idx = how_many_cards * len(self._players)
        self._trump = None if trump_idx >= MAX_CARDS else cards[trump_idx]

    @property
    def trump(self) -> Optional[Card]:
        """Return trump card."""
        return self._trump
