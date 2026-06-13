package a

// Meters is a value object; it is the target of a legitimate conversion.
type Meters struct{ v float64 }

func NewMeters(v float64) (Meters, error) { return Meters{v: v}, nil }
func (m Meters) String() string           { return "m" }

// Feet's ToMeters returns another value object (a named type), so it is a
// legitimate conversion and is NOT flagged.
type Feet struct{ v float64 }

func NewFeet(v float64) (Feet, error) { return Feet{v: v}, nil }
func (f Feet) String() string         { return "ft" }
func (f Feet) ToMeters() Meters       { return Meters{v: f.v * 0.3048} }

// BadToString exposes ToString — flagged (use String instead).
type BadToString struct{ v string }

func NewBadToString(v string) (BadToString, error) { return BadToString{v: v}, nil }
func (b BadToString) String() string               { return b.v }
func (b BadToString) ToString() string             { return b.v } // want `value object BadToString exposes ToString`

// BadToInt exposes a To* accessor returning a primitive — flagged.
type BadToInt struct{ v int }

func NewBadToInt(v int) (BadToInt, error) { return BadToInt{v: v}, nil }
func (b BadToInt) String() string         { return "i" }
func (b BadToInt) ToInt() int             { return b.v } // want `value object BadToInt exposes ToInt returning a Go primitive`

// Wrapped exposes a To* accessor returning (primitive, error) — still a
// representation leak, flagged.
type Wrapped struct{ v string }

func NewWrapped(v string) (Wrapped, error) { return Wrapped{v: v}, nil }
func (w Wrapped) String() string           { return w.v }
func (w Wrapped) ToRaw() (string, error)   { return w.v, nil } // want `value object Wrapped exposes ToRaw returning a Go primitive`

// Counter has a method beginning with "To" but a lowercase third letter, so it
// is an ordinary word ("Total"), not a To-accessor — not flagged.
type Counter struct{ n int }

func NewCounter(n int) (Counter, error) { return Counter{n: n}, nil }
func (c Counter) String() string        { return "c" }
func (c Counter) Total() int            { return c.n }
