# Followup report

- Observed UTC start: 2026-09-26T00:19:30.234Z
- Released at (UTC): 2026-09-26T00:19:20.832Z
- Observed UTC end: 2026-09-26T00:19:48.662Z
- Edits: in `candidate/application.py`, transfers and purchases now require source funds for amount plus 2, debit amount plus 2, and credit destination only by amount. Failed insufficient-funds operations return before changing balances.
- Verification: passed. Ran the required `python3 -B application.py` entry with balances, a successful transfer, a successful purchase, and an insufficient-funds transfer; outputs showed fees deducted, destination credited only by amount, and balances unchanged on failure.
- Controller intervention: none observed.
- Usage: unknown.
