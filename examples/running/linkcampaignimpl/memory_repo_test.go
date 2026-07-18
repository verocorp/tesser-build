package linkcampaignimpl

import (
	"context"
	"testing"

	"github.com/verocorp/tesser-build/examples/running/campaign"
)

func TestInMemoryCampaignRepository_RoundTrip(t *testing.T) {
	repo := NewInMemoryCampaignRepository()
	ctx := context.Background()

	original, err := campaign.NewCampaign(campaign.CampaignSpec{
		ID:   "camp-1",
		Name: "Spring Sale",
		Links: []campaign.ShortLinkSpec{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring", Active: true},
		},
	})
	if err != nil {
		t.Fatalf("setup: unexpected error: %v", err)
	}

	if err := repo.Save(ctx, original); err != nil {
		t.Fatalf("Save: unexpected error: %v", err)
	}

	loaded, err := repo.Load(ctx, original.ID())
	if err != nil {
		t.Fatalf("Load: unexpected error: %v", err)
	}

	if loaded.ID() != original.ID() || loaded.Name() != original.Name() {
		t.Fatalf("loaded campaign does not match original: %+v vs %+v", loaded, original)
	}
	if len(loaded.Links()) != 1 || loaded.Links()[0].Slug() != original.Links()[0].Slug() {
		t.Fatalf("loaded links do not match original: %+v", loaded.Links())
	}
}

func TestInMemoryCampaignRepository_PreservesDeactivation(t *testing.T) {
	repo := NewInMemoryCampaignRepository()
	ctx := context.Background()

	c, _ := campaign.NewCampaign(campaign.CampaignSpec{
		ID:   "camp-1",
		Name: "Spring Sale",
		Links: []campaign.ShortLinkSpec{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring", Active: true},
		},
	})
	if err := c.DeactivateShortLink(campaign.MustNewSlug("spring-sale")); err != nil {
		t.Fatalf("setup: unexpected error: %v", err)
	}
	if err := repo.Save(ctx, c); err != nil {
		t.Fatalf("Save: unexpected error: %v", err)
	}

	loaded, err := repo.Load(ctx, c.ID())
	if err != nil {
		t.Fatalf("Load: unexpected error: %v", err)
	}
	if loaded.Links()[0].Active() {
		t.Error("reconstruction through the constructor must preserve a link's deactivated state")
	}
}

func TestInMemoryCampaignRepository_LoadNotFound(t *testing.T) {
	repo := NewInMemoryCampaignRepository()
	if _, err := repo.Load(context.Background(), campaign.MustNewCampaignID("does-not-exist")); err == nil {
		t.Fatal("expected error loading a campaign that was never saved")
	}
}
