"""Model classes (the M in MVC)."""


class IllegalStateException(RuntimeError):
    """A model was asked to perform an illegal state transition."""

    pass


class Player:
    """Participant in the game."""

    def __init__(self, provisional_name: str, secret_id: str):
        """Initialize a new Player."""
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
        """Flag if Player has already confirmed his name, i.e. joined the game."""
        return self._confirmed_name is not None

    @property
    def has_bid(self) -> bool:
        """Flag if Player has placed a bid in the current Round."""
        return self.is_confirmed and self._bid is not None

    @property
    def bid(self):
        """Return how many tricks the Player believes she is going to win."""
        return self._bid

    def place_bid(self, value: int) -> None:
        """Announce how many tricks the Player believes she is going to win."""
        self._ensure_confirmed()
        self._ensure_has_cards()
        if 0 <= value <= len(self._cards):
            self._bid = value
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
        """Confirm invitation to play by confirming or updating the display name."""
        if confirmed_name is None or confirmed_name.strip() == '':
            _confirmed_name = _provisional_name
        else:
            self._confirmed_name = confirmed_name

    def accept_cards(self, round_, cards) -> None:
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


class Round:
    def __init__(self, confirmed_players):

        """Initialize a new instance with confirmed participating Players."""
        if all(p.is_confirmed for p in confirmed_players) and len(confirmed_players) > 0:
            self._players = confirmed_players
        else:
            raise ValueError(
                "Can't initialize round without confirmed players")
        self._current_player = 0

    @property
    def current_player(self) -> Player:
        """Return Player whose turn it is."""
        return self._players[self._current_player]

    def play_card(self, player: Player, card) -> None:
        """Call from player to notify that she put a card down."""
        pass
