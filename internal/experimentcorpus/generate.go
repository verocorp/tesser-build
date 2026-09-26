package experimentcorpus

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
)

type Options struct {
	Family  string
	Variant string
	Seed    int64
	Out     string
}

type Metadata struct {
	SchemaVersion int               `json:"schema_version"`
	Family        string            `json:"family"`
	Variant       string            `json:"variant"`
	Seed          int64             `json:"seed"`
	SeedStrategy  string            `json:"seed_strategy"`
	Producer      string            `json:"producer"`
	Protocol      string            `json:"protocol"`
	Python        string            `json:"python"`
	Conformance   string            `json:"conformance"`
	Architecture  string            `json:"architecture"`
	Mutation      string            `json:"mutation"`
	Provenance    string            `json:"provenance"`
	Digests       map[string]string `json:"sha256"`
}

func Generate(options Options) error {
	if options.Family != "reserving-inventory" && options.Family != "transferring-funds" {
		return fmt.Errorf("unsupported family %q", options.Family)
	}
	if options.Variant != "structured" && options.Variant != "scattered" {
		return fmt.Errorf("unsupported variant %q", options.Variant)
	}
	if options.Out == "" {
		return errors.New("out is required")
	}
	source := application(options)
	readme := fmt.Sprintf("# Controlled %s seed\n\nRun `python3.12 application.py` and send one JSON command per line.\nState lasts for one process only. No third-party dependencies are needed.\n\nVariant: %s. Implementation seed: %d. The seed never changes initial state\nor the protocol. Both variants are intentionally nonconformant controlled\nseeds: neither implements the full Tesser architecture. Conformance is\nunchecked; structured means centralized policy, not certified conformance.\n\nThe producer uses authored policy templates, not probe answers. The scattered\nvariant repeats policy at distinct entry paths without intentional behavioral\nbugs. metadata.json records the mutation and SHA-256 digests of the generated\nsource, this README, and the tree declaration. Runtime-host integration is\nnot provided or claimed.\n", options.Family, options.Variant, options.Seed)
	readme += "\nSeed parity selects one of two equivalent integer-range validation expressions.\nDifferent seeds of the same parity produce identical application source.\n\n## Protocol\n\nCommands must have exactly the documented keys. Integer arguments are in\n1..1000; booleans, floats, nulls, missing/extra keys and unknown operations\nreturn `{\"error\":\"invalid_input\"}` before state-dependent checks. Every\nrejection preserves state. Malformed JSON and duplicate keys are rejected.\nOne response is flushed per input line; EOF ends the process.\n\n"
	if options.Family == "reserving-inventory" {
		readme += "Initial state is stock=10, reserved=0. `status` takes only `op`.\n`reserve`, `release`, `restock`, and `ship` take `op` and `quantity`.\nReserve raises reserved; ship lowers stock. Both require quantity no greater\nthan stock minus reserved, else `insufficient_stock`. Release lowers reserved\nif sufficient, else `insufficient_reserved`. Restock raises stock. All successes\nreturn exactly `{stock,reserved,available}`, with available=stock-reserved.\n"
	} else {
		readme += "Initial balances are amber=100, birch=40. `balances` takes only `op`.\n`transfer` takes `op`, `from`, `to`, and `amount`; accounts must be distinct\nmembers of amber/birch. `purchase` takes only `op` and `amount` and transfers\nfrom amber to birch. Both reject `insufficient_funds` if the source is short;\notherwise debit and credit atomically, without fees. All successes return\nexactly `{amber,birch}`.\n"
	}
	files := map[string][]byte{
		"application.py": []byte(source),
		"README.md":      []byte(readme),
		".tesser-root":   []byte("app\n"),
	}
	mutation := "centralized-policy-and-state"
	if options.Variant == "scattered" {
		mutation = "repeat-policy-across-legitimate-entry-paths"
	}
	metadata := Metadata{
		SchemaVersion: 1, Family: options.Family, Variant: options.Variant, Seed: options.Seed,
		SeedStrategy: "parity selects one of two equivalent integer-range validation expressions",
		Producer:     "tesser-corpus/v1", Protocol: "json-lines/v1", Python: "3.12",
		Conformance: "unchecked", Architecture: "intentionally-nonconformant-controlled-seed",
		Mutation: mutation, Provenance: "authored semantic implementation; no expected probe answers used",
		Digests: make(map[string]string),
	}
	for name, content := range files {
		digest := sha256.Sum256(content)
		metadata.Digests[name] = hex.EncodeToString(digest[:])
	}
	encoded, err := json.MarshalIndent(metadata, "", "  ")
	if err != nil {
		return err
	}
	files["metadata.json"] = append(encoded, '\n')
	root, err := outputRoot(options.Out)
	if err != nil {
		return err
	}
	defer root.Close()
	for _, name := range []string{"application.py", "README.md", ".tesser-root", "metadata.json"} {
		file, err := root.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o644)
		if err != nil {
			return err
		}
		_, writeErr := file.Write(files[name])
		closeErr := file.Close()
		if err := errors.Join(writeErr, closeErr); err != nil {
			return err
		}
	}
	return nil
}
