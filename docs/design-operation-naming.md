# Operation naming, outcomes, and the words that cross a boundary

<!-- tb-status: design — ruled 2026-09-13, not yet enacted in code, skill, or analyzer -->

This records the conventions settled in the ubiquitous-language review of
`examples/durable-execution` on 2026-09-13. It is a design note: nothing here
is enforced yet, and the last section says which layer would carry each rule.
The review walked one path, `POST /purchases`, top to bottom, and read every
name as the sentence it forms. The names that survived that test are the
conventions; the path is kept at the end as the worked example.

The frame the review used is `skills/tesser-build/strategic-design.md`: a
type, method, or field is named for the domain concept, never for the
technology or the pattern; one term has one meaning; one concept has one
term. The calling-mode norm of 2026-09-06 (`start_` is asynchronous, `run_`
is synchronous, the verb goes on the caller's relay method, a handler carries
no verb, a response is named for what it is) is assumed throughout.

## Operations

1. **An operation is a verb and the thing it acts on.** `place_order`,
   `price_product`, `confirm_order`, `charge_payment_method`. A bare verb is
   not an operation name: `purchase` and `charge` both failed this test.
   Mechanically, an operation name has at least two segments. Semantically,
   the verb is verb-only where the compound could read as a noun phrase
   (`purchase_order` is a procurement document; `price_order` reads three
   ways), and the object is the business thing, never its key (`product`,
   not `sku`).

2. **An orchestrator's method is an operation.** It is never `run`: `run`
   says nothing about what the act is, an orchestrator may carry several
   operations that a pattern word could never name, and `run` is the caller's
   calling-mode word. `OrderOrchestrator.confirm_order`, not
   `OrderOrchestrator.run`.

3. **Across a relay, one operation, one name.** The relay method, the runner
   that implements it, the runtime handler, and the orchestrator or action
   method it invokes are one operation seen from four places, so they carry
   one name. Across the client the rule does not hold: the client is a
   published language, decoupled from what runs behind it, and chooses the
   caller's word. That the customer's `pay_for_order` and the workflow's
   `pay_for_order` coincide is a fact about this domain, not a rule.

4. **The calling-mode verb lives on the relay protocol and its runners.**
   `start_<operation>` accepts and returns; `run_<operation>` waits. The
   operation after the prefix exists on the far side under that name. A
   runner carries the verb because it implements the relay and has the same
   signatures. The runtime never does: its handlers are the receiving end.

5. **A runtime handler is the operation, and the runtime exposes it as
   `<operation>_handler`.** The nested function carries the operation's name
   because that is the name the SDK registers (`OrderActions/price_product`,
   `OrderOrchestrator/confirm_order`). The attribute the runtime exposes is
   that name plus `_handler`, derived and not chosen, because the attribute
   is the SDK's decorated function, engine-specific, and a bare
   `price_product` on a runtime would read as the application method it
   forwards to. Two workflows in one runtime are two differently named
   functions; nothing is aliased to a name it did not carry. A handler is
   invoked only by the engine. Our code references it for its name.

## Messages and outcomes

6. **Request, response, and outcome derive from the operation.**
   `<Operation>Request`, `<Operation>Response`, `<Operation>Outcome`, and
   `Start<Operation>Response` with `Start<Operation>Outcome` for the
   accept-and-return crossing. No message is named for a class
   (`OrderOrchestratorRequest`), a calling mode (`RunResponse`), or a
   pattern.

7. **An expected alternative from a dependency is an outcome member on the
   response, matched with `assert_never`.** It is never an exception. A port
   or relay declares no errors.

8. **An outcome member reads as a sentence after the act.** "Confirming the
   order: confirmed, the product price was not found, already started." A
   member is one way the act can end that the caller acts on differently. Two
   members the caller handles identically are one member, and their
   difference is data on the response. The kinds seen so far, a catalog and
   not a closed set: the act done, sometimes in more than one way
   (`Taken.TAKEN / HELD`); the step or reason it stopped; the answer to a
   question (`SlugAvailability.TAKEN / FREE`); and what the engine crossing
   added (`ALREADY_STARTED`). The last kind exists only on relay responses,
   because only a relay crosses an engine, and it is produced by the runner
   translating the engine's refusal, never by the orchestrator.

9. **An outcome names what the act itself observed one hop down.** A parent
   workflow names which of its own steps did not complete,
   `ORDER_NOT_CONFIRMED`, `PAYMENT_DECLINED`, never a reason from further
   down. The deeper reason travels as data on the response, so the caller
   can still be told, and the parent's enum stays closed over its own act:
   a new reason in `ConfirmOrderOutcome` does not touch
   `PayForOrderOutcome`. A parent that compensates keys on which step
   stopped, never why, so this is also the shape compensation needs.

