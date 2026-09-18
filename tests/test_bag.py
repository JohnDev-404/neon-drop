"""Tests for the 7-bag randomizer."""

import random
from collections import Counter

from neon_drop.core.bag import Bag
from neon_drop.core.piece import PIECES


def test_first_seven_are_a_permutation() -> None:
    bag = Bag(random.Random(0))
    first_seven = [bag.next() for _ in range(7)]
    assert sorted(first_seven) == sorted(PIECES)


def test_two_bags_contain_each_piece_twice() -> None:
    bag = Bag(random.Random(1))
    fourteen = [bag.next() for _ in range(14)]
    assert Counter(fourteen) == {k: 2 for k in PIECES}


def test_peek_does_not_consume() -> None:
    bag = Bag(random.Random(2))
    peeked = bag.peek(5)
    drawn = [bag.next() for _ in range(5)]
    assert peeked == drawn


def test_deterministic_with_same_seed() -> None:
    a = Bag(random.Random(42))
    b = Bag(random.Random(42))
    assert [a.next() for _ in range(50)] == [b.next() for _ in range(50)]
