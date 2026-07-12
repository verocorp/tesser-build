package campaign

import (
	"fmt"
	"strings"
)

// CampaignName is the marketing team's name for a Campaign. Simple,
// single-value value object: flat constructor, native equality.
//
// The rules given for this feature don't say anything about the shape of a
// campaign's name beyond "a name" — the simplest rule that fits the
// skill's primitive-obsession guidance (the value is domain-meaningful and
// gets a validation rule) is "non-empty". Noted here since the skill left
// this specific rule uncovered.
type CampaignName struct {
	value string
}

// NewCampaignName validates and constructs a CampaignName.
func NewCampaignName(value string) (CampaignName, error) {
	if strings.TrimSpace(value) == "" {
		return CampaignName{}, fmt.Errorf("campaign name must not be empty")
	}
	return CampaignName{value: value}, nil
}

// MustNewCampaignName panics on invalid input; use only with known-valid
// literals (tests, package-level vars), never with runtime data.
func MustNewCampaignName(value string) CampaignName {
	n, err := NewCampaignName(value)
	if err != nil {
		panic(err)
	}
	return n
}

// String is the display form and the sole string accessor.
func (n CampaignName) String() string {
	return n.value
}
