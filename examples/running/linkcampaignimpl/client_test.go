package linkcampaignimpl

import (
	"context"
	"testing"

	"github.com/verocorp/go-ddd/examples/running/campaignapp"
	"github.com/verocorp/go-ddd/examples/running/linkcampaign"
)

// TestNewClient_WiresEndToEnd demonstrates the wiring point: a real
// CampaignService, composed behind the public linkcampaign.Client via
// NewClient, runs a real use case against the in-memory repository.
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
