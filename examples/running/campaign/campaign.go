package campaign

import "fmt"

const MaxShortLinksPerCampaign = 25

type Campaign struct {
	id    CampaignID
	name  CampaignName
	links []ShortLink
	_     [0]func()
}

type CampaignSpec struct {
	ID    string
	Name  string
	Links []ShortLinkSpec
}

func NewCampaign(spec CampaignSpec) (Campaign, error) {
	id, err := NewCampaignID(spec.ID)
	if err != nil {
		return Campaign{}, fmt.Errorf("invalid campaign id: %w", err)
	}
	name, err := NewCampaignName(spec.Name)
	if err != nil {
		return Campaign{}, fmt.Errorf("invalid campaign name: %w", err)
	}

	var links []ShortLink
	for i, linkSpec := range spec.Links {
		link, err := NewShortLink(linkSpec)
		if err != nil {
			return Campaign{}, fmt.Errorf("invalid short link at index %d: %w", i, err)
		}
		links, err = appendShortLink(links, link)
		if err != nil {
			return Campaign{}, fmt.Errorf("short link at index %d: %w", i, err)
		}
	}

	return Campaign{id: id, name: name, links: links}, nil
}

func (c Campaign) ID() CampaignID     { return c.id }
func (c Campaign) Name() CampaignName { return c.name }

func (c Campaign) Links() []ShortLink {
	out := make([]ShortLink, len(c.links))
	copy(out, c.links)
	return out
}

func (c *Campaign) AddShortLink(spec ShortLinkSpec) error {
	spec.Active = true
	link, err := NewShortLink(spec)
	if err != nil {
		return fmt.Errorf("invalid short link: %w", err)
	}
	links, err := appendShortLink(c.links, link)
	if err != nil {
		return err
	}
	c.links = links
	return nil
}

func (c *Campaign) DeactivateShortLink(slug Slug) error {
	for i := range c.links {
		if c.links[i].Slug() == slug {
			return c.links[i].Deactivate()
		}
	}
	return fmt.Errorf("no short link with slug %s in campaign %s", slug, c.id)
}

func appendShortLink(links []ShortLink, link ShortLink) ([]ShortLink, error) {
	if len(links) >= MaxShortLinksPerCampaign {
		return nil, fmt.Errorf("campaign already holds the maximum of %d short links", MaxShortLinksPerCampaign)
	}
	for _, existing := range links {
		if existing.Slug() == link.Slug() {
			return nil, fmt.Errorf("duplicate slug %s in campaign", link.Slug())
		}
	}
	return append(links, link), nil
}
