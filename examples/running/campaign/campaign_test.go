package campaign

import (
	"fmt"
	"reflect"
	"testing"
)

func testSlug(i int) string {
	return fmt.Sprintf("slug-%04d", i)
}

func validCampaignSpec() CampaignSpec {
	return CampaignSpec{
		ID:   "camp-1",
		Name: "Spring Sale",
		Links: []ShortLinkSpec{
			{Slug: "spring-sale", TargetURL: "https://example.com/spring", Active: true},
		},
	}
}

func TestNewCampaign_InvariantHolds(t *testing.T) {
	c, err := NewCampaign(validCampaignSpec())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(c.Links()) != 1 {
		t.Fatalf("expected 1 link, got %d", len(c.Links()))
	}
}

func TestNewCampaign_EmptyLinksAllowed(t *testing.T) {
	spec := CampaignSpec{ID: "camp-1", Name: "Empty Campaign"}
	c, err := NewCampaign(spec)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(c.Links()) != 0 {
		t.Fatalf("expected 0 links, got %d", len(c.Links()))
	}
}

func TestNewCampaign_RejectsDuplicateSlug(t *testing.T) {
	spec := validCampaignSpec()
	spec.Links = append(spec.Links, ShortLinkSpec{
		Slug: "spring-sale", TargetURL: "https://example.com/other", Active: true,
	})
	if _, err := NewCampaign(spec); err == nil {
		t.Fatal("expected error for duplicate slug within one campaign")
	}
}

func TestNewCampaign_RejectsOverCapacity(t *testing.T) {
	spec := CampaignSpec{ID: "camp-1", Name: "Big Campaign"}
	for i := 0; i < MaxShortLinksPerCampaign+1; i++ {
		spec.Links = append(spec.Links, ShortLinkSpec{
			Slug:      testSlug(i),
			TargetURL: "https://example.com",
			Active:    true,
		})
	}
	if _, err := NewCampaign(spec); err == nil {
		t.Fatal("expected error when exceeding the maximum short links per campaign")
	}
}

func TestCampaign_DefensiveCopy(t *testing.T) {
	c, _ := NewCampaign(validCampaignSpec())
	links := c.Links()
	links[0] = ShortLink{}

	if c.Links()[0].Slug() != MustNewSlug("spring-sale") {
		t.Error("mutating the returned slice must not affect the campaign")
	}
}

func TestCampaign_EqualityBlocked(t *testing.T) {
	if reflect.TypeOf(Campaign{}).Comparable() {
		t.Fatal("Campaign must be non-comparable; aggregates are never compared by value")
	}
}

func TestCampaign_AddShortLink(t *testing.T) {
	c, _ := NewCampaign(validCampaignSpec())

	if err := c.AddShortLink(ShortLinkSpec{Slug: "winter-sale", TargetURL: "https://example.com/winter"}); err != nil {
		t.Fatalf("legal AddShortLink must not error: %v", err)
	}
	if len(c.Links()) != 2 {
		t.Fatalf("expected 2 links after add, got %d", len(c.Links()))
	}

	if err := c.AddShortLink(ShortLinkSpec{Slug: "winter-sale", TargetURL: "https://example.com/other"}); err == nil {
		t.Fatal("expected error adding a duplicate slug")
	}
	if len(c.Links()) != 2 {
		t.Fatal("a rejected AddShortLink must not partially mutate the campaign")
	}
}

func TestCampaign_AddShortLink_RejectsOverCapacity(t *testing.T) {
	spec := CampaignSpec{ID: "camp-1", Name: "Big Campaign"}
	c, _ := NewCampaign(spec)
	for i := 0; i < MaxShortLinksPerCampaign; i++ {
		if err := c.AddShortLink(ShortLinkSpec{
			Slug:      testSlug(i),
			TargetURL: "https://example.com",
		}); err != nil {
			t.Fatalf("unexpected error filling campaign to capacity: %v", err)
		}
	}
	if err := c.AddShortLink(ShortLinkSpec{Slug: "one-too-many", TargetURL: "https://example.com"}); err == nil {
		t.Fatal("expected error adding a 26th short link")
	}
}

func TestCampaign_DeactivateShortLink(t *testing.T) {
	c, _ := NewCampaign(validCampaignSpec())

	if err := c.DeactivateShortLink(MustNewSlug("spring-sale")); err != nil {
		t.Fatalf("legal DeactivateShortLink must not error: %v", err)
	}
	if c.Links()[0].Active() {
		t.Error("the short link must be inactive after deactivation")
	}

	if err := c.DeactivateShortLink(MustNewSlug("spring-sale")); err == nil {
		t.Fatal("deactivating an already-deactivated link must error")
	}
}

func TestCampaign_DeactivateShortLink_NotFound(t *testing.T) {
	c, _ := NewCampaign(validCampaignSpec())
	if err := c.DeactivateShortLink(MustNewSlug("no-such-slug")); err == nil {
		t.Fatal("expected error deactivating a slug the campaign does not own")
	}
}
