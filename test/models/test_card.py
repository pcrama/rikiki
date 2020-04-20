import pytest

from app.models import (Card, beats, card_allowed, same_suit)


def test_same_suit__examples():
    assert same_suit(Card.Heart2, Card.HeartKing)
    assert same_suit(Card.Spade7, Card.Spade10)
    assert same_suit(Card.ClubQueen, Card.ClubJack)
    assert same_suit(Card.Diamond8, Card.Diamond9)
    assert not same_suit(Card.Heart5, Card.DiamondAce)
    assert not same_suit(Card.DiamondAce, Card.SpadeQueen)
    assert not same_suit(Card.ClubAce, Card.HeartAce)


def test_beats__no_trump_only_first_card_of_trick__examples():
    # Heart
    assert beats(Card.Heart3, Card.Heart2,
                 first_card_in_trick=Card.Heart2)
    assert not beats(Card.Heart2, Card.Heart3,
                     first_card_in_trick=Card.Heart2)
    assert beats(Card.HeartJack, Card.Heart10,
                 first_card_in_trick=Card.Heart2)
    assert not beats(Card.Heart10, Card.HeartJack,
                     first_card_in_trick=Card.Heart2)
    assert beats(Card.HeartQueen, Card.HeartJack,
                 first_card_in_trick=Card.Heart2)
    assert not beats(Card.HeartJack, Card.HeartQueen,
                     first_card_in_trick=Card.Heart2)
    assert beats(Card.HeartKing, Card.HeartQueen,
                 first_card_in_trick=Card.Heart2)
    assert not beats(Card.HeartQueen, Card.HeartKing,
                     first_card_in_trick=Card.Heart2)
    assert beats(Card.HeartAce, Card.HeartKing,
                 first_card_in_trick=Card.Heart2)
    assert not beats(Card.HeartKing, Card.HeartAce,
                     first_card_in_trick=Card.Heart2)
    # Diamond
    assert beats(Card.Diamond3, Card.Diamond2,
                 first_card_in_trick=Card.Diamond2)
    assert not beats(Card.Diamond2, Card.Diamond3,
                     first_card_in_trick=Card.Diamond2)
    assert beats(Card.DiamondJack, Card.Diamond10,
                 first_card_in_trick=Card.Diamond2)
    assert not beats(Card.Diamond10, Card.DiamondJack,
                     first_card_in_trick=Card.Diamond2)
    assert beats(Card.DiamondQueen, Card.DiamondJack,
                 first_card_in_trick=Card.Diamond2)
    assert not beats(Card.DiamondJack, Card.DiamondQueen,
                     first_card_in_trick=Card.Diamond2)
    assert beats(Card.DiamondKing, Card.DiamondQueen,
                 first_card_in_trick=Card.Diamond2)
    assert not beats(Card.DiamondQueen, Card.DiamondKing,
                     first_card_in_trick=Card.Diamond2)
    assert beats(Card.DiamondAce, Card.DiamondKing,
                 first_card_in_trick=Card.Diamond2)
    assert not beats(Card.DiamondKing, Card.DiamondAce,
                     first_card_in_trick=Card.Diamond2)
    # Club
    assert beats(Card.Club3, Card.Club2,
                 first_card_in_trick=Card.Club2)
    assert not beats(Card.Club2, Card.Club3,
                     first_card_in_trick=Card.Club2)
    assert beats(Card.ClubJack, Card.Club10,
                 first_card_in_trick=Card.Club2)
    assert not beats(Card.Club10, Card.ClubJack,
                     first_card_in_trick=Card.Club2)
    assert beats(Card.ClubQueen, Card.ClubJack,
                 first_card_in_trick=Card.Club2)
    assert not beats(Card.ClubJack, Card.ClubQueen,
                     first_card_in_trick=Card.Club2)
    assert beats(Card.ClubKing, Card.ClubQueen,
                 first_card_in_trick=Card.Club2)
    assert not beats(Card.ClubQueen, Card.ClubKing,
                     first_card_in_trick=Card.Club2)
    assert beats(Card.ClubAce, Card.ClubKing,
                 first_card_in_trick=Card.Club2)
    assert not beats(Card.ClubKing, Card.ClubAce,
                     first_card_in_trick=Card.Club2)
    # Spade
    assert beats(Card.Spade3, Card.Spade2,
                 first_card_in_trick=Card.Spade2)
    assert not beats(Card.Spade2, Card.Spade3,
                     first_card_in_trick=Card.Spade2)
    assert beats(Card.SpadeJack, Card.Spade10,
                 first_card_in_trick=Card.Spade2)
    assert not beats(Card.Spade10, Card.SpadeJack,
                     first_card_in_trick=Card.Spade2)
    assert beats(Card.SpadeQueen, Card.SpadeJack,
                 first_card_in_trick=Card.Spade2)
    assert not beats(Card.SpadeJack, Card.SpadeQueen,
                     first_card_in_trick=Card.Spade2)
    assert beats(Card.SpadeKing, Card.SpadeQueen,
                 first_card_in_trick=Card.Spade2)
    assert not beats(Card.SpadeQueen, Card.SpadeKing,
                     first_card_in_trick=Card.Spade2)
    assert beats(Card.SpadeAce, Card.SpadeKing,
                 first_card_in_trick=Card.Spade2)
    assert not beats(Card.SpadeKing, Card.SpadeAce,
                     first_card_in_trick=Card.Spade2)


def test_beats__no_trump_mixed_colors__examples():
    assert beats(Card.Heart2, Card.Diamond10, first_card_in_trick=Card.Heart2)
    assert not beats(Card.Diamond10, Card.Heart2,
                     first_card_in_trick=Card.Heart2)


def test_beats__trump__examples():
    assert beats(Card.Heart2, Card.DiamondAce,
                 first_card_in_trick=Card.DiamondJack, trump=Card.Heart5)
    assert beats(Card.SpadeAce, Card.SpadeQueen,
                 first_card_in_trick=Card.DiamondJack, trump=Card.Spade10)
    assert beats(Card.Heart6, Card.Heart5,
                 first_card_in_trick=Card.Club6, trump=Card.DiamondJack)


def test_card_allowed__examples():
    # Anything is allowed as first card on the table
    assert card_allowed(Card.Heart2,
                        hand=[Card.Heart2, Card.Diamond7, Card.SpadeAce],
                        table=[])
    # Must follow suit of first played card, with or without trump
    assert card_allowed(
        Card.Heart2,
        hand=[Card.Heart2, Card.Diamond7, Card.SpadeAce, Card.ClubAce],
        table=[Card.HeartQueen])
    assert not card_allowed(
        Card.Heart2,
        hand=[Card.Heart2, Card.Diamond7, Card.SpadeAce, Card.ClubAce],
        table=[Card.Diamond8])
    # If unable to follow suit of first card, anything is allowed
    hand = [Card.Diamond7, Card.SpadeAce, Card.ClubAce]
    for card in hand:
        assert card_allowed(
            card, hand=hand, table=[Card.HeartQueen])
