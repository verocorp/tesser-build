package campaign

import "fmt"

// ShortLink is the entity a Campaign owns: a slug mapped to a target URL,
// with a lifecycle (active -> deactivated). Its identity is its Slug: two
// short links with the same slug in the same campaign would be the same
// link, and the business rule that forbids duplicate slugs within a
// campaign is exactly the identity rule an entity earns (see
// entities.md: "a value object that wraps an ID has no identity of its
// own" — here Slug plays that role for ShortLink, the same way CustomerID
// identifies a Customer).
type ShortLink struct {
	slug      Slug
	targetURL TargetURL
	active    bool
}

// ShortLinkSpec carries construction data across the layer boundary:
// primitive leaves only. Active is included (rather than assumed true) so
// a repository can reconstruct a previously-deactivated link through this
// same constructor; application-service creation paths always pass true,
// since there is no use case for creating an already-deactivated link.
type ShortLinkSpec struct {
	Slug      string
	TargetURL string
	Active    bool
}

// NewShortLink validates and constructs a ShortLink. It builds each child
// value object via its own constructor and wraps the error with context; it
// re-validates nothing.
func NewShortLink(spec ShortLinkSpec) (ShortLink, error) {
	slug, err := NewSlug(spec.Slug)
	if err != nil {
		return ShortLink{}, fmt.Errorf("invalid slug: %w", err)
	}
	targetURL, err := NewTargetURL(spec.TargetURL)
	if err != nil {
		return ShortLink{}, fmt.Errorf("invalid target url: %w", err)
	}
	return ShortLink{slug: slug, targetURL: targetURL, active: spec.Active}, nil
}

func (s ShortLink) Slug() Slug           { return s.slug }
func (s ShortLink) TargetURL() TargetURL { return s.targetURL }
func (s ShortLink) Active() bool         { return s.active }

// Deactivate is the entity's guarded lifecycle transition: a link with a
// lifecycle (active -> deactivated), mutated in place, two states -> one
// guard clause. A short link can only be deactivated once.
func (s *ShortLink) Deactivate() error {
	if !s.active {
		return fmt.Errorf("short link %s is already deactivated", s.slug)
	}
	s.active = false
	return nil
}

// Equal compares ShortLink by identity (its slug) — never by attribute
// comparison and never by string form.
func (s ShortLink) Equal(other ShortLink) bool {
	return s.slug == other.slug
}
