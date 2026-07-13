package ordersapp

import (
	"context"

	"github.com/verocorp/go-ddd/rationale/changeability/anchor/orders"
)

// service is the single implementation of orders.Client. The composition root
// returns it typed as orders.Client, so dependents depend on the interface.
type service struct{ repo Repository }

// New builds the service over a repository and returns it as orders.Client.
func New(repo Repository) orders.Client { return &service{repo: repo} }

func (s *service) PlaceOrder(ctx context.Context, req orders.PlaceOrderRequest) (orders.PlaceOrderResponse, error) {
	total := int64(len(req.SKUs)) * 100
	o, err := NewOrder(OrderSpec{ID: "ord-" + req.CustomerID, Total: total})
	if err != nil {
		return orders.PlaceOrderResponse{}, err
	}
	if err := s.repo.Save(ctx, o); err != nil {
		return orders.PlaceOrderResponse{}, err
	}
	return orders.PlaceOrderResponse{OrderID: o.ID(), Total: o.Total()}, nil
}

func (s *service) GetOrder(ctx context.Context, req orders.GetOrderRequest) (orders.GetOrderResponse, error) {
	o, err := s.repo.Get(ctx, req.OrderID)
	if err != nil {
		return orders.GetOrderResponse{}, err
	}
	return orders.GetOrderResponse{OrderID: o.ID(), Status: o.Status(), Total: o.Total()}, nil
}
