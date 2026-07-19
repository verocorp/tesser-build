//go:build !ignoreme

// tb-cell: value-objects go-example ✅
package a

//go:generate echo directives-are-exempt

func Triple(x int) int { //nolint:examplelint // reason text rides the directive
	return x * 3
}
