# Model classes


class IllegalStateException(RuntimeError):
    """A model was asked to perform an illegal state transition"""
    pass


class Player:
    def __init__(self, provisional_name, secret_id):
        self._provisional_name = provisional_name
        self._secret_id = secret_id
        self._confirmed_name = None
        self._cards = []
        self._bid = None
        self._round = None

    @property
    def name(self):
        if self._confirmed_name is None:
            return self._provisional_name
        else:
            return self._confirmed_name

    @property
    def secret_id(self):
        return self._secret_id

    @property
    def is_confirmed(self):
        return self._confirmed_name is not None

    @property
    def has_bid(self):
        return self.is_confirmed and self._bid is not None

    @property
    def bid(self):
        return self._bid

    def place_bid(self, value):
        self._ensure_confirmed()
        self._ensure_has_cards()
        if 0 <= value <= len(self._cards):
            self._bid = value
        else:
            raise ValueError(
                f"{self} can't bid {value}: outside [0, {len(self._cards)}]")

    def __str__(self):
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

    def confirm(self, confirmed_name):
        if confirmed_name is None or confirmed_name.strip() == '':
            _confirmed_name = _provisional_name
        else:
            self._confirmed_name = confirmed_name

    def accept_cards(self, round_, cards):
        self._ensure_confirmed()
        if self._round is None or self._cards == []:
            self._round = round_
            self._cards = cards
        else:
            raise IllegalStateException(f"{self} can't change game round now")

    def _ensure_confirmed(self):
        if not self.is_confirmed:
            raise IllegalStateException(f"{self} not confirmed yet")

    def _ensure_has_cards(self):
        if (self._cards is None or self._cards == []
                or self._round is None):
            raise IllegalStateException(
                f"{self} has no cards or not in a round")

    def _ensure_has_bid(self):
        if self._bid is None:
            raise IllegalStateException(f"{self} has not placed his bid yet")

    def play_card(self, card):
        self._ensure_confirmed()
        self._ensure_has_cards()
        self._ensure_has_bid()
        self._cards.remove(card)
        self._round.play_card(self, card)
        return card


class Round:
    def __init__(self, confirmed_players):
        if all(p.is_confirmed for p in confirmed_players) and len(confirmed_players) > 0:
            self._players = confirmed_players
        else:
            raise ValueError(
                "Can't initialize round without confirmed players")
        self._current_player = 0

    @property
    def current_player(self):
        return self._players[self._current_player]

    def play_card(self, player, card):
        pass
