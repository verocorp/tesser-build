// Package a demonstrates the four flagged comment shapes.
package a

// Double is a doc comment on an exported function.
func Double(x int) int {
	/* a block comment inside a body */
	return x * 2 // a trailing comment
}
