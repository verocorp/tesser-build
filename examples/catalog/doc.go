// Package catalog is a minimal product-catalog domain whose only job is to
// exercise the two value-object shapes the other examples never need: a
// compound value object with a field that has multiple representations
// (Money, backed by *big.Rat — 1.5 and 1.50 are the same value but not the
// same pointer, so == lies and Equal is mandatory) and a collection value
// object that wraps a map (Labels — copied in and out so the backing map
// never escapes). A Product entity holds a SKU (simple value object), a
// Price, and Labels, giving those value objects a domain-meaningful home
// rather than standing alone as "value-object theater".
//
// Simple value objects, entities, and aggregates are exercised by the other
// examples (ddd, lending, running); this package deliberately stays small and
// adds only what those leave uncovered.
package catalog
