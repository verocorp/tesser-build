package campaignapp

import (
	"context"
	"fmt"
	"testing"

	"github.com/verocorp/tesser-build/examples/running/campaign"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

type fakeCampaignRepository struct {
	campaigns map[string]campaign.Campaign
}

func newFakeCampaignRepository() *fakeCampaignRepository {
	return &fakeCampaignRepository{campaigns: make(map[string]campaign.Campaign)}
}

func (r *fakeCampaignRepository) Save(_ context.Context, c campaign.Campaign) error {
	r.campaigns[c.ID().String()] = c
	return nil
}

func (r *fakeCampaignRepository) Load(_ context.Context, id campaign.CampaignID) (campaign.Campaign, error) {
	c, ok := r.campaigns[id.String()]
	if !ok {
		return campaign.Campaign{}, fmt.Errorf("campaign %s not found", id)
	}
	return c, nil
}

func TestCampaignService_CreateCampaign(t *testing.T) {
	svc := NewCampaignService(newFakeCampaignRepository())

	resp, err := svc.CreateCampaign(context.Background(), linkcampaign.CreateCampaignRequest{
		Name: "Spring Sale",
		Links: []linkcampaign.ShortLinkInput{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring"},
		},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.CampaignID == "" {
		t.Fatal("expected a generated campaign id")
	}
	if resp.Name != "Spring Sale" {
		t.Errorf("Name = %q, want %q", resp.Name, "Spring Sale")
	}
	if len(resp.Links) != 1 || resp.Links[0].Slug != "spring-sale" || !resp.Links[0].Active {
		t.Errorf("unexpected links in response: %+v", resp.Links)
	}
}

func TestCampaignService_CreateCampaign_RejectionPropagates(t *testing.T) {
	svc := NewCampaignService(newFakeCampaignRepository())

	_, err := svc.CreateCampaign(context.Background(), linkcampaign.CreateCampaignRequest{
		Name: "",
	})
	if err == nil {
		t.Fatal("expected the domain constructor's rejection to propagate")
	}
}

func TestCampaignService_AddShortLink(t *testing.T) {
	repo := newFakeCampaignRepository()
	svc := NewCampaignService(repo)

	created, err := svc.CreateCampaign(context.Background(), linkcampaign.CreateCampaignRequest{Name: "Spring Sale"})
	if err != nil {
		t.Fatalf("setup: unexpected error: %v", err)
	}

	resp, err := svc.AddShortLink(context.Background(), linkcampaign.AddShortLinkRequest{
		CampaignID: created.CampaignID,
		Slug:       "spring-sale",
		TargetURL:  "https://example.com/spring",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(resp.Links) != 1 {
		t.Fatalf("expected 1 link after add, got %d", len(resp.Links))
	}

	_, err = svc.AddShortLink(context.Background(), linkcampaign.AddShortLinkRequest{
		CampaignID: created.CampaignID,
		Slug:       "spring-sale",
		TargetURL:  "https://example.com/other",
	})
	if err == nil {
		t.Fatal("expected error adding a duplicate slug")
	}
}

func TestCampaignService_DeactivateShortLink(t *testing.T) {
	repo := newFakeCampaignRepository()
	svc := NewCampaignService(repo)

	created, err := svc.CreateCampaign(context.Background(), linkcampaign.CreateCampaignRequest{
		Name: "Spring Sale",
		Links: []linkcampaign.ShortLinkInput{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring"},
		},
	})
	if err != nil {
		t.Fatalf("setup: unexpected error: %v", err)
	}

	resp, err := svc.DeactivateShortLink(context.Background(), linkcampaign.DeactivateShortLinkRequest{
		CampaignID: created.CampaignID,
		Slug:       "spring-sale",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.Links[0].Active {
		t.Error("expected the short link to be inactive after deactivation")
	}

	if _, err := svc.DeactivateShortLink(context.Background(), linkcampaign.DeactivateShortLinkRequest{
		CampaignID: created.CampaignID,
		Slug:       "spring-sale",
	}); err == nil {
		t.Fatal("expected error deactivating an already-deactivated link")
	}
}

func TestCampaignService_GetCampaign(t *testing.T) {
	repo := newFakeCampaignRepository()
	svc := NewCampaignService(repo)

	created, err := svc.CreateCampaign(context.Background(), linkcampaign.CreateCampaignRequest{
		Name: "Spring Sale",
		Links: []linkcampaign.ShortLinkInput{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring"},
		},
	})
	if err != nil {
		t.Fatalf("setup: unexpected error: %v", err)
	}

	resp, err := svc.GetCampaign(context.Background(), linkcampaign.GetCampaignRequest{CampaignID: created.CampaignID})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if resp.CampaignID != created.CampaignID || resp.Name != "Spring Sale" || len(resp.Links) != 1 {
		t.Errorf("unexpected response: %+v", resp)
	}
}

func TestCampaignService_GetCampaign_NotFound(t *testing.T) {
	svc := NewCampaignService(newFakeCampaignRepository())

	_, err := svc.GetCampaign(context.Background(), linkcampaign.GetCampaignRequest{CampaignID: "does-not-exist"})
	if err == nil {
		t.Fatal("expected error fetching a campaign that does not exist")
	}
}
