// tb-cell: public-interface go-example 🟡 -- v3 single-main shape; settled anatomy's Go mirror (examples/app) pending
package main

import (
	"log"
	"net/http"

	"github.com/verocorp/tesser-build/examples/running/campaignapp"
	"github.com/verocorp/tesser-build/examples/running/linkcampaignimpl"
	"github.com/verocorp/tesser-build/examples/running/transport"
)

func wire() http.Handler {
	repo := linkcampaignimpl.NewInMemoryCampaignRepository()
	svc := campaignapp.NewCampaignService(repo)
	client := linkcampaignimpl.NewClient(svc)
	return transport.NewHandler(client)
}

func main() {
	log.Println("link-campaign service listening on :8080")
	if err := http.ListenAndServe(":8080", wire()); err != nil {
		log.Fatal(err)
	}
}
