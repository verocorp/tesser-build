package campaign

import "testing"

func TestNewCampaignName_Rejection(t *testing.T) {
	cases := []string{"", "   "}
	for _, value := range cases {
		if _, err := NewCampaignName(value); err == nil {
			t.Fatalf("NewCampaignName(%q): expected error, got nil", value)
		}
	}
}

func TestNewCampaignName_Accepts(t *testing.T) {
	if _, err := NewCampaignName("Spring Sale"); err != nil {
		t.Fatalf("NewCampaignName: unexpected error: %v", err)
	}
}

func TestMustNewCampaignName_PanicsOnInvalid(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("MustNewCampaignName: expected panic on invalid input")
		}
	}()
	MustNewCampaignName("")
}

func TestCampaignName_Equality(t *testing.T) {
	a := MustNewCampaignName("Spring Sale")
	b := MustNewCampaignName("Spring Sale")
	c := MustNewCampaignName("Winter Sale")

	if a != b {
		t.Error("campaign names with the same value must be equal")
	}
	if a == c {
		t.Error("campaign names with different values must not be equal")
	}
}

func TestCampaignName_String(t *testing.T) {
	n := MustNewCampaignName("Spring Sale")
	if n.String() != "Spring Sale" {
		t.Errorf("String() = %q, want %q", n.String(), "Spring Sale")
	}
}