10. **Outcome and state are different things.** An outcome is an act-noun
    with result members, matched once and never stored. A state is an
    attribute-noun with value members, stored on the object, and has no
    failure branch. `LinkState.ACTIVE / INACTIVE` is a state.
    `ConfirmOrderOutcome.CONFIRMED` is an outcome.

Where outcomes come from, by kind: a domain transition returns a
`ts.Outcome` (closed set, `enum.auto()`, matched once, never stored or
serialized). A port or relay response carries a plain `enum.Enum` with string
values as a field, because a response is data that crosses a boundary and a
relay response is snapshotted onto the wire. An orchestrator's response is a
relay response, so its outcome is the relay's. Services, actions, and clients
define none: a service matches outcomes and raises situations, an action
passes its port's outcome through on the relay response, and a client raises
situations.

## Vocabulary across roles

11. **One fact keeps one word from the port inward.** What changes by hop is
    the carrier's subject, so a member gains a prefix and never a new word:
    `GetProductPriceOutcome.NOT_FOUND` at the port becomes
    `ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND` one level up. "Not found"
    over "missing": a lookup can only report what it searched for, not what
    ought to exist, and "missing" is already a transport category in this
    tree (`client.Missing` is 404 wearing a class name).

12. **The ubiquitous language holds in the domain and the application; the
    client is its published form; an adapter translates.** An adapter speaks
    its backend's language (a dict answering `None`, Restate's
    `TerminalError` with a status, an ingress 409, HTTP's 404) and converts
    it into the application's at the port or relay the application declared,
    in both directions. No backend word crosses inward: nothing named for an
    engine, a status, or a transport category exists inward of an adapter.
    `ports/engine.py`, `client.Missing`, `client.Conflict`,
    `client.Unavailable`, and `ChargeDeclined` are that crossing, and go.

13. **The handler's exhaustive match over the client's declared situations
    is the one place a situation becomes a status.** The client declares its
    situations (`ERRORS`, pinned by the client test to every exception class
    in the module). The HTTP handler matches each to a response and closes on
    `assert_never`, so adding a situation fails every host's match loudly.
    The status is HTTP's category and only the HTTP handler knows HTTP; the
    CLI host maps the same situations to exit codes; a second host is a
    second mapping, never a change to the situation. The word never implies
    the status: `ProductPriceNotFound` is 422 on `POST /purchases`, where
    the body named an unknown product, and would be 404 on a `GET` for that
    product's price. The route decides. Everything else reaching the host is
    a fault and takes the host's catch-all to 500. Today each route repeats
    the match; that duplication is accepted and out of scope here.

## Errors

14. **Two classes only.** A *situation* is a business term the caller acts
    on, raised across the client (`OrderNotConfirmed`, `PaymentDeclined`,
    `ProductPriceNotFound`). A *fault* is anything no expert has a word for;
    it propagates untyped to the host's catch-all and is handled nowhere
    below the host. `Unavailable` at every hop was neither: it was the 503
    wearing a class name, saying the same nothing five times.

## The worked path: `POST /purchases`

Read top to bottom, each hop as the sentence it forms.

| Hop | Operation | Sentence |
|---|---|---|
| Client, service | `pay_for_order(PayForOrderRequest) -> PayForOrderResponse` | the customer pays for the order |
| Parent relay, runner | `run_pay_for_order`, `PayForOrderRequest` carrying the `Order` | the workflow pays for the order, and the caller waits |
| Parent handler | `pay_for_order`, exposed as `pay_for_order_handler`, registered `PurchaseOrchestrator/pay_for_order` | |
| Parent orchestrator | `PurchaseOrchestrator.pay_for_order(PayForOrderRequest) -> PayForOrderResponse` | paying for the order |
| Child relay, runner | `run_confirm_order` / `start_confirm_order`, `ConfirmOrderRequest` | confirm it first |
| Child handler | `confirm_order`, exposed as `confirm_order_handler`, registered `OrderOrchestrator/confirm_order` | |
| Child orchestrator | `OrderOrchestrator.confirm_order(ConfirmOrderRequest) -> ConfirmOrderResponse` | confirming the order |
| Action relay, action | `run_price_product`, `OrderActions.price_product` | price its product |
| Repository port | `ProductCatalogRepository.get_product_price` | get the product price from the catalog |
| Action relay, action | `run_take_payment`, `PurchaseActions.take_payment` | then take payment for the total |
| Payment port | `PaymentProcessor.charge_payment_method` | charge the payment method |

The outcomes, one per act, every member as a sentence:

- Paying for the order: paid, the order was not confirmed, the payment was
  declined, or already started.
  `PayForOrderOutcome.PAID / ORDER_NOT_CONFIRMED / PAYMENT_DECLINED / ALREADY_STARTED`
