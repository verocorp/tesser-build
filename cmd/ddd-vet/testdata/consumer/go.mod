// A self-contained consumer module (no external deps) that ddd-vet is run
// against end-to-end. The nested go.mod makes it invisible to the parent
// module's ./... patterns; the e2e test copies this tree to a temp dir, where it
// controls .go-ddd.yaml, then runs the built ddd-vet binary here.
module dddvetfixture

go 1.25
