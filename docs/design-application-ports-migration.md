# Migrating the five example trees to application/ports

Measured, not estimated. Running the shipped ports checker over the existing
trees produces **136 findings**, and they fall into three mechanical shapes plus
one genuine modelling gap.

## The blast radius, by rule

| Tree | TB081 (port arity) | TB052 (kind placement) | TB060 (adapters→application) | Total |
|---|---|---|---|---|
| `python-app` | 50 | 14 | 5 | 69 |
| `llmport` | 34 | 5 | 2 | 41 |
| `spike-shells` | 8 | 3 | — | 11 |
| `errorspy` | 4 | 6 | 1 | 11 |
| `serdepy` | — | 1 | 1 | 2 |

- **TB081 (98)** — every port method signature. `save(parts: CampaignParts) -> None`
  becomes `save(SaveCampaignRequest) -> SaveCampaignResponse`.
- **TB052 (29)** — every `ts.Parts` class, now unclassified, moving to a ports
  module as `ts.Request` / `ts.Response`.
- **TB060 (9)** — every adapter importing `application.parts` or
  `application.service`, repointing at `application.ports.*`.

## The four unions and two bools

The only signatures that need a real modelling decision rather than a mechanical
rewrite:

| Site | Today | Becomes |
|---|---|---|
| `python-app` `CampaignRepository.find` | `FoundCampaign \| MissingCampaign` | `CampaignLookup` enum + payload |
| `python-app` `CampaignRepository.find_by_slug` | same | same |
| `errorspy` `CampaignRepository.find` | same | same |
| `llmport` `SlotDirectory.reserve` | `Reserved \| SlotTaken` | `ReservationOutcome` enum |
| `python-app` `CampaignRepository.slug_taken` | `-> bool` | `SlugAvailability` enum |
| `llmport` `BookingRepository.has` | `-> bool` | `BookingPresence` enum |

The two bool returns are where the "ban bare bool in a port DTO" question bites.
The repo already argues the position elsewhere — TB016 bans a bool inside a
value object, and `skills/tesser-build/domain-return.md` rule 5 says a public
predicate answer "is a concept, not a boolean". Applying it at the port boundary
is consistent, and it is mechanically decidable.

## The modelling gap: a record with no port

`serdepy` has no `ts.Port` anywhere. `parcel/application/parts.py` holds
`ParcelParts` plus a decompose walk, and `parcel/adapters/wire.py` imports the
record directly to build a payload.

Under the new rules that record has no home: a ports module must declare exactly
one port, and there is no port here to declare. Three ways out, in order of
honesty:

1. **Give the adapter its port.** `wire.py` is an outbound adapter; outbound
   adapters satisfy a port the context owns. The absence is a modelling gap the
   rules just exposed, not a rule defect. `ParcelWire` (or `ParcelPublisher`)
   with `to_payload(ParcelRecord) -> PayloadResponse` gives the record a home and
   makes the example conform to the doctrine it is supposed to demonstrate.
2. **Allow a records-only ports module.** Cheap, but it reopens the sharing hole
   the one-port-per-module rule closes structurally — two ports could then both
   import nothing yet both reference a shared records module... except they
   cannot, because the leaf rule forbids sibling imports. So a records-only
   module would be reachable by *nobody*, which makes it useless. Rejected on
   its own terms.
3. **Leave serdepy exempt.** Rejected: the repo has no ratchet and no
   code-family off switch.

Option 1 is the only coherent answer, and it is the one the rules are pushing
toward. That is the rules doing their job.
