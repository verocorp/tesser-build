package linkcampaignimpl

import (
	"github.com/verocorp/tesser-build/examples/running/campaignapp"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

type client struct {
	*campaignapp.CampaignService
}

var _ linkcampaign.Client = (*client)(nil)

func NewClient(svc *campaignapp.CampaignService) linkcampaign.Client {
	return &client{CampaignService: svc}
}
