package campaign

import "fmt"

type ShortLink struct {
	slug      Slug
	targetURL TargetURL
	active    bool
}

type ShortLinkSpec struct {
	Slug      string
	TargetURL string
	Active    bool
}

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

func (s *ShortLink) Deactivate() error {
	if !s.active {
		return fmt.Errorf("short link %s is already deactivated", s.slug)
	}
	s.active = false
	return nil
}

func (s ShortLink) Equal(other ShortLink) bool {
	return s.slug == other.slug
}
