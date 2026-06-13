package inconsistent

import "fmt"

// --- Non-conformance 3: EQUALITY VIA String() -----------------------------
//
// Anchor: residual ".String() as equality" found in the test-VO-assertions
// audit (certus). Temp is "a value object" — it has a constructor and a
// String() — but it keeps its scale as representation instead of normalizing,
// and its equality compares the DISPLAY form. Two values that are the SAME
// physical temperature, built in different scales, render different strings and
// compare unequal: the bare-float == bug (../primitive) wearing a value
// object's clothes. This is exactly the pattern `checkstring` forbids.
type Temp struct {
	scale string // "C" or "K" — kept, not normalized away
	value float64
}

func NewTempCelsius(c float64) Temp { return Temp{scale: "C", value: c} }
func NewTempKelvin(k float64) Temp  { return Temp{scale: "K", value: k} }

func (t Temp) String() string { return fmt.Sprintf("%.2f%s", t.value, t.scale) }

// EqualByString compares display strings. 0°C and 273.15K stringify to "0.00C"
// and "273.15K", so this reports the same temperature as unequal — the wrong
// answer, the same one ../primitive gives. ../valueobject normalizes to Kelvin
// and compares value, so its Equal() is right.
func (t Temp) EqualByString(other Temp) bool { return t.String() == other.String() }
