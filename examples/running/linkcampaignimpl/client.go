package linkcampaignimpl

import (
	"github.com/verocorp/go-ddd/examples/running/campaignapp"
	"github.com/verocorp/go-ddd/examples/running/linkcampaign"
)

// client embeds *campaignapp.CampaignService, which promotes its methods
// so client satisfies linkcampaign.Client with zero forwarding code: every
// CampaignService method already takes and returns the public package's
// DTOs, and every use case here maps 1:1 onto a Client operation of the
// same name.
type client struct {
	*campaignapp.CampaignService
}

// Compile-time proof the contract is met — fails to build if a signature
// drifts.
var _ linkcampaign.Client = (*client)(nil)

// NewClient composes svc behind the public linkcampaign.Client.
func NewClient(svc *campaignapp.CampaignService) linkcampaign.Client {
	return &client{CampaignService: svc}
}
