# Operation naming, outcomes, and the words that cross a boundary

<!-- tb-status: design — ruled 2026-09-13 with the four open questions settled the same day; not yet enacted in code, skill, or analyzer -->

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
   `OrderOrchestrator.run`. This is a 2026-09-13 ruling that extends the
   2026-09-06 norm: that norm took the verb off handlers and responses but
   its own scratch note still wrote `OrderOrchestrator.run`, so the ban on
   the orchestrator's method is new here, not something the norm stated.

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
   functions; nothing is aliased to a name it did not carry. In production
   a handler is invoked by the engine: the runners pass the decorated
   function to `workflow_call`, `workflow_send`, or `ctx.service_call`, and
   the SDK reads the service name, the handler name, and the serdes off it.
   Tests call the handlers directly, which the SDK's wrapper allows. An
   operation name is unique within its owner, not within the runtime: the
   engine registers `A/confirm_order` and `B/confirm_order` as two
   handlers, so where two owners on one runtime share an operation the
   attribute is qualified by the owner, `order_confirm_order_handler`.
   Otherwise `<operation>_handler` stands.

## Messages and outcomes

6. **Request, response, and outcome derive from the operation.**
   `<Operation>Request`, `<Operation>Response`, `<Operation>Outcome`, and
   `Start<Operation>Response` with `Start<Operation>Outcome` for the
   accept-and-return crossing. No message is named for a class
   (`OrderOrchestratorRequest`), a calling mode (`RunResponse`), or a
   pattern. The thing an operation hands back is a field on the response,
   and the record that pictures it is named for the thing and nothing
   else: `client.Campaign`, `client.Link`, `ports.Price`, `ports.Booking`.
   The domain's `Campaign` and the client's `Campaign` are one concept in
   two packages, told apart by the module alias at every use. There is no
   suffix: `View` was never ruled and `Record` was never ruled; both go.
   Where the outcome may leave the thing absent, the field is a tuple of
   zero or one. A response shared by several operations is the defect
   this rule removes: `CampaignView` answered four operations and
   `BookingStateResponse` answered five, and each becomes
   `<Operation>Response` holding a `Campaign` or a `Booking`.

7. **An expected alternative from a dependency is an outcome member on the
   response, matched with `assert_never`.** It is never an exception. A port
   or relay declares no errors. Every hop passes its dependency's outcome
   through on its own response, the action included: the catalog's
   `NOT_FOUND` rides `PriceProductOutcome.PRICE_NOT_FOUND` on the action's
   relay response before it reaches the orchestrator. A member is a final
   business fact, never a translated transient failure: a lost processor
   response is a fault that the engine retries with the same idempotency
   key, not `DECLINED`, because money may have moved. A change to an
   outcome set is a redeploy boundary, the same as a snapshot gaining a
   field: an in-flight journal replays the members it was written with.

