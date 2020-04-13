"""Model classes (the M in MVC)."""
import enum
import random
import typing


class IllegalStateException(RuntimeError):
    """A model was asked to perform an illegal state transition."""

    pass


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
            raise IllegalStateException(f"{self} can't change game round now")

    def _ensure_confirmed(self) -> None:
        if not self.is_confirmed:
            raise IllegalStateException(f"{self} not confirmed yet")

    def _ensure_has_cards(self) -> None:
        if (self._cards is None or self._cards == []
                or self._round is None):
            raise IllegalStateException(
                f"{self} has no cards or not in a round")

    def _ensure_has_bid(self) -> None:
        if self._bid is None:
            raise IllegalStateException(f"{self} has not placed his bid yet")

    def play_card(self, card):
        """Put a card down on the table."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        self._ensure_has_bid()
        self._cards.remove(card)
        self._round.play_card(self, card)
        return card


MAX_CARDS = 52
@enum.auto
class Card(enum.IntEnum):
    r"""Enumeration of all cards.

    (let ((counter 0))
      (dolist (suit '("Heart" "Diamond" "Club" "Spade"))
        (dolist (value '(2 3 4 5 6 7 8 9 10 "Jack" "Queen" "King" "Ace"))
          (insert (format "\n    %s%s = %d" suit value counter))
          (incf counter))))
    """

    Heart2 = 0
    Heart3 = 1
    Heart4 = 2
    Heart5 = 3
    Heart6 = 4
    Heart7 = 5
    Heart8 = 6
    Heart9 = 7
    Heart10 = 8
    HeartJack = 9
    HeartQueen = 10
    HeartKing = 11
    HeartAce = 12
    Diamond2 = 13
    Diamond3 = 14
    Diamond4 = 15
    Diamond5 = 16
    Diamond6 = 17
    Diamond7 = 18
    Diamond8 = 19
    Diamond9 = 20
    Diamond10 = 21
    DiamondJack = 22
    DiamondQueen = 23
    DiamondKing = 24
    DiamondAce = 25
    Club2 = 26
    Club3 = 27
    Club4 = 28
    Club5 = 29
    Club6 = 30
    Club7 = 31
    Club8 = 32
    Club9 = 33
    Club10 = 34
    ClubJack = 35
    ClubQueen = 36
    ClubKing = 37
    ClubAce = 38
    Spade2 = 39
    Spade3 = 40
    Spade4 = 41
    Spade5 = 42
    Spade6 = 43
    Spade7 = 44
    Spade8 = 45
    Spade9 = 46
    Spade10 = 47
    SpadeJack = 48
    SpadeQueen = 49
    SpadeKing = 50
    SpadeAce = 51


class Round:
    """A Round deals the cards, handles the bidding and playing process."""

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

    @property
    def current_player(self) -> Player:
        """Return Player whose turn it is."""
        return self._players[self._current_player]

    def play_card(self, player: Player, card) -> None:
        """Call from player to notify that she put a card down."""
        pass

    def place_bid(self, player: Player, bid: int) -> None:
        """Call from player to notify that she placed a bid."""
        pass

    def deal_cards(self, how_many_cards):
        """Shuffle cards and tell each player what cards he has."""
        cards = list(range(MAX_CARDS))
        random.shuffle(cards)
        for (i, p) in enumerate(self._players):
            p.accept_cards(
                self, cards[(i * how_many_cards):((i + 1) * how_many_cards)])
