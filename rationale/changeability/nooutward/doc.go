// Package nooutward is the changeability arm for decision 3: a domain object
// emits no non-domain representation; turning a domain object into a DTO is the
// application service's Respond step, not a method on the domain.
//
// Layout mirrors the real layering:
//   - domain/ — the pure domain; exposes value objects, never primitives; imports
//     nothing outward.
//   - pub/     — the public interface: the Client contract and its DTOs, dumb bags
//     of primitives (no methods, no constructors), importing nothing. response_v1
//     / response_v2 are the -tags repv2 outward-representation migration.
//   - app/     — the application service: Convert + Respond, the SINGLE mapping
//     site between DTO primitives and domain value objects.
//   - emit/    — the coupled (violation) domain: a domain object that emits its own
//     DTO via ToResponse().
//   - decoupled/consumerNN, coupled/fanout/consumerNN — the generated N-scaling
//     arms the contrast measures.
//
// The proof lives in contrast_test.go: a response-DTO reshape forces the decoupled
// arm (operates on domain value objects) 0 edits and the coupled arm (reaches the
// domain-emitted DTO) N. Scoring is predeclared in ../SCORING.md.
//
// Note there is deliberately NO import-cycle guard: a properly dumb DTO imports
// nothing, so a domain importing it is never a cycle — the rule is a convention
// the compiler does not enforce, and the changeability fan-out is what justifies
// it. See ../SCORING.md (decision 3) and adversary_provenance.md.
package nooutward

//go:generate go run ./internal/gen
