// tb-cell: handlers go-example 🟡 -- v3 transport/ shape; adapters/handlers layout pending the Go mirror
package transport

import (
	"encoding/json"
	"net/http"

	"github.com/verocorp/tesser-build/examples/running/linkcampaign"
)

type Handler struct {
	client linkcampaign.Client
	mux    *http.ServeMux
}

func NewHandler(client linkcampaign.Client) *Handler {
	h := &Handler{client: client, mux: http.NewServeMux()}
	h.mux.HandleFunc("POST /campaigns", h.createCampaign)
	h.mux.HandleFunc("GET /campaigns/{id}", h.getCampaign)
	h.mux.HandleFunc("POST /campaigns/{id}/links", h.addShortLink)
	h.mux.HandleFunc("POST /campaigns/{id}/links/{slug}/deactivate", h.deactivateShortLink)
	return h
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	h.mux.ServeHTTP(w, r)
}

func (h *Handler) createCampaign(w http.ResponseWriter, r *http.Request) {
	var req linkcampaign.CreateCampaignRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	resp, err := h.client.CreateCampaign(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, err)
		return
	}
	writeJSON(w, http.StatusCreated, resp)
}

func (h *Handler) getCampaign(w http.ResponseWriter, r *http.Request) {
	req := linkcampaign.GetCampaignRequest{CampaignID: r.PathValue("id")}
	resp, err := h.client.GetCampaign(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusNotFound, err)
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func (h *Handler) addShortLink(w http.ResponseWriter, r *http.Request) {
	var body linkcampaign.ShortLinkInput
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		writeError(w, http.StatusBadRequest, err)
		return
	}
	req := linkcampaign.AddShortLinkRequest{
		CampaignID: r.PathValue("id"),
		Slug:       body.Slug,
		TargetURL:  body.TargetURL,
	}
	resp, err := h.client.AddShortLink(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, err)
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func (h *Handler) deactivateShortLink(w http.ResponseWriter, r *http.Request) {
	req := linkcampaign.DeactivateShortLinkRequest{
		CampaignID: r.PathValue("id"),
		Slug:       r.PathValue("slug"),
	}
	resp, err := h.client.DeactivateShortLink(r.Context(), req)
	if err != nil {
		writeError(w, http.StatusUnprocessableEntity, err)
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

func writeError(w http.ResponseWriter, status int, err error) {
	writeJSON(w, status, map[string]string{"error": err.Error()})
}
