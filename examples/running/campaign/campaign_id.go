package campaign

import "fmt"

type CampaignID struct {
	value string
}

func NewCampaignID(value string) (CampaignID, error) {
	if value == "" {
		return CampaignID{}, fmt.Errorf("campaign id must not be empty")
	}
	return CampaignID{value: value}, nil
}

func MustNewCampaignID(value string) CampaignID {
	id, err := NewCampaignID(value)
	if err != nil {
		panic(err)
	}
	return id
}

func (id CampaignID) String() string {
	return id.value
}
