package linkcampaignimpl

import (
	"context"
	"testing"

	"github.com/verocorp/tesser-build/examples/running/campaignapp"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

func TestNewClient_WiresEndToEnd(t *testing.T) {
	repo := NewInMemoryCampaignRepository()
	svc := campaignapp.NewCampaignService(repo)
	client := NewClient(svc)
	ctx := context.Background()

	created, err := client.CreateCampaign(ctx, linkcampaign.CreateCampaignRequest{Name: "Spring Sale"})
	if err != nil {
		t.Fatalf("CreateCampaign: unexpected error: %v", err)
	}

	fetched, err := client.GetCampaign(ctx, linkcampaign.GetCampaignRequest{CampaignID: created.CampaignID})
	if err != nil {
		t.Fatalf("GetCampaign: unexpected error: %v", err)
	}
	if fetched.Name != "Spring Sale" {
		t.Errorf("Name = %q, want %q", fetched.Name, "Spring Sale")
	}
}
