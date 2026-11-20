# JurisFlow

Practice management for Kenyan law firms, built on Frappe and ERPNext.

JurisFlow is designed to protect a firm from three expensive mistakes (a missed date, a broken client-money rule, a missed tax or privacy duty) and to help it get paid for its work. It is a rules-driven system, not just a records database: deadlines, reminders and compliance checks are computed from data the firm controls and an advocate verifies.

> **Status: early development.** Parts are built and unit-tested; others are planned. Do not use it for live client work until a pilot firm has validated it and a qualified advocate has verified every deadline rule.

> **Professional responsibility.** JurisFlow flags and reminds. It does not give legal advice, and the advocate remains responsible for every date, filing and trust-account duty.

## What it does

| Area | Purpose |
|---|---|
| Matters | Clients, matters, parties, tasks, stages, limitation dates |
| Diary | Courts, hearings, hearing reminders, confirmation and escalation |
| Deadlines | Statutory and procedural time limits computed from verified rules |
| Compliance | Conflict-of-interest checks with ID and fuzzy name matching |
| Billing | Time entries, unbilled-time tracking, fee notes (in progress) |

Planned: client-money (trust) controls, WhatsApp and SMS, M-Pesa collection, KRA eTIMS invoicing, document templates, a client portal, and a firm-wide risk dashboard.

## Project status

| Module | State |
|---|---|
| JF Matters | Built |
| JF Diary (courts, hearings, hearing clock) | Built |
| JF Billing | Partly built |
| JF Compliance (conflict check) | Built |
| JF Deadlines | Built and unit-tested; Frappe integration still being validated |
| Matter-level access (confidential matters) | Not started |
| Trust accounting | Not started |
| WhatsApp / SMS, M-Pesa, eTIMS | Not started |
| Client portal, document automation | Not started |

"Unit-tested" means the pure calculation and configuration logic has automated tests. It does not yet mean the whole app is proven on a live site.

## Architecture

- Frappe 16 and ERPNext 16. ERPNext is intended to be the accounting engine.
- One codebase, one site per firm. Firm-specific behaviour lives in settings and master data, never in forked code.
- Rules as data. Deadline rules, reminder offsets, holiday lists, vacation periods and the permission matrix are editable records or config files, not constants in code.
- No hard deletes on matters, hearings, courts, deadline rules, trigger events or computed deadlines. Records are cancelled, deactivated or superseded.

```
jurisflow/
  engines/      pure Python rules, no database, unit-tested
  services/     transactions that use engines and the database
  jobs/         scheduled tasks (reminders, escalation)
  api/          whitelisted endpoints
  config/       permission matrix and deadline configuration (JSON)
  jf_*/         one folder per module (DocTypes and controllers)
  patches/      migrations
  tests/unit/   Frappe-free tests
```

## Deadline engine

1. A user records a Deadline Trigger Event against a matter.
2. The service finds active, verified Deadline Rules matching trigger type, practice area and court level.
3. For each rule it creates a Computed Deadline for the responsible advocate, with a snapshot of the rule values used.
4. A daily job sends reminders at each offset, escalates unassigned deadlines to partners, and marks overdue open deadlines as Missed.
5. If the trigger date is corrected, the old deadline becomes Superseded (not deleted) and a new one is computed.

Counting conventions are set per rule: calendar or court days, whether day one is the day after the trigger or the trigger day, whether court vacations count, and whether a non-working due date rolls forward or back.

Safety rules, enforced on the server and covered by tests:

- A rule cannot be activated without a named verifier and verification date.
- Only roles listed in JF Deadline Settings can verify a rule.
- Changing a verified rule's logic fields voids the verification and deactivates it.
- Overriding a computed date or waiving a deadline needs a written reason.
- Each deadline keeps a snapshot of the rule and calendar it was computed from.

This repository contains no real time limits. A qualified advocate must enter and verify each rule from the relevant statute and procedure rules before it goes live.

## Installation

Requires a Frappe bench on the `version-16` branch with ERPNext installed. The repository is private, so fetching it needs GitHub access (SSH key or token).

```bash
cd ~/frappe-bench
bench get-app https://github.com/Johnjuguna/JurisFlow.git --branch feature/jf-deadlines
bench new-site firm.example.com --install-app erpnext --install-app jurisflow
bench --site firm.example.com migrate
```

Back up before migrating any site that holds real data: `bench --site <site> backup`.

## Configuration

After installing, open JF Deadline Settings and set the Court Holiday List, the Court Vacation Periods, the roles allowed to verify rules (for example Advocate and Law Firm Partner), and the escalation window (default 14 days).

Roles created on migrate are listed in `jurisflow/config/deadline_config.json`. Per-DocType permissions are in `jurisflow/config/access_matrix.json`.

## Development

Unit tests need no Frappe site:

```bash
cd ~/frappe-bench/apps/jurisflow
python3 -m unittest discover -s jurisflow/tests/unit -t . -v
```

Conventions: write business rules as pure functions in `engines/` with tests first; do not hardcode firm-specific values, roles or periods; re-check invariants in DocType controllers; use a feature branch and run `migrate` on a scratch site before merging.

## Roadmap

1. Foundation: matter-level access, audit trail, scheduled backups, tested restore.
2. Court-day core: Court Day Pack, cause-list matcher, WhatsApp and SMS confirmation loop.
3. Billing and collection: fee notes, fee scales, M-Pesa, dunning, eTIMS.
4. Trust accounting: paired accounts, balance checks, maker-checker, accountant's compliance pack (accountant review required).
5. Client-facing: portal, importer, sample data, practice-area packs.
6. Insight: risk dashboard, fee-leakage detector, optional AI assists.

The order will change with what a pilot firm needs most.

## Licence

Proprietary. All rights reserved. See `license.txt`. No right to copy, resell, sublicense or reverse engineer is granted. The placeholder licence text is not a legal agreement: a Kenyan advocate should draft or review the real licence, data-processing agreement and support terms.

## Author

John Njuguna
