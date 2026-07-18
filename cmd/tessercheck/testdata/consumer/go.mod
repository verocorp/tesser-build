// A self-contained consumer module (no external deps) that tessercheck is run
// against end-to-end. The nested go.mod makes it invisible to the parent
// module's ./... patterns; the e2e test copies this tree to a temp dir, where it
// controls .tesser-build.yaml, then runs the built tessercheck binary here.
module tessercheckfixture

go 1.25
