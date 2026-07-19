package linkcampaignimpl

import (
	"context"
	"fmt"
	"sync"

	"github.com/verocorp/tesser-build/examples/running/campaign"
)

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

type InMemoryCampaignRepository struct {
	mu        sync.Mutex
	campaigns map[string]campaignRecord
}

func NewInMemoryCampaignRepository() *InMemoryCampaignRepository {
	return &InMemoryCampaignRepository{campaigns: make(map[string]campaignRecord)}
}

func (r *InMemoryCampaignRepository) Save(_ context.Context, c campaign.Campaign) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.campaigns[c.ID().String()] = decompose(c)
	return nil
}

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
