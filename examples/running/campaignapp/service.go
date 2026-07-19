package campaignapp

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"fmt"

	"github.com/verocorp/tesser-build/examples/running/campaign"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

type CampaignRepository interface {
	Save(ctx context.Context, c campaign.Campaign) error
	Load(ctx context.Context, id campaign.CampaignID) (campaign.Campaign, error)
}

type CampaignService struct {
	repo CampaignRepository
}

func NewCampaignService(repo CampaignRepository) *CampaignService {
	return &CampaignService{repo: repo}
}

func (s *CampaignService) CreateCampaign(ctx context.Context, req linkcampaign.CreateCampaignRequest) (linkcampaign.CreateCampaignResponse, error) {
	spec := toCampaignSpec(req)

	c, err := campaign.NewCampaign(spec)
	if err != nil {
		return linkcampaign.CreateCampaignResponse{}, fmt.Errorf("invalid campaign: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil {
		return linkcampaign.CreateCampaignResponse{}, fmt.Errorf("persist campaign %s: %w", c.ID(), err)
	}

	return linkcampaign.CreateCampaignResponse{
		CampaignID: c.ID().String(),
		Name:       c.Name().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

func (s *CampaignService) AddShortLink(ctx context.Context, req linkcampaign.AddShortLinkRequest) (linkcampaign.AddShortLinkResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID)
	if err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}

	c, err := s.repo.Load(ctx, id)
	if err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}
	linkSpec := campaign.ShortLinkSpec{Slug: req.Slug, TargetURL: req.TargetURL}
	if err := c.AddShortLink(linkSpec); err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("add short link rejected: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil {
		return linkcampaign.AddShortLinkResponse{}, fmt.Errorf("persist campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.AddShortLinkResponse{
		CampaignID: c.ID().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

func (s *CampaignService) DeactivateShortLink(ctx context.Context, req linkcampaign.DeactivateShortLinkRequest) (linkcampaign.DeactivateShortLinkResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID)
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}
	slug, err := campaign.NewSlug(req.Slug)
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("invalid slug: %w", err)
	}

	c, err := s.repo.Load(ctx, id)
	if err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}
	if err := c.DeactivateShortLink(slug); err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("deactivate short link rejected: %w", err)
	}

	if err := s.repo.Save(ctx, c); err != nil {
		return linkcampaign.DeactivateShortLinkResponse{}, fmt.Errorf("persist campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.DeactivateShortLinkResponse{
		CampaignID: c.ID().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

func (s *CampaignService) GetCampaign(ctx context.Context, req linkcampaign.GetCampaignRequest) (linkcampaign.GetCampaignResponse, error) {
	id, err := campaign.NewCampaignID(req.CampaignID)
	if err != nil {
		return linkcampaign.GetCampaignResponse{}, fmt.Errorf("invalid campaign id: %w", err)
	}

	c, err := s.repo.Load(ctx, id)
	if err != nil {
		return linkcampaign.GetCampaignResponse{}, fmt.Errorf("load campaign %s: %w", req.CampaignID, err)
	}

	return linkcampaign.GetCampaignResponse{
		CampaignID: c.ID().String(),
		Name:       c.Name().String(),
		Links:      toShortLinkViews(c.Links()),
	}, nil
}

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

func newCampaignIDValue() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