8. **An outcome member reads as a sentence after the act.** "Confirming the
   order: confirmed, the product price was not found, already started." A
   member is one way the act can end that the caller acts on differently. A
   test that follows from that, proposed here and not yet ruled on: two
   members that mean the same thing to the dependency are one member, and
   their difference is data on the response. One caller branching the same
   way on two members is not the test: `ItemLookup.ARCHIVED / MISSING` are
   two catalog facts even where one reader answers both with an empty
   tuple. A field only some members can fill is a tuple of zero or one,
   `GetProductPriceResponse.prices`, so a response carries an outcome beside
   fields that are truthful for every member. The snapshot checks shape
   only, each element's shape included, and never the count against the
   outcome: a snapshot decides once (the 2026-09-11 ruling), and the
   consistency between two fields is the consumer's, whose happy arm reads
   the one record and faults on a payload that lacks it. Both ends of the
   wire are ours, so nothing is lost by refusing it one hop later. (The
   count-per-member check was an addition of mine under Codex's finding 4,
   never ruled, and it cost 59 markers in the enactment before Chris struck
   it on 2026-09-13.) The kinds seen so far, a catalog and
   not a closed set: the act done, sometimes in more than one way
   (`Taken.TAKEN / HELD`); the step or reason it stopped; the answer to a
   question (`SlugTakenOutcome.TAKEN / FREE`); and what the engine crossing
   added (`ALREADY_STARTED`). The last kind exists only on relay responses,
   because only a relay crosses an engine, and it is produced by the runner
   translating the engine's refusal, never by the orchestrator. It exists
   only on the `run_` path, and only where the runner can recognise the
   engine's specific refusal, the 409 whose body says the workflow was
   already invoked. Any other 409, a cancellation included, is a fault: the
   runner raises, and a member for cancellation waits for the compensation
   scenario to give it a meaning. The `start_` outcome is `STARTED` alone,
   because a repeat send is a 202 dedup on the server and the refusal is
   unobservable there (measured on restate-server 1.7.2, 2026-09-08). The
   member is the application's word for its own once-only rule, which the
   engine's key dedup merely enforces, so it belongs in the act's outcome
   and not in a response of the crossing's own (Chris, 2026-09-13). The
   runner produces it by constructing the relay response directly inside
   the except that recognised the refusal, with an empty reason, because a
   mapper maps from something and the runner has nothing to map from but
   the key it already reads, and because the engine's message text is not
   the application's word. Two implementations of one relay each write
   that construction, as two repositories each construct their port's
   response. The property that survives is precise: a runner never reads
   or names the payload, the order's fields, which cross only through the
   snapshot; constructing the relay's own response is the adapter
   fulfilling its protocol.

9. **An outcome names what the act itself observed one hop down.** A parent
   workflow names which of its own steps did not complete,
   `ORDER_NOT_CONFIRMED`, `PAYMENT_DECLINED`, never a reason from further
   down. This rule governs summarising, and rule 11 governs forwarding: a
   hop that passes the same fact on keeps its word, a parent reporting on
   its own step names the step. The worked chain does both, `NOT_FOUND` to
   `PRICE_NOT_FOUND` to `PRODUCT_PRICE_NOT_FOUND` forwarded through the
   action and the child, then `ORDER_NOT_CONFIRMED` summarised by the
   parent. The deeper reason travels as data on the response, so the caller
   can still be told, and the parent's enum stays closed over its own act:
   a new reason in `ConfirmOrderOutcome` does not touch
   `PayForOrderOutcome`. A hypothesis for the compensation scenario, not a
   ruling: a parent that undoes the steps that ran would key on which step
   stopped, which is the shape this naming gives it. The purchase today has
   no compensation, so that scenario is where it gets tested.

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
    `PriceProductOutcome.PRICE_NOT_FOUND` on the action's response and
    `ConfirmOrderOutcome.PRODUCT_PRICE_NOT_FOUND` on the child's. This is
    forwarding the same fact; a parent summarising its own step is rule 9,
    and the two never apply to the same hop. "Not found"
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
    product's price. The route decides. A malformed request is the host's
    own category, `protocol.BadRequest` to 400, decided before the client is
    reached. Everything else reaching the host is a fault and takes the
    host's catch-all to 500. Today each route repeats
    the match; that duplication is accepted and out of scope here.

## Errors

14. **Two classes only.** A *situation* is a business term the caller acts
    on, raised across the client (`OrderNotConfirmed`, `PaymentDeclined`,
    `ProductPriceNotFound`). A *fault* is anything no expert has a word for;
    it propagates untyped to the nearest host and is handled nowhere in
    domain or application code. `Unavailable` at every hop was neither: it
    was the 503 wearing a class name, saying the same nothing five times.

    There are two hosts, and each owns its own fault policy. The HTTP host's
    is `except Exception` to 500, because it answers a human now. The
    engine runtime is a host too: the engine invokes our handlers, and the
    SDK's policy for an exception that is not a `TerminalError` is retry
    from the journal. That is the right default for a transient fault and
    the wrong one forever for a permanent one, so the runtime's policy is a
    bounded `InvocationRetryPolicy` declared on its `Service` and
    `Workflow` objects, with `on_max_attempts` deciding pause or kill.
    Today the tree declares none, so the server's unbounded default applies
    and a permanent fault replays forever (README, the 4,298-digit
    quantity). The one place a handler raises `TerminalError` itself is the
    serde wrapper on a body that cannot be parsed, because that fails every
    replay and the SDK cannot know it. A synchronous runner that waits on
    the engine with no read timeout inherits the engine's policy on a
    connection to a human, so that wait is bounded or that door is
    asynchronous.

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
- Starting to confirm the order: started. A repeat send is deduplicated by
  the server, so there is no second member to observe.
  `StartConfirmOrderOutcome.STARTED`
