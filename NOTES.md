1. **No late joiners.** A member can only be added before week 1 has been
   closed (i.e. before any payout has happened). Once the group starts
   paying out, `add_member` raises an error.
   *Why:* allowing late joins would break the "one payout per member, in
   join order" invariant and make the historical pot arithmetic ambiguous
   (was the new member supposed to have contributed to past weeks?).

2. **Contributions apply to the current week only.** There is no back-pay
   or pre-pay. `record_contribution` always books against
   `self.current_week`.
   *Why:* keeps "who owes what for week N" unambiguous, and matches how a
   real susu meeting works — you settle this week's money this week.

3. **No overpayment.** A member may pay at most what they still owe for
   the current week.
   *Why:* the brief said to reject payments above what a member owes; I
   apply that strictly (no credit balance carried forward). Simpler and
   removes a whole class of accounting ambiguity.

4. **Empty or whitespace-only member IDs are rejected**, as are duplicate
   IDs. Member names are optional and default to the ID.

5. **Closing a week with no members, or after every member has already
   received a payout, is an error.** The group is considered "complete"
   once `len(payout_history) == len(members)`.

6. **Money is `Decimal` at all times.** Inputs are converted through a
   single helper, `money()`, which normalizes to 2 decimal places using
   `ROUND_HALF_UP`. No `float` ever touches an amount.

7. **Payout recipient is chosen by join order** (an internal counter
   assigned at `add_member` time), skipping members who have already been
   paid.

## Design decisions worth flagging

- **Library vs CLI split.** `susu.py` contains the classes
  (`SusuGroup`, `Member`, `Payout`, `SusuError`) *and* a `run_cli()`
  function. The CLI is only invoked under
  `if __name__ == "__main__":`, which is what lets `test_susu.py` import
  the module without launching the menu.
- **Errors vs return values.** Rule violations raise `SusuError`. A
  refused week-close is *not* an exception — it returns a dict with
  `closed=False` and a list of `(member, owed)` pairs. This is
  deliberate: "week cannot close yet" is a normal state, not a bug.
- **A single pot source of truth.** The pot is computed as
  `weekly_contribution * len(members)` at the moment of close. This
  guarantees the total paid out equals the total collected for that week,
  by construction.