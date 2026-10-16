

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional


def money(amount) -> Decimal:
    """Return an exact Decimal with 2 decimal places, round-half-up."""
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SusuError(Exception):
    """Any rule violation raises this."""



# Data classes

@dataclass
class Member:
    member_id: str
    name: str
    join_order: int
    payments: Dict[int, Decimal] = field(default_factory=dict)  # week -> paid

    def paid(self, week: int) -> Decimal:
        return self.payments.get(week, money(0))


@dataclass
class Payout:
    week: int
    member_id: str
    member_name: str
    amount: Decimal



#  group logic

class SusuGroup:
    def __init__(self, weekly_contribution):
        self.weekly_contribution = money(weekly_contribution)
        if self.weekly_contribution <= 0:
            raise SusuError("Weekly contribution must be positive.")
        self.current_week: int = 1
        self.members: Dict[str, Member] = {}
        self.payout_history: List[Payout] = []
        self._join_counter: int = 0

    # membership 
    def add_member(self, member_id: str, name: str = "") -> Member:
        member_id = member_id.strip()
        if not member_id:
            raise SusuError("Member ID cannot be empty.")
        if member_id in self.members:
            raise SusuError(f"Member '{member_id}' already exists.")
        # Assumption 1: no joining once the group has started paying out.
        if self.payout_history or self.current_week > 1:
            raise SusuError(
                "Cannot add members after the group has started paying out."
            )
        self._join_counter += 1
        m = Member(member_id=member_id, name=name or member_id,
                   join_order=self._join_counter)
        self.members[member_id] = m
        return m

    def _members_in_order(self) -> List[Member]:
        return sorted(self.members.values(), key=lambda m: m.join_order)

    # contributions 
    def record_contribution(self, member_id: str, amount) -> Decimal:
        """Record a contribution for the CURRENT week. Returns the new total."""
        if member_id not in self.members:
            raise SusuError(f"Unknown member '{member_id}'.")
        amt = money(amount)
        if amt <= 0:
            raise SusuError("Contribution must be greater than zero.")

        m = self.members[member_id]
        already = m.paid(self.current_week)
        owed = self.weekly_contribution - already
        if owed <= 0:
            raise SusuError(
                f"{m.name} has already paid in full for week {self.current_week}."
            )
        if amt > owed:
            raise SusuError(
                f"Payment of {amt} exceeds amount owed ({owed}) "
                f"for week {self.current_week}."
            )
        m.payments[self.current_week] = already + amt
        return m.payments[self.current_week]

    #  closing a week 
    def next_recipient(self) -> Member:
        paid_ids = {p.member_id for p in self.payout_history}
        for m in self._members_in_order():
            if m.member_id not in paid_ids:
                return m
        raise SusuError("Every member has already received a payout.")

    def close_week(self) -> dict:
        """Try to close the current week.

        Returns either:
          {"closed": False, "week": w, "unpaid": [(member, owed), ...]}
        or
          {"closed": True,  "week": w, "recipient": member, "amount": pot}
        """
        if not self.members:
            raise SusuError("Cannot close a week with no members.")
        if len(self.payout_history) >= len(self.members):
            raise SusuError("Group is complete; every member has been paid.")

        unpaid = []
        for m in self._members_in_order():
            owed = self.weekly_contribution - m.paid(self.current_week)
            if owed > 0:
                unpaid.append((m, owed))

        if unpaid:
            return {"closed": False, "week": self.current_week, "unpaid": unpaid}

        recipient = self.next_recipient()
        pot = self.weekly_contribution * len(self.members)
        closed_week = self.current_week
        self.payout_history.append(
            Payout(closed_week, recipient.member_id, recipient.name, pot)
        )
        self.current_week += 1
        return {"closed": True, "week": closed_week,
                "recipient": recipient, "amount": pot}

    #  report 
    def report(self) -> dict:
        paid_full, owing = [], []
        for m in self._members_in_order():
            paid = m.paid(self.current_week)
            owed = self.weekly_contribution - paid
            if owed > 0:
                owing.append((m, paid, owed))
            else:
                paid_full.append((m, paid))
        return {
            "weekly_contribution": self.weekly_contribution,
            "current_week": self.current_week,
            "paid_full": paid_full,
            "owing": owing,
            "payouts": list(self.payout_history),
            "complete": (len(self.members) > 0
                         and len(self.payout_history) == len(self.members)),
        }


def _ask(prompt: str, default: str = "") -> str:
    v = input(prompt).strip()
    return v if v else default


def run_cli():
    print("=== Susu Group Manager ===")
    while True:
        try:
            weekly = money(input("Weekly contribution (GHS): ").strip())
            if weekly <= 0:
                print("Must be positive.")
                continue
            break
        except Exception:
            print("Invalid amount.")

    group = SusuGroup(weekly)

    menu = """
--- Menu ---
1. Add member
2. Record contribution
3. Close week
4. Report
0. Quit
"""
    while True:
        print(menu)
        choice = _ask("Choice: ")

        if choice == "1":
            mid = _ask("Member ID: ")
            name = _ask("Name (optional): ")
            try:
                m = group.add_member(mid, name)
                print(f"Added {m.name} (join order #{m.join_order}).")
            except SusuError as e:
                print(f"Error: {e}")

        elif choice == "2":
            mid = _ask("Member ID: ")
            try:
                amt = money(_ask("Amount: "))
                total = group.record_contribution(mid, amt)
                print(f"Recorded. {mid} total for week "
                      f"{group.current_week}: {total}")
            except SusuError as e:
                print(f"Error: {e}")
            except Exception:
                print("Invalid amount.")

        elif choice == "3":
            try:
                res = group.close_week()
            except SusuError as e:
                print(f"Error: {e}")
                continue
            if res["closed"]:
                print(f"Week {res['week']} closed. Pot of {res['amount']} "
                      f"paid to {res['recipient'].name} "
                      f"({res['recipient'].member_id}).")
            else:
                print(f"Week {res['week']} NOT closed. Outstanding balances:")
                for m, owed in res["unpaid"]:
                    print(f"  - {m.name} ({m.member_id}) owes {owed}")

        elif choice == "4":
            r = group.report()
            print(f"\nWeekly contribution: {r['weekly_contribution']}")
            print(f"Current week: {r['current_week']}")
            if r["complete"]:
                print("Group is COMPLETE (all members paid out).")
            print("\nPaid in full this week:")
            print("  (none)" if not r["paid_full"] else "")
            for m, paid in r["paid_full"]:
                print(f"  - {m.name} ({m.member_id}): {paid}")
            print("\nOwing this week:")
            print("  (none)" if not r["owing"] else "")
            for m, paid, owed in r["owing"]:
                print(f"  - {m.name} ({m.member_id}): paid {paid}, owes {owed}")
            print("\nPayout history:")
            print("  (none)" if not r["payouts"] else "")
            for p in r["payouts"]:
                print(f"  - Week {p.week}: {p.member_name} "
                      f"({p.member_id}) received {p.amount}")

        elif choice == "0":
            print("Bye.")
            return
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    run_cli()