- Pricing the product: priced, or the price was not found.
  `PriceProductOutcome.PRICED / PRICE_NOT_FOUND`
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
reconstructed from status codes in five runners (two from ingress HTTP
statuses, three from `TerminalError` statuses), raised as `TerminalError`
in four handlers, and caught in twelve `except` arms across two services.

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
  receiving end, which rule 2 rejects for the reasons given there.
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

Some of this is enforced today, and the line matters for scoping the
enactment. Already enforced: `TB084` requires a domain outcome's members to
be `enum.auto()`, forbids holding one on a field, and requires every match
on one to close on `assert_never` (the domain half of 8 and 10). `TB052`'s
placement keeps error declarations out of relay modules and puts
application errors in `application/ports/`, so the relay half of 7 holds by
placement, but ports themselves are allowed a `port_error` today, so the
port half of 7 is a reversal, not a gap. `TB081` checks that an operation
takes one `ts.Request` and returns one `ts.Response`, and `TB085` derives a
local's name from its class. Since 2026-09-14 `TB085` also carries the
single-declaration halves of 1, 2, and 6: on every client, port,
application client, and relay protocol method, an operation has at least
two segments, `start_` and `run_` appear only on a relay (where they are
required), and the request, response, and the response's `outcome` field
derive from the operation; on every public orchestrator method, the name is
not `run`, carries no calling-mode prefix, and has two segments. An
enum-typed field on an operation's own response is its outcome: there is at
most one, it is named `outcome`, and a data enum rides inside a record
rather than on the response (Chris, 2026-09-14; whether every response must
carry exactly one is an open follow-up). Which layer would carry the rest:

- **tessercheck** can carry the mechanical halves: an operation name has at
  least two segments (1); an orchestrator method is not `run` (2); the relay
  chain shares one operation name (3); a relay method is a calling-mode
  prefix plus an operation that exists on the far side, and a runtime
  handler is the bare operation exposed as `<operation>_handler` (4, 5);
  request, response, and outcome derive from the operation (6); a port or
  relay declares no errors (7); an SDK import or an error declaration
  inward of an adapter (12, by placement). Placement cannot judge
  vocabulary: whether a word is transport's or the domain's is review, and
  a lexical ban on "status" would flag scheduling's `StatusRequest`, which
  is about a booking. Proving the relay-to-handler chain needs the
  registration binding, including a decorator's `name=` override, which
  base-class classification does not see. Beyond naming checks, the
  outcome-on-response shape needs three analyzer changes: admit a plain
  enum in a relay module, where placement rejects it today; recognise a
  `match` on a response's outcome field the way `TB084` recognises one on a
  `ts.Outcome`, since a class named `*Outcome` activates nothing; and
  remove the `port_error` placement row rather than add a check. Where the
  match sits: a port outcome in the action's mapper (`MapToPriceSpec` is
  the precedent), a relay outcome in the orchestrator or the service. A
  service method has one match. An orchestrator has one match per relay
  it depends on, because a parent that runs a child and then takes payment
  branches on both, and the second cannot move into a mapper when its
  happy arm is a domain call (Chris, 2026-09-13, from the enactment).
- **The skill** carries the semantic halves: the verb test and the object
  test (1), the client's word being the caller's (3), the sentence test on
  every member (8), a parent naming its own step (9), outcome versus state
  (10), one word from the port inward (11), adapters as translators (12),
  the handler as the one translation to a status (13), situations and
  faults (14).

## Rulings, 2026-09-13

The four questions the review left open, and how Chris ruled on each.

- **"Confirm" is the seller's word for the child act.** `confirm_order`,
  `ConfirmOrderRequest`, `ConfirmOrderOutcome.CONFIRMED`, and the parent's
  `ORDER_NOT_CONFIRMED` stand.
