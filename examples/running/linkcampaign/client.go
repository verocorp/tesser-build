// Package linkcampaign is the public contract for the link-campaign
// component — the entire surface other code (an HTTP layer, another
// module) is meant to depend on. It declares the Client interface and its
// DTOs only; no behavior, no domain types cross this boundary. Callers
// depend on this package and never on the application-service, repository,
// or domain packages behind it, so those internals can be refactored
// freely as long as this contract holds.
package linkcampaign

import "context"

// Client is the entire public surface of the link-campaign component.
type Client interface {
	CreateCampaign(ctx context.Context, req CreateCampaignRequest) (CreateCampaignResponse, error)
	AddShortLink(ctx context.Context, req AddShortLinkRequest) (AddShortLinkResponse, error)
	DeactivateShortLink(ctx context.Context, req DeactivateShortLinkRequest) (DeactivateShortLinkResponse, error)
	GetCampaign(ctx context.Context, req GetCampaignRequest) (GetCampaignResponse, error)
}

// ShortLinkInput is the primitive-leaved shape of a short link supplied when
// creating a campaign.
type ShortLinkInput struct {
	Slug      string `json:"slug"`
	TargetURL string `json:"target_url"`
}

// ShortLinkView is the primitive-leaved shape of a short link returned to a
// caller — never a domain object.
type ShortLinkView struct {
	Slug      string `json:"slug"`
	TargetURL string `json:"target_url"`
	Active    bool   `json:"active"`
}

// CreateCampaignRequest is the "create a new campaign" use case's request:
// a name and an initial — possibly empty — set of short links.
type CreateCampaignRequest struct {
	Name  string           `json:"name"`
	Links []ShortLinkInput `json:"links"`
}

type CreateCampaignResponse struct {
	CampaignID string          `json:"campaign_id"`
	Name       string          `json:"name"`
	Links      []ShortLinkView `json:"links"`
}

// AddShortLinkRequest is the "add a short link to an existing campaign" use
// case's request.
type AddShortLinkRequest struct {
	CampaignID string `json:"campaign_id"`
	Slug       string `json:"slug"`
	TargetURL  string `json:"target_url"`
}

type AddShortLinkResponse struct {
	CampaignID string          `json:"campaign_id"`
	Links      []ShortLinkView `json:"links"`
}

// DeactivateShortLinkRequest is the "deactivate a short link" use case's
// request.
type DeactivateShortLinkRequest struct {
	CampaignID string `json:"campaign_id"`
	Slug       string `json:"slug"`
}

type DeactivateShortLinkResponse struct {
	CampaignID string          `json:"campaign_id"`
	Links      []ShortLinkView `json:"links"`
}

// GetCampaignRequest is the "fetch a campaign and its links for display"
// use case's request.
type GetCampaignRequest struct {
	CampaignID string `json:"campaign_id"`
}

type GetCampaignResponse struct {
	CampaignID string          `json:"campaign_id"`
	Name       string          `json:"name"`
	Links      []ShortLinkView `json:"links"`
}
