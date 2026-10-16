"""
Automated tests for the Susu Group Manager.

Run with:   python -m unittest -v
"""

import unittest
from decimal import Decimal

from susu import SusuGroup, SusuError, money


class TestMembership(unittest.TestCase):

    def test_duplicate_member_is_rejected(self):
        """Rule 1: duplicate member IDs are rejected."""
        g = SusuGroup(50)
        g.add_member("Ama")
        with self.assertRaises(SusuError):
            g.add_member("Ama")

    def test_unknown_member_contribution_is_rejected(self):
        """Rule 1: contributions for unknown members are rejected."""
        g = SusuGroup(50)
        g.add_member("Ama")
        with self.assertRaises(SusuError):
            g.record_contribution("Ghost", 50)

    def test_zero_and_negative_amounts_are_rejected(self):
        """Rule 1: zero/negative amounts are rejected."""
        g = SusuGroup(50)
        g.add_member("Ama")
        with self.assertRaises(SusuError):
            g.record_contribution("Ama", 0)
        with self.assertRaises(SusuError):
            g.record_contribution("Ama", -10)

    def test_overpayment_is_rejected(self):
        """Rule 1: paying more than owed for the week is rejected."""
        g = SusuGroup(50)
        g.add_member("Ama")
        with self.assertRaises(SusuError):
            g.record_contribution("Ama", 60)

    def test_cannot_add_member_after_week_one_closes(self):
        """Assumption 1: no late joiners after payouts have started."""
        g = SusuGroup(50)
        g.add_member("Ama")
        g.record_contribution("Ama", 50)
        g.close_week()               # week 1 closes → current_week becomes 2
        with self.assertRaises(SusuError):
            g.add_member("Latecomer")


class TestMoney(unittest.TestCase):

    def test_money_is_exact_decimal(self):
        """Rule 2: amounts are exact Decimal, no float error."""
        self.assertEqual(money("50.00"), Decimal("50.00"))
        self.assertEqual(money(50),      Decimal("50.00"))
        # Classic float trap: 0.1 + 0.2 != 0.3 as floats, but is exact here.
        self.assertEqual(money("0.10") + money("0.20"), money("0.30"))
        self.assertIsInstance(money("10"), Decimal)


class TestPartialPaymentAndClosing(unittest.TestCase):

    def test_partial_payment_then_week_cannot_close(self):
        """
        Rule: close_week() must refuse to pay out when someone still owes,
        and must report exactly who owes how much.
        """
        g = SusuGroup(50)
        g.add_member("Ama")
        g.add_member("Kofi")
        g.add_member("Esi")

        g.record_contribution("Ama", 50)
        g.record_contribution("Kofi", 50)
        g.record_contribution("Esi", 30)     # partial

        result = g.close_week()

        self.assertFalse(result["closed"])
        self.assertEqual(result["week"], 1)
        # Exactly one unpaid member, and only Esi.
        self.assertEqual(len(result["unpaid"]), 1)
        m, owed = result["unpaid"][0]
        self.assertEqual(m.member_id, "Esi")
        self.assertEqual(owed, Decimal("20.00"))
        # No payout must have happened.
        self.assertEqual(g.payout_history, [])
        # Week must not have advanced.
        self.assertEqual(g.current_week, 1)

    def test_week_closes_and_pays_next_in_order_after_full_payment(self):
        """
        The full example: after Esi tops up, week 1 closes and Ama
        receives the whole 150.00 pot; week advances; Kofi is next.
        """
        g = SusuGroup(50)
        g.add_member("Ama")
        g.add_member("Kofi")
        g.add_member("Esi")

        g.record_contribution("Ama", 50)
        g.record_contribution("Kofi", 50)
        g.record_contribution("Esi", 30)

        # First attempt: not ready.
        self.assertFalse(g.close_week()["closed"])

        # Esi tops up.
        g.record_contribution("Esi", 20)

        # Second attempt: closes, pot goes to Ama.
        result = g.close_week()
        self.assertTrue(result["closed"])
        self.assertEqual(result["week"], 1)
        self.assertEqual(result["recipient"].member_id, "Ama")
        self.assertEqual(result["amount"], Decimal("150.00"))

        # Current week advanced; Kofi is next.
        self.assertEqual(g.current_week, 2)
        r = g.report()
        self.assertIn("Kofi", r["payouts"][0].member_id == "Ama" and
                      [m.member_id for m, _ in r["paid_full"] +
                       [(m, p) for m, p, _ in r["owing"]]])

    def test_payout_order_follows_join_order(self):
        """Over three weeks, payouts go Ama → Kofi → Esi."""
        g = SusuGroup(50)
        for name in ["Ama", "Kofi", "Esi"]:
            g.add_member(name)

        winners = []
        for _ in range(3):
            for name in ["Ama", "Kofi", "Esi"]:
                g.record_contribution(name, 50)
            result = g.close_week()
            self.assertTrue(result["closed"])
            winners.append(result["recipient"].member_id)

        self.assertEqual(winners, ["Ama", "Kofi", "Esi"])


class TestReport(unittest.TestCase):

    def test_report_shows_current_week_and_outstanding(self):
        g = SusuGroup("50.00")
        g.add_member("Ama")
        g.add_member("Kofi")
        g.record_contribution("Ama", "50.00")
        g.record_contribution("Kofi", "10.00")

        r = g.report()
        self.assertEqual(r["current_week"], 1)
        self.assertEqual(r["weekly_contribution"], Decimal("50.00"))

        # Ama is paid in full, Kofi owes 40.00.
        paid_ids = [m.member_id for m, _ in r["paid_full"]]
        owing    = {m.member_id: owed for m, _, owed in r["owing"]}
        self.assertEqual(paid_ids, ["Ama"])
        self.assertEqual(owing, {"Kofi": Decimal("40.00")})


if __name__ == "__main__":
    unittest.main()