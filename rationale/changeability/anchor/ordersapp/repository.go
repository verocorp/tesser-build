package ordersapp

import "context"

// Repository is the persistence port. It takes and returns DOMAIN objects
// (Order), never backend rows — the rule the decision-4 arms probe, and the
// reason a backend adapter can be swapped without the service or its callers
// noticing. Package backend implements it.
type Repository interface {
	Save(ctx context.Context, o Order) error
	Get(ctx context.Context, id string) (Order, error)
}
