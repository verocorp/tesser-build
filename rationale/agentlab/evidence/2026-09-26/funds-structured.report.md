Preparation/release start observed UTC: 2026-09-26T00:19:20.832Z
Implementation start observed UTC: 2026-09-26T00:19:20.832Z
Implementation end observed UTC: 2026-09-26T00:20:06Z

Edited only `candidate/application.py`: the shared successful move path now requires source balance >= amount + 2 and debits amount + 2, while destination receives amount. Existing insufficient-funds behavior returns before changing either balance. Balances shape is unchanged.

Verification: passed focused executable checks for transfer with a sufficient balance (amount plus fee deducted, amount credited), insufficient purchase with balances unchanged, and exact-boundary success followed by insufficient purchase with balances unchanged.

Controller intervention: none observed. Usage: unknown.
