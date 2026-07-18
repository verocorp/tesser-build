package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

// TestWiring_EndToEnd drives the composition root's object graph through a
// real HTTP request: create a campaign, then fetch it back. It demonstrates
// the app is wired together correctly end-to-end, from the handler down to
// the in-memory repository.
func TestWiring_EndToEnd(t *testing.T) {
	ts := httptest.NewServer(wire())
	defer ts.Close()

	createBody := `{"name":"Spring Sale","links":[{"slug":"spring-sale","target_url":"https://example.com/spring"}]}`
	createResp, err := http.Post(ts.URL+"/campaigns", "application/json", bytes.NewBufferString(createBody))
	if err != nil {
		t.Fatalf("POST /campaigns: %v", err)
	}
	defer createResp.Body.Close()
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("POST /campaigns: status = %d, want %d", createResp.StatusCode, http.StatusCreated)
	}

	var created linkcampaign.CreateCampaignResponse
	if err := json.NewDecoder(createResp.Body).Decode(&created); err != nil {
		t.Fatalf("decode create response: %v", err)
	}

	getResp, err := http.Get(ts.URL + "/campaigns/" + created.CampaignID)
	if err != nil {
		t.Fatalf("GET /campaigns/{id}: %v", err)
	}
	defer getResp.Body.Close()
	if getResp.StatusCode != http.StatusOK {
		t.Fatalf("GET /campaigns/{id}: status = %d, want %d", getResp.StatusCode, http.StatusOK)
	}

	var fetched linkcampaign.GetCampaignResponse
	if err := json.NewDecoder(getResp.Body).Decode(&fetched); err != nil {
		t.Fatalf("decode get response: %v", err)
	}
	if fetched.Name != "Spring Sale" || len(fetched.Links) != 1 {
		t.Errorf("unexpected fetched campaign: %+v", fetched)
	}
}
