"""Tests for ConsensusAgent._consensus_rule."""

import pytest

from agents.consensus_agent import ConsensusAgent


class TestConsensusRule:

    def test_intersection_when_multiple(self):
        s1_buys  = {"A", "B", "C"}
        s2_buys  = {"B", "C", "D"}
        s1_sells = {"E", "F"}
        s2_sells = {"F", "G"}
        buy_set, sell_set = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
        # Intersection has 2 elements -> use intersection
        assert buy_set == {"B", "C"}
        assert sell_set == {"F"}

    def test_union_fallback_single_intersection(self):
        s1_buys  = {"A", "B"}
        s2_buys  = {"B", "C"}
        # Intersection = {"B"} (1 element) -> use union
        s1_sells = {"D"}
        s2_sells = {"E"}
        buy_set, sell_set = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
        assert buy_set == {"A", "B", "C"}

    def test_union_fallback_empty_intersection(self):
        s1_buys  = {"A"}
        s2_buys  = {"B"}
        s1_sells = set()
        s2_sells = set()
        buy_set, sell_set = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
        assert buy_set == {"A", "B"}

    def test_conflict_removal(self):
        """Caller removes conflicts; test that consensus_rule itself doesn't remove them."""
        s1_buys  = {"A", "B"}
        s2_buys  = {"A", "C"}
        s1_sells = {"A", "D"}
        s2_sells = {"A", "E"}
        buy_set, sell_set = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
        # "A" is in both -> conflict present in raw output
        assert "A" in buy_set
        assert "A" in sell_set

    def test_empty_signals(self):
        buy_set, sell_set = ConsensusAgent._consensus_rule(set(), set(), set(), set())
        assert buy_set == set()
        assert sell_set == set()

    def test_no_overlap_sells(self):
        s1_sells = {"X"}
        s2_sells = {"Y"}
        _, sell_set = ConsensusAgent._consensus_rule(set(), set(), s1_sells, s2_sells)
        # intersection empty (0 elements) -> union
        assert sell_set == {"X", "Y"}