- **The charge request gains a simple payment method object.** The language
  found that `ChargePaymentMethodRequest` carried an order id and cents and
  nothing to charge. The ruling is to add a simple `PaymentMethod` domain
  object and thread it from the client's `PayForOrderRequest` through the
  relay to the port, so the operation charges what its name says. Its shape
  is decided when it is built; the ruling is that it exists.
- **`FOUND / NOT_FOUND` everywhere, for now.** Every port enum that answers a
  lookup uses `NOT_FOUND`, so `CampaignLookup`, `Loaded`, and `Priced` are
  renamed in the same change as this tree, not recorded as exceptions.
- **"Checkout" is deferred to the compensation scenario.** The word is
  right for confirm plus take payment, and the decision whether the parent
  act is renamed to it waits until that scenario is built, because it is the
  scenario that will say whether compensation is this act extended or a new
  one. Until then the parent stays `pay_for_order`.

- **A record inside a response is named for the thing, with no suffix.**
  Asked how rule 6 handles a response several operations share, the
  inventory found eight `*View` classes across five trees (`CampaignView`
  in errorspy and python-app, `LinkView`, `VerdictView`, `LinkVerdictView`,
  `ItemView` twice in ports, `BookingView` in llmport) and four shared
  responses (`CampaignView` by four operations in two trees,
  `BookingStateResponse` by five, `FindCampaignResponse` by `find` and
  `find_by_slug`). Chris: "there is no View, there is no word, it's just
  the thing: Campaign, Link, etc." So the record is `Campaign`, `Link`,
  `Item`, `Booking`, `Verdict`, `Price`, in whichever package pictures it,
  and every operation derives its own response around it. `PriceRecord`
  goes the same way. `find` / `find_by_slug` sharing one response is an
  operation-naming question under rule 1, either one operation with two
  keys or two operations with two responses, and is left to enactment.

- **The rule 1 migration is in scope now.** The enactment counted 54
  protocol operation declarations across the eleven Python trees that are
  a bare verb or name a non-business object, `find`, `get`, `save`,
  `check`, `find_view`, and Codex counted 62 messages not derivable from an
  operation. Chris (2026-09-13): rename them as part of this work, verb and
  the thing, then derive their messages and outcomes. That is what
  retires `find_view`, `CampaignRow`, and `CampaignRowLookup`: a
  repository lookup and a read-side lookup of a campaign are two acts,
  `find_campaign` and `find_campaign_by_slug`, each with its own derived
  response and outcome, and the record inside is `Campaign`. A collision
  between two derived names inside one package is resolved by naming the
  acts apart, never by a suffix word.

- **A cancellation 409 is a fault, for now.** The SDK surfaces a cancelled
  invocation as `TerminalError("cancelled", 409)`, in the same shape as the
  already-invoked refusal, told apart only by the server's message text.
  Nothing in the tree cancels today, and what a cancelled purchase means
  for money already moved is the compensation scenario's question. So the
  runner recognises only the already-invoked refusal as `ALREADY_STARTED`
  and raises on any other 409; a member for cancellation is added when
  that scenario gives it a meaning, a redeploy boundary on one relay
  response.

- **Retry policy is set in the engine host and its runtime only, for now.**
  A retry policy encodes two kinds of knowledge: business facts the
  application owns (whether repeating an operation is safe, how long the
  caller may wait) and operational numbers the adapter owns (intervals,
  attempt count, pause or kill). The application could declare its half in
  engine-neutral terms on the relay, the way `start_`/`run_` already
  declare a crossing's waiting, and the runtime would translate. That is
  deferred until a use case needs it. Until then the runtime declares a
  bounded `InvocationRetryPolicy` per `Service` and `Workflow`, and the
  attempt bound and the synchronous runner's wait bound are adapter
  choices with no input from the use case, recorded as such rather than
  read as designed.

Recorded, not reopened: `submit_order` and `place_order` are two client
words for one act, differing only in whether the caller waits. The
calling-mode norm chose them deliberately as the caller's words for what
comes back.
