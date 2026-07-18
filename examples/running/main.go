// Command running is a minimal, runnable link-campaign service: the
// composition root that wires the in-memory repository, the application
// service, the public Client, and the HTTP handler together, then serves
// requests.
//
// tb-cell: public-interface go-example 🟡 -- v3 single-main shape; settled anatomy's Go mirror (examples/app) pending
package main

import (
	"log"
	"net/http"

	"github.com/verocorp/tesser-build/examples/running/campaignapp"
	"github.com/verocorp/tesser-build/examples/running/linkcampaignimpl"
	"github.com/verocorp/tesser-build/examples/running/transport"
)

// wire is the composition root: the one place that chooses the concrete
// implementations (here, the in-memory repository), composes them behind
// the public linkcampaign.Client, and constructs the handler, injecting the
// Client into it. Swapping the repository for a database-backed one later
// is a one-line change, here only.
func wire() http.Handler {
	repo := linkcampaignimpl.NewInMemoryCampaignRepository() // the impl choice lives here …
	svc := campaignapp.NewCampaignService(repo)              // … inject it into the service
	client := linkcampaignimpl.NewClient(svc)                // compose behind the public Client
	return transport.NewHandler(client)                      // construct handler, INJECT the Client
}

func main() {
	log.Println("link-campaign service listening on :8080")
	if err := http.ListenAndServe(":8080", wire()); err != nil { // a minimal runnable main
		log.Fatal(err)
	}
}
