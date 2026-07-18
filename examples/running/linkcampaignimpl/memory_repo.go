// Package linkcampaignimpl is the concrete link-campaign implementation: an
// in-memory campaignapp.CampaignRepository, and the struct that satisfies
// the public linkcampaign.Client by embedding the application service. This
// package is imported from exactly one place in this example — the
// composition root (main.go) — which is the only site that chooses it over
// some other implementation.
package linkcampaignimpl

import (
	"context"
	"fmt"
	"sync"

	"github.com/verocorp/tesser-build/examples/running/campaign"
)

// campaignRecord and linkRecord are storage rows: primitive leaves, shaped
// by persistence rather than the domain.
type campaignRecord struct {
	id    string
	name  string
	links []linkRecord
}

type linkRecord struct {
	slug      string
	targetURL string
	active    bool
}

// InMemoryCampaignRepository is an in-memory campaignapp.CampaignRepository
// — fine for tests and this runnable example. A database-backed repository
// would satisfy the same interface later; swapping it in is a one-line
// change at the composition root.
type InMemoryCampaignRepository struct {
	mu        sync.Mutex
	campaigns map[string]campaignRecord
}

// NewInMemoryCampaignRepository constructs an empty repository.
func NewInMemoryCampaignRepository() *InMemoryCampaignRepository {
	return &InMemoryCampaignRepository{campaigns: make(map[string]campaignRecord)}
}

// Save takes the whole aggregate and decomposes it into a storage row — the
// caller never extracts children itself.
func (r *InMemoryCampaignRepository) Save(_ context.Context, c campaign.Campaign) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.campaigns[c.ID().String()] = decompose(c)
	return nil
}

// Load reconstructs the aggregate through its constructor, so every
// invariant is re-established on the way out; a stored-but-invalid
// aggregate cannot come back to life.
func (r *InMemoryCampaignRepository) Load(_ context.Context, id campaign.CampaignID) (campaign.Campaign, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	rec, ok := r.campaigns[id.String()]
	if !ok {
		return campaign.Campaign{}, fmt.Errorf("campaign %s not found", id)
	}
	return campaign.NewCampaign(rec.toSpec())
}

func decompose(c campaign.Campaign) campaignRecord {
	links := c.Links()
	linkRecs := make([]linkRecord, len(links))
	for i, l := range links {
		linkRecs[i] = linkRecord{slug: l.Slug().String(), targetURL: l.TargetURL().String(), active: l.Active()}
	}
	return campaignRecord{id: c.ID().String(), name: c.Name().String(), links: linkRecs}
}

func (rec campaignRecord) toSpec() campaign.CampaignSpec {
	links := make([]campaign.ShortLinkSpec, len(rec.links))
	for i, l := range rec.links {
		links[i] = campaign.ShortLinkSpec{Slug: l.slug, TargetURL: l.targetURL, Active: l.active}
	}
	return campaign.CampaignSpec{ID: rec.id, Name: rec.name, Links: links}
}
