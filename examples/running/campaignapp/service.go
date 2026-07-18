// Package campaignapp is the application-service and repository seam for
// the link-campaign domain. CampaignService coordinates each use case
// (convert -> delegate -> persist -> respond) and holds no business logic
// of its own — every rule is enforced by the campaign package's Campaign
// aggregate and its owned ShortLink entities. CampaignRepository is the
// persistence boundary the domain depends on to load and save a Campaign.
//
// The service's methods speak the public linkcampaign package's DTOs
// directly (rather than a second, service-local set) — see client.go in
// linkcampaignimpl for why: it lets the impl's Client-satisfying struct
// embed this service with zero forwarding code, since every use case here
// maps 1:1 onto a linkcampaign.Client operation of the same name.
package campaignapp

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"

	"github.com/verocorp/tesser-build/examples/running/campaign"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

// CampaignRepository is the persistence boundary for the Campaign
// aggregate: whole aggregate in, reconstructed aggregate out. Defined here,
// in the application service's own package — the domain depends on this
// abstraction, never on a concrete store.
type CampaignRepository interface {
	Save(ctx context.Context, c campaign.Campaign) error
	Load(ctx context.Context, id campaign.CampaignID) (campaign.Campaign, error)
}

// CampaignService coordinates the link-campaign use cases.
type CampaignService struct {
	repo CampaignRepository
}

// NewCampaignService constructs a CampaignService. The repository is
// injected, never constructed inside.
func NewCampaignService(repo CampaignRepository) *CampaignService {
	return &CampaignService{repo: repo}
}

// CreateCampaign is the "create a new campaign" use case: it constructs a
// brand-new Campaign aggregate (including its initial set of short links)
// and persists it.
func (s *CampaignService) CreateCampaign(ctx context.Context, req linkcampaign.CreateCampaignRequest) (linkcampaign.CreateCampaignResponse, error) {
	spec := toCampaignSpec(req) // 1. Convert

	c, err := campaign.NewCampaign(spec) // 2. Delegate (construct)
	if err != nil {
		return linkcampaign.CreateCampaignResponse{}, fmt.Errorf("invalid campaign: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil { // 3. Persist (whole aggregate)
		return linkcampaign.CreateCampaignResponse{}, fmt.Errorf("persist campaign %s: %w", c.ID(), err)
	}

	return linkcampaign.CreateCampaignResponse{ // 4. Respond (domain -> DTO)
		CampaignID: c.ID().String(),
		Name:       c.Name().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

// AddShortLink is the "add a short link to an existing campaign" use case:
// it loads the campaign and calls its guarded AddShortLink transition.
func (s *CampaignService) AddShortLink(ctx context.Context, req linkcampaign.AddShortLinkRequest) (linkcampaign.AddShortLinkResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID) // 1. Convert
	if err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}

	c, err := s.repo.Load(ctx, id) // 2a. load …
	if err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}
	linkSpec := campaign.ShortLinkSpec{Slug: req.Slug, TargetURL: req.TargetURL}
	if err := c.AddShortLink(linkSpec); err != nil { // 2b. … guarded transition
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("add short link rejected: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil { // 3. Persist
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("persist campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.AddShortLinkResponse{ // 4. Respond
		CampaignID: c.ID().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

// DeactivateShortLink is the "deactivate a short link" use case: it loads
// the campaign and calls its guarded DeactivateShortLink transition.
func (s *CampaignService) DeactivateShortLink(ctx context.Context, req linkcampaign.DeactivateShortLinkRequest) (linkcampaign.DeactivateShortLinkResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID) // 1. Convert
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}
	slug, err := campaign.NewSlug(req.Slug)
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("invalid slug: %w", err)
	}

	c, err := s.repo.Load(ctx, id) // 2a. load …
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}
	if err := c.DeactivateShortLink(slug); err != nil { // 2b. … guarded transition
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("deactivate short link rejected: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil { // 3. Persist
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("persist campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.DeactivateShortLinkResponse{ // 4. Respond
		CampaignID: c.ID().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

// GetCampaign is the "fetch a campaign and its links for display" use
// case: a read-only load, no transition, no persist.
func (s *CampaignService) GetCampaign(ctx context.Context, req linkcampaign.GetCampaignRequest) (linkcampaign.GetCampaignResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID) // 1. Convert
	if err != nil {
		return linkcampaign.GetCampaignResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}

	c, err := s.repo.Load(ctx, id) // 2. Delegate (load; no transition)
	if err != nil {
		return linkcampaign.GetCampaignResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.GetCampaignResponse{ // 4. Respond
		CampaignID: c.ID().String(),
		Name:       c.Name().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

// toCampaignSpec converts the create-campaign request DTO into a
// campaign.CampaignSpec. Pure mapping — no rules — including generating a
// fresh campaign ID, since the request never supplies one.
func toCampaignSpec(req linkcampaign.CreateCampaignRequest) campaign.CampaignSpec {
	links := make([]campaign.ShortLinkSpec, len(req.Links))
	for i, l := range req.Links {
		links[i] = campaign.ShortLinkSpec{Slug: l.Slug, TargetURL: l.TargetURL, Active: true}
	}
	return campaign.CampaignSpec{
		ID:    newCampaignIDValue(),
		Name:  req.Name,
		Links: links,
	}
}

// toShortLinkViews maps the aggregate's owned short links to their
// response-DTO projection (the Respond step's field mapping, not a domain
// computation — no sum/filter/group).
func toShortLinkViews(links []campaign.ShortLink) []linkcampaign.ShortLinkView {
	views := make([]linkcampaign.ShortLinkView, len(links))
	for i, l := range links {
		views[i] = linkcampaign.ShortLinkView{
			Slug:      l.Slug().String(),
			TargetURL: l.TargetURL().String(),
			Active:    l.Active(),
		}
	}
	return views
}

// newCampaignIDValue generates a fresh campaign identifier. ID-generation
// strategy isn't covered by the skill; a random hex string is the simplest
// choice that fits its spirit — a stable, opaque identity assigned once,
// here at the Convert step, before the aggregate is constructed.
func newCampaignIDValue() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