- Confirming the order: confirmed, the product price was not found, or
  already started.
  `ConfirmOrderOutcome.CONFIRMED / PRODUCT_PRICE_NOT_FOUND / ALREADY_STARTED`
- Starting to confirm the order: started, or already started.
  `StartConfirmOrderOutcome.STARTED / ALREADY_STARTED`
- Getting the product price: found, or not found.
  `GetProductPriceOutcome.FOUND / NOT_FOUND`
- Charging the payment method: charged, or declined.
  `ChargePaymentMethodOutcome.CHARGED / DECLINED`

The client raises situations rather than an outcome, so `pay_for_order` on
the client has none. `Purchase` stays as the aggregate, an order paid for,
the result of the act and not the act; `PurchaseService`,
`PurchaseOrchestrator`, and `PurchaseActions` stay named for that thing.

What this replaces, on the same path today: relay `run_purchase_orchestrator`
and `run_order_orchestrator`; handlers `run_purchase` (registered as `run`)
and `run`, aliased to `purchase_orchestrator_handler` and
`order_orchestrator_handler`; methods `PurchaseOrchestrator.run` and
`OrderOrchestrator.run`; messages `PurchaseOrchestratorRequest` and
`OrderOrchestratorRequest`; the client's bare `purchase`; the port's bare
`charge`; `Priced.FOUND / MISSING`; and the error chain
`EngineRejected` / `EngineMissing` / `EngineConflict` / `EngineUnavailable`
reconstructed from status codes in three runners, raised as `TerminalError`
in four handlers, and caught in eight `except` arms across two services.

## Names that were tried and why they failed

Kept so the next reader does not re-derive them.

- `price_order` and `PriceOrderOutcome.PRICED`: "price" and "order" are each
  a noun and a verb, so the compound reads as "price the order", "a price
  order", or "order by price", and the happy member restates the verb.
- `purchase_order`: a procurement document.
- `Priced.PRICED`, `Placed.SKU_UNPRICED`: an enum named after its happy
  member says nothing twice or contradicts itself.
- `OrderPricing` / `OrderPayment` as orchestrator classes with a fixed
  `run`: the act is a noun, but moving it to the class keeps `run` on the
  receiving end, which the calling-mode norm forbids.
- `settle_order` for the parent: no one in this domain settles an order; a
  word invented to give the seller's side its own term is rule 1's drift.
- `SKU_UNPRICED`: names a state of a key, and the reader must work out why
  that stops a payment.
- `PRODUCT_NOT_IN_CATALOG`: asserts more than the lookup knows; the narrower
  fact is that the price was not found.
- `PRODUCT_PRICE_NOT_FOUND` on the parent: the child's reason crossing up;
  the parent observed only that its step did not complete.
- `Unavailable` at every hop, `Missing`, `Conflict`: transport categories
  wearing class names.

## What carries each rule

Nothing here is enforced today. Which layer would carry each:

- **tessercheck** can carry the mechanical halves: an operation name has at
  least two segments (1); an orchestrator method is not `run` (2); the relay
  chain shares one operation name (3); a relay method is a calling-mode
  prefix plus an operation that exists on the far side, and a runtime
  handler is the bare operation exposed as `<operation>_handler` (4, 5);
  request, response, and outcome derive from the operation (6); a port or
  relay declares no errors (7); nothing inward of an adapter is named for an
  engine or a status (12, by placement).
- **The skill** carries the semantic halves: the verb test and the object
  test (1), the client's word being the caller's (3), the sentence test on
  every member (8), a parent naming its own step (9), outcome versus state
  (10), one word from the port inward (11), adapters as translators (12),
  the handler as the one translation to a status (13), situations and
  faults (14).

## Open, and Chris's to rule

- Whether "confirm" is the seller's word for what the child workflow does.
  Everything on the child leg derives from it. If it is not, the act still
  needs a verb-only word, because the sentence test leaves no compound built
  on "price" standing.
- `ChargePaymentMethodRequest` carries an order id and cents and no payment
  method. Either the message gains the payment method it charges, or the
  thing being charged is the order and the port is `charge_order`. A
  modelling gap the language found, not a naming choice.
- `NOT_FOUND` at the port changes the `FOUND / MISSING` convention used by
  at least three other examples' port enums (`CampaignLookup`, `Loaded`,
  `Priced`). A repo-wide rename in the same change, or a recorded exception.
- Whether the compensation scenario's reserved word, "checkout", and this
  act's seller side are the same act. Not touched here.
- `submit_order` and `place_order` are two client words for one act,
  differing only in whether the caller waits. The calling-mode norm chose
  them deliberately as the caller's words for what comes back; recorded, not
  reopened.
