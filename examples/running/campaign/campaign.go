package campaign

import "fmt"

// MaxShortLinksPerCampaign is the business rule capping how many short
// links one campaign may hold.
const MaxShortLinksPerCampaign = 25

// Campaign is the aggregate root: it owns a set of ShortLinks and enforces
// the invariants that span them — no two short links may share a slug,
// and a campaign holds at most MaxShortLinksPerCampaign links. It is the
// only entry point for adding or deactivating an owned short link; nothing
// outside the aggregate holds or mutates the collection directly.
//
// A campaign has a lifecycle (links are added and deactivated over time),
// so it is a mutable aggregate: root-guarded transitions re-establish the
// invariants after every change.
type Campaign struct {
	id    CampaignID
	name  CampaignName
	links []ShortLink
	_     [0]func() // non-comparable: aggregates are never compared by value
}

// CampaignSpec carries construction data across the layer boundary:
// primitive leaves only, nesting mirroring composition (Links holds nested
// ShortLinkSpecs).
type CampaignSpec struct {
	ID    string
	Name  string
	Links []ShortLinkSpec
}

// NewCampaign validates and constructs a Campaign, including its initial —
// possibly empty — set of short links. The cross-object invariants (unique
// slug, at-most-25 links) are enforced here, so an invalid Campaign is
// unrepresentable.
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

// Links returns a defensive copy — the caller can never mutate the
// campaign's owned collection.
func (c Campaign) Links() []ShortLink {
	out := make([]ShortLink, len(c.links))
	copy(out, c.links)
	return out
}

// AddShortLink is the root-guarded transition for the "add a short link to
// an existing campaign" use case: it re-establishes both cross-object
// invariants (unique slug, at-most-25 links) before the new link is
// admitted.
func (c *Campaign) AddShortLink(spec ShortLinkSpec) error {
	spec.Active = true // a newly added short link always starts active
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

// DeactivateShortLink is the root-guarded transition for the "deactivate a
// short link" use case: the root looks up the owned child by its slug and
// calls its guarded lifecycle method — callers never reach into the
// collection themselves.
func (c *Campaign) DeactivateShortLink(slug Slug) error {
	for i := range c.links {
		if c.links[i].Slug() == slug {
			return c.links[i].Deactivate()
		}
	}
	return fmt.Errorf("no short link with slug %s in campaign %s", slug, c.id)
}

// appendShortLink enforces the invariants that span the campaign's owned
// short links — no two links may share a slug, and a campaign holds at
// most MaxShortLinksPerCampaign links. Shared by the constructor and
// AddShortLink so the rule is enforced in exactly one place, never by
// callers.
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
