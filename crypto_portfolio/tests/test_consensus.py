"""Unit tests for consensus agent intersection rule."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.consensus_agent import ConsensusAgent


def test_intersection_when_multiple():
    s1_buys = {"BTC", "ETH", "SOL", "ADA"}
    s2_buys = {"BTC", "ETH", "DOT"}
    s1_sells = {"DOGE", "SHIB"}
    s2_sells = {"DOGE", "XRP"}

    buys, sells = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
    assert "BTC" in buys
    assert "ETH" in buys
    # Intersection of sells has only DOGE (size=1) → fall back to union
    assert "DOGE" in sells
    assert "SHIB" in sells
    assert "XRP" in sells


def test_union_when_intersection_empty():
    s1_buys = {"BTC"}
    s2_buys = {"ETH"}
    s1_sells = set()
    s2_sells = set()
    buys, sells = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
    # Intersection is empty → use union
    assert "BTC" in buys
    assert "ETH" in buys


def test_conflict_removal():
    s1_buys = {"BTC", "ETH"}
    s2_buys = {"BTC", "ETH"}
    s1_sells = {"BTC"}
    s2_sells = {"BTC"}
    buys, sells = ConsensusAgent._consensus_rule(s1_buys, s2_buys, s1_sells, s2_sells)
    # BTC is in both → should be excluded from both
    assert "BTC" not in buys
    assert "BTC" not in sells
    assert "ETH" in buys
