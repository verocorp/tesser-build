package transport_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/verocorp/tesser-build/examples/running/campaignapp"
	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
	"github.com/verocorp/tesser-build/examples/running/linkcampaignimpl"
	"github.com/verocorp/tesser-build/examples/running/transport"
)

// newTestHandler wires a real Client (in-memory repo + application service)
// behind the Handler, the same way the composition root does, so this
// test exercises the handler against real wiring rather than a mock.
func newTestHandler() *transport.Handler {
	repo := linkcampaignimpl.NewInMemoryCampaignRepository()
	svc := campaignapp.NewCampaignService(repo)
	client := linkcampaignimpl.NewClient(svc)
	return transport.NewHandler(client)
}

func TestHandler_CreateAndFetchCampaign(t *testing.T) {
	h := newTestHandler()
	ts := httptest.NewServer(h)
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
	if created.CampaignID == "" {
		t.Fatal("expected a non-empty campaign id")
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
	if fetched.Name != "Spring Sale" || len(fetched.Links) != 1 || fetched.Links[0].Slug != "spring-sale" {
		t.Errorf("unexpected fetched campaign: %+v", fetched)
	}
}

func TestHandler_AddAndDeactivateShortLink(t *testing.T) {
	h := newTestHandler()
	ts := httptest.NewServer(h)
	defer ts.Close()

	createResp, err := http.Post(ts.URL+"/campaigns", "application/json", bytes.NewBufferString(`{"name":"Spring Sale"}`))
	if err != nil {
		t.Fatalf("POST /campaigns: %v", err)
	}
	var created linkcampaign.CreateCampaignResponse
	json.NewDecoder(createResp.Body).Decode(&created)
	createResp.Body.Close()

	addBody := `{"slug":"spring-sale","target_url":"https://example.com/spring"}`
	addResp, err := http.Post(ts.URL+"/campaigns/"+created.CampaignID+"/links", "application/json", bytes.NewBufferString(addBody))
	if err != nil {
		t.Fatalf("POST /campaigns/{id}/links: %v", err)
	}
	defer addResp.Body.Close()
	if addResp.StatusCode != http.StatusOK {
		t.Fatalf("POST /campaigns/{id}/links: status = %d, want %d", addResp.StatusCode, http.StatusOK)
	}

	deactivateResp, err := http.Post(ts.URL+"/campaigns/"+created.CampaignID+"/links/spring-sale/deactivate", "application/json", nil)
	if err != nil {
		t.Fatalf("POST .../deactivate: %v", err)
	}
	defer deactivateResp.Body.Close()
	if deactivateResp.StatusCode != http.StatusOK {
		t.Fatalf("POST .../deactivate: status = %d, want %d", deactivateResp.StatusCode, http.StatusOK)
	}

	var deactivated linkcampaign.DeactivateShortLinkResponse
	if err := json.NewDecoder(deactivateResp.Body).Decode(&deactivated); err != nil {
		t.Fatalf("decode deactivate response: %v", err)
	}
	if len(deactivated.Links) != 1 || deactivated.Links[0].Active {
		t.Errorf("expected the short link to be inactive: %+v", deactivated.Links)
	}
}

func TestHandler_GetCampaign_NotFound(t *testing.T) {
	h := newTestHandler()
	ts := httptest.NewServer(h)
	defer ts.Close()

	resp, err := http.Get(ts.URL + "/campaigns/does-not-exist")
	if err != nil {
		t.Fatalf("GET /campaigns/{id}: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("status = %d, want %d", resp.StatusCode, http.StatusNotFound)
	}
}
