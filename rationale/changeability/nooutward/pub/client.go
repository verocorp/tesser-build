// Package pub is the PUBLIC INTERFACE of the maneuver component: the Client
// contract and the DTOs that cross it. The DTOs are dumb bags of primitives —
// no methods, no constructors — and this package imports NOTHING (it is a leaf).
// Clients send and receive these DTOs; the application service (package app)
// converts them to and from domain objects. The domain never sees them.
//
// See ../../SCORING.md (decision 3).
package pub

import "context"

// Client is the public contract. It speaks DTOs, never domain objects.
type Client interface {
	DescribeManeuver(ctx context.Context, req DescribeManeuverRequest) (ManeuverResponse, error)
}

// DescribeManeuverRequest is a request DTO: a dumb bag of primitives.
type DescribeManeuverRequest struct {
	ManeuverID string
}

// ManeuverResponse is the response DTO. Its shape is the OUTWARD representation
// that migrates: see response_v1.go (BurnSeconds) and response_v2.go
// (DurationMillis), switched by -tags repv2. It has no methods and no constructor;
// the application service assembles it in its Respond step.
