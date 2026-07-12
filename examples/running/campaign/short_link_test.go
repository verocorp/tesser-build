package campaign

import "testing"

func validShortLinkSpec() ShortLinkSpec {
	return ShortLinkSpec{Slug: "spring-sale", TargetURL: "https://example.com/spring", Active: true}
}

func TestNewShortLink_Rejection(t *testing.T) {
	t.Run("invalid slug", func(t *testing.T) {
		spec := validShortLinkSpec()
		spec.Slug = "NOPE"
		if _, err := NewShortLink(spec); err == nil {
			t.Fatal("expected error for invalid slug")
		}
	})
	t.Run("invalid target url", func(t *testing.T) {
		spec := validShortLinkSpec()
		spec.TargetURL = "not-a-url"
		if _, err := NewShortLink(spec); err == nil {
			t.Fatal("expected error for invalid target url")
		}
	})
}

func TestNewShortLink_Accepts(t *testing.T) {
	link, err := NewShortLink(validShortLinkSpec())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !link.Active() {
		t.Error("a newly constructed short link with Active: true must be active")
	}
}

func TestShortLink_IdentitySemantics(t *testing.T) {
	a, _ := NewShortLink(validShortLinkSpec())
	sameSlugSpec := validShortLinkSpec()
	sameSlugSpec.TargetURL = "https://example.com/different"
	b, _ := NewShortLink(sameSlugSpec)

	if !a.Equal(b) {
		t.Error("short links with the same slug must be equal, regardless of other attributes")
	}

	differentSlugSpec := validShortLinkSpec()
	differentSlugSpec.Slug = "winter-sale"
	c, _ := NewShortLink(differentSlugSpec)

	if a.Equal(c) {
		t.Error("short links with different slugs must not be equal")
	}
}

func TestShortLink_Deactivate(t *testing.T) {
	link, _ := NewShortLink(validShortLinkSpec())

	if err := link.Deactivate(); err != nil {
		t.Fatalf("legal transition must not error: %v", err)
	}
	if link.Active() {
		t.Error("Deactivate must leave the link inactive")
	}

	if err := link.Deactivate(); err == nil {
		t.Fatal("deactivating an already-deactivated link must error")
	}
	if link.Active() {
		t.Error("the illegal transition must leave state unchanged (still inactive)")
	}
}
