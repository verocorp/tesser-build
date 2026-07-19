package campaign

import (
	"fmt"
	"strings"
)

type CampaignName struct {
	value string
}

func NewCampaignName(value string) (CampaignName, error) {
	if strings.TrimSpace(value) == "" {
		return CampaignName{}, fmt.Errorf("campaign name must not be empty")
	}
	return CampaignName{value: value}, nil
}

func MustNewCampaignName(value string) CampaignName {
	n, err := NewCampaignName(value)
	if err != nil {
		panic(err)
	}
	return n
}

func (n CampaignName) String() string {
	return n.value
}
