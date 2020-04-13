"""Model classes (the M in MVC)."""
import enum
import random
import typing


class ModelError(RuntimeError):
    """Super class for all exceptions thrown by the models."""

    pass


class IllegalStateError(ModelError):
    """A model was asked to perform an illegal state transition."""

    pass


class OutOfTurnError(ModelError):
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


class Player:
    """Participant in the game."""

    def __init__(self, provisional_name: str, secret_id: str):
        """Initialize a new Player."""
        _ensure_non_blank(provisional_name, name="provisional_name")
        _ensure_non_blank(secret_id, name="secret_id")
        self._provisional_name = provisional_name
        """The display name of the Player as proposed by the Organizer."""
        self._secret_id = secret_id
        """A random string, will be used to authenticate the link."""
        self._confirmed_name = None
        """The name the Player chose for himself."""
        self._cards = []
        """The Player's hand"""
        self._bid = None
        """The Player's bid: how much tricks does she believe she will make in
a Round."""
        self._round = None
        """Reference to the Round the Player is currently participating in."""

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
        return self._secret_id

    @property
    def is_confirmed(self) -> bool:
        """Flag if Player already confirmed her name, i.e. joined the game."""
        return self._confirmed_name is not None

    @property
    def has_bid(self) -> bool:
        """Flag if Player has placed a bid in the current Round."""
        return self.is_confirmed and self._bid is not None

    @property
    def bid(self) -> typing.Optional[int]:
        """Return how many tricks the Player believes she is going to win."""
        return self._bid

    def place_bid(self, value: int) -> None:
        """Announce how many tricks the Player believes she is going to win."""
        self._ensure_confirmed()
        self._ensure_has_cards()
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

    def accept_cards(
            self,
            round_: typing.ForwardRef("Round"),
            cards: typing.List[int]
    ) -> None:
        """Accept the cards that the Round has dealt."""
        self._ensure_confirmed()
        if self._round is None or self._cards == []:
            self._round = round_
            self._cards = cards
        else:
            raise IllegalStateError(f"{self} can't change game round now")

    def _ensure_confirmed(self) -> None:
        if not self.is_confirmed:
            raise IllegalStateError(f"{self} not confirmed yet")

    def _ensure_has_cards(self) -> None:
        if (self._cards is None or self._cards == []
                or self._round is None):
            raise IllegalStateError(
                f"{self} has no cards or not in a round")

    def _ensure_has_bid(self) -> None:
        if self._bid is None:
            raise IllegalStateError(f"{self} has not placed his bid yet")

    def play_card(self, card):
        """Put a card down on the table."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        self._ensure_has_bid()
        self._cards.remove(card)
        self._round.play_card(self, card)
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


def beats(card1: Card,
          card2: Card,
          first_card_in_trick: Card,
          trump: typing.Optional[Card] = None) -> bool:
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
    class State(enum.Enum):
        """States of a Round."""

        BIDDING = enum.auto()
        PLAYING = enum.auto()
        DONE = enum.auto()

    def __init__(self,
                 confirmed_players: typing.List[Player],
                 how_many_cards: int):
        """Create new instance with confirmed participating Players."""
        if (len(confirmed_players) > 1
                and all(p.is_confirmed for p in confirmed_players)):
            self._players = confirmed_players
        else:
            raise ValueError(
                "Can't create Round without at least 2 players, all confirmed")
        if (how_many_cards > 0
                and (how_many_cards * len(confirmed_players)) < MAX_CARDS):
            self.deal_cards(how_many_cards)
        else:
            raise ValueError("how_many_cards must be > 0")
        self._current_player = 0
        self._current_trick = []
        self._state = Round.State.BIDDING

    @property
    def current_player(self) -> Player:
        """Return Player whose turn it is."""
        return self._players[self._current_player]

    def play_card(self, player: Player, card) -> None:
        """Call from player to notify that she put a card down."""
        pass

    def place_bid(self, player: Player, bid: int) -> None:
        """Call from player to notify that she placed a bid."""
        self._ensure_state(Round.State.BIDDING)
        self._ensure_current_player(player, "bid")
        self._current_player += 1
        if self._current_player >= len(self._players):
            self._current_player = 0
            self._state = Round.State.PLAYING

    def _ensure_state(self, desired_state):
        if self._state != desired_state:
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
