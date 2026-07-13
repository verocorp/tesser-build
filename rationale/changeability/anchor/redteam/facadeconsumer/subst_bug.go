//go:build subst

// This file is EXCLUDED from normal builds (the subst tag is never set in
// production or in `go test ./...`). It models change C2 — "make this dependent
// unit-testable against a substitute" — for the FACADE arm.
//
// To test facadeconsumer.Reserve against a fake, you would need to pass a
// substitute into the facade. The facade (redteam/portless) exposes no such
// seam, so the line below does not compile:
//
//	go build -tags subst ./rationale/changeability/anchor/redteam/facadeconsumer  -> MUST fail.
//
// The compile error IS the forced edit: to gain substitutability you must add an
// injection API to portless (editing the boundary) or rewrite this consumer onto
// orders.Client. The decoupled consumers pay 0 here — they already receive the
// interface. See ../../SCORING.md change C2.
package facadeconsumer

import "github.com/verocorp/go-ddd/rationale/changeability/anchor/redteam/portless"

// portless.PlaceOrderWith does not exist: the facade has no injection seam.
var _ = portless.PlaceOrderWith
