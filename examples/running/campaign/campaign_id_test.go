package campaign

import "testing"

func TestNewCampaignID_Rejection(t *testing.T) {
	if _, err := NewCampaignID(""); err == nil {
		t.Fatal("NewCampaignID(\"\"): expected error, got nil")
	}
}

func TestNewCampaignID_Accepts(t *testing.T) {
	if _, err := NewCampaignID("abc123"); err != nil {
		t.Fatalf("NewCampaignID: unexpected error: %v", err)
	}
}

func TestMustNewCampaignID_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("MustNewCampaignID: expected panic on invalid input")
		}
	}()
	MustNewCampaignID("")
}

func TestCampaignID_Equality(t *testing.T) {
	a := MustNewCampaignID("abc123")
	b := MustNewCampaignID("abc123")
	c := MustNewCampaignID("xyz789")

	if a != b {
		t.Error("campaign IDs with the same value must be equal")
	}
	if a == c {
		t.Error("campaign IDs with different values must not be equal")
	}
}

func TestCampaignID_String(t *testing.T) {
	id := MustNewCampaignID("abc123")
	if id.String() != "abc123" {
		t.Errorf("String() = %q, want %q", id.String(), "abc123")
	}
}
