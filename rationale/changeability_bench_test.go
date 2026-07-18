// Benchmarks for the adversarial side of the case: value objects are not free.
// These measure where the VO COSTS something at runtime versus the bare
// primitive, so the suite shows the boundary, not only the wins.
//
// Run: go test -bench=. -benchmem ./...
//
// Expected shape of the result:
//   - Simple value types (construct/equality): overhead is near-zero — the VO
//     is a struct of the same size, validation is a couple of comparisons.
//   - Collection VOs: the defensive-copy rule costs a real allocation per
//     construction and per bulk read that the raw map never pays. THAT is the
//     honest "VO loses" case, and it's where a hot path should think twice.
package changeability_test

import (
	"testing"

	"github.com/verocorp/tesser-build/rationale/primitive"
	"github.com/verocorp/tesser-build/rationale/valueobject"
)

// sink defeats dead-code elimination so the work actually runs.
var (
	sinkF64  float64
	sinkBool bool
	sinkStr  string
	sinkMap  map[string]string
)

// --- Simple value type: construction (VO validates + wraps) ---

func BenchmarkConstruct_Primitive(b *testing.B) {
	for i := 0; i < b.N; i++ {
		sinkF64 = 300.0
	}
}

func BenchmarkConstruct_VO(b *testing.B) {
	for i := 0; i < b.N; i++ {
		t, _ := valueobject.FromKelvin(300.0) // validates against absolute zero
		sinkF64 = t.Kelvin()
	}
}

// --- Simple value type: equality ---

func BenchmarkEqual_Primitive(b *testing.B) {
	for i := 0; i < b.N; i++ {
		sinkBool = primitive.TempEqual(0.0, 273.15) // wrong answer, but this is the cost
	}
}

func BenchmarkEqual_VO(b *testing.B) {
	c, _ := valueobject.FromCelsius(0)
	k, _ := valueobject.FromKelvin(273.15)
	for i := 0; i < b.N; i++ {
		sinkBool = c.Equal(k) // right answer
	}
}

// --- Collection VO: the real cost is the defensive copy ---

func BenchmarkCollectionRead_PrimitiveMap(b *testing.B) {
	m := map[string]string{"sensor": "imu", "axis": "z", "rev": "3"}
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		sinkStr = primitive.TagValue(m, "axis") // direct index, 0 allocs
	}
}

func BenchmarkCollectionRead_VO_Get(b *testing.B) {
	tags := valueobject.NewTags(map[string]string{"sensor": "imu", "axis": "z", "rev": "3"})
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		sinkStr = tags.Get("axis") // single-key read, 0 allocs — VO is free here
	}
}

func BenchmarkCollectionConstruct_PrimitiveMap(b *testing.B) {
	src := map[string]string{"sensor": "imu", "axis": "z", "rev": "3"}
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		sinkMap = src // alias, 0 allocs (and 0 safety)
	}
}

func BenchmarkCollectionConstruct_VO_Tags(b *testing.B) {
	src := map[string]string{"sensor": "imu", "axis": "z", "rev": "3"}
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		sinkMap = valueobject.NewTags(src).All() // copy on construct + copy on read
	}
}
