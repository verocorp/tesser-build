"""A minimal product-catalog domain whose only job is to exercise the two
value-object shapes the running arc never needs: a compound value object with
a multiple-representation field (Money, backed by ``decimal.Decimal`` — 1.5 and
1.50 are the same value) and a collection value object that wraps a mapping
(Labels). A Product entity holds a SKU (simple value object), a Price, and
Labels, so those value objects have a domain-meaningful home rather than
standing alone as "value-object theater".

Simple value objects, entities, aggregates, services, repositories, and the
composition root are exercised by the running arc (examples/python at the
package root); this package deliberately stays small and adds only the VO
shapes that arc leaves uncovered.
"""
