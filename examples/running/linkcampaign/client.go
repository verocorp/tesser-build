package linkcampaign

import "context"

type Client interface {
	CreateCampaign(ctx context.Context, req CreateCampaignRequest) (CreateCampaignResponse, error)
	AddShortLink(ctx context.Context, req AddShortLinkRequest) (AddShortLinkResponse, error)
	DeactivateShortLink(ctx context.Context, req DeactivateShortLinkRequest) (DeactivateShortLinkResponse, error)
	GetCampaign(ctx context.Context, req GetCampaignRequest) (GetCampaignResponse, error)
}

type ShortLinkInput struct {
	Slug      string `json:"slug"`
	TargetURL string `json:"target_url"`
}

type ShortLinkView struct {
	Slug      string `json:"slug"`
	TargetURL string `json:"target_url"`
	Active    bool   `json:"active"`
}

type CreateCampaignRequest struct {
	Name  string           `json:"name"`
	Links []ShortLinkInput `json:"links"`
}

type CreateCampaignResponse struct {
	CampaignID string          `json:"campaign_id"`
	Name       string          `json:"name"`
	Links      []ShortLinkView `json:"links"`
}

type AddShortLinkRequest struct {
	CampaignID string `json:"campaign_id"`
	Slug       string `json:"slug"`
	TargetURL  string `json:"target_url"`
}

type AddShortLinkResponse struct {
	CampaignID string          `json:"campaign_id"`
	Links      []ShortLinkView `json:"links"`
}

type DeactivateShortLinkRequest struct {
	CampaignID string `json:"campaign_id"`
	Slug       string `json:"slug"`
}

type DeactivateShortLinkResponse struct {
	CampaignID string          `json:"campaign_id"`
	Links      []ShortLinkView `json:"links"`
}

type GetCampaignRequest struct {
	CampaignID string `json:"campaign_id"`
}

type GetCampaignResponse struct {
	CampaignID string          `json:"campaign_id"`
	Name       string          `json:"name"`
	Links      []ShortLinkView `json:"links"`
}
