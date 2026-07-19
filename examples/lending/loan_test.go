package lending

import (
	"testing"
	"time"
)

func day(y int, m time.Month, d int) time.Time {
	return time.Date(y, m, d, 0, 0, 0, 0, time.UTC)
}

func validLoanSpec() LoanSpec {
	return LoanSpec{
		ID:           "loan-1",
		BookID:       "book-1",
		CheckoutDate: day(2026, time.January, 1),
	}
}

func TestNewLoan_Valid(t *testing.T) {
	spec := validLoanSpec()
	l, err := NewLoan(spec)
	if err != nil {
		t.Fatalf("NewLoan(%+v) returned unexpected error: %v", spec, err)
	}
	if got, want := l.ID().String(), spec.ID; got != want {
		t.Errorf("ID() = %q, want %q", got, want)
	}
	if got, want := l.BookID().String(), spec.BookID; got != want {
		t.Errorf("BookID() = %q, want %q", got, want)
	}
	if got, want := l.CheckoutDate(), spec.CheckoutDate; !got.Equal(want) {
		t.Errorf("CheckoutDate() = %v, want %v", got, want)
	}
	if got, want := l.DueDate(), day(2026, time.January, 15); !got.Equal(want) {
		t.Errorf("DueDate() = %v, want %v (14 days after checkout)", got, want)
	}
	if l.Returned() {
		t.Error("a freshly checked-out loan must not be Returned")
	}
}

func TestNewLoan_InvalidIDRejected(t *testing.T) {
	spec := validLoanSpec()
	spec.ID = ""
	if _, err := NewLoan(spec); err == nil {
		t.Error("NewLoan with empty ID = nil error, want error")
	}
}

func TestNewLoan_InvalidBookIDRejected(t *testing.T) {
	spec := validLoanSpec()
	spec.BookID = ""
	if _, err := NewLoan(spec); err == nil {
		t.Error("NewLoan with empty book ID = nil error, want error")
	}
}

func TestNewLoan_ZeroCheckoutDateRejected(t *testing.T) {
	spec := validLoanSpec()
	spec.CheckoutDate = time.Time{}
	if _, err := NewLoan(spec); err == nil {
		t.Error("NewLoan with zero checkout date = nil error, want error")
	}
}

func TestNewLoan_ReturnedWithoutReturnDateRejected(t *testing.T) {
	spec := validLoanSpec()
	spec.Returned = true
	if _, err := NewLoan(spec); err == nil {
		t.Error("NewLoan with Returned=true and no return date = nil error, want error")
	}
}

func TestNewLoan_ReturnDateBeforeCheckoutRejected(t *testing.T) {
	spec := validLoanSpec()
	spec.Returned = true
	spec.ReturnDate = day(2025, time.December, 31)
	if _, err := NewLoan(spec); err == nil {
		t.Error("NewLoan with return date before checkout = nil error, want error")
	}
}

func TestNewLoan_ReconstructReturnedLoan(t *testing.T) {
	spec := validLoanSpec()
	spec.Returned = true
	spec.ReturnDate = day(2026, time.January, 20)
	l, err := NewLoan(spec)
	if err != nil {
		t.Fatalf("NewLoan(%+v) returned unexpected error: %v", spec, err)
	}
	if !l.Returned() {
		t.Error("Returned() = false, want true")
	}
	rd, ok := l.ReturnDate()
	if !ok || !rd.Equal(spec.ReturnDate) {
		t.Errorf("ReturnDate() = (%v, %v), want (%v, true)", rd, ok, spec.ReturnDate)
	}
}

func TestLoan_Equality(t *testing.T) {
	same, err := NewLoan(LoanSpec{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)})
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	differentBook, err := NewLoan(LoanSpec{ID: "loan-1", BookID: "book-2", CheckoutDate: day(2026, time.February, 1)})
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	if !same.Equal(differentBook) {
		t.Error("loans with the same ID must be Equal regardless of other attributes")
	}

	other, err := NewLoan(LoanSpec{ID: "loan-2", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)})
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	if same.Equal(other) {
		t.Error("loans with different IDs must not be Equal even with identical attributes")
	}
}

func TestLoan_Return_Succeeds(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	returnDate := day(2026, time.January, 10)
	if err := l.Return(returnDate); err != nil {
		t.Fatalf("Return(%v) returned unexpected error: %v", returnDate, err)
	}
	if !l.Returned() {
		t.Error("Returned() = false after a successful Return")
	}
	rd, ok := l.ReturnDate()
	if !ok || !rd.Equal(returnDate) {
		t.Errorf("ReturnDate() = (%v, %v), want (%v, true)", rd, ok, returnDate)
	}
}

func TestLoan_Return_RejectsAlreadyReturned(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	if err := l.Return(day(2026, time.January, 10)); err != nil {
		t.Fatalf("first Return returned unexpected error: %v", err)
	}
	if err := l.Return(day(2026, time.January, 11)); err == nil {
		t.Error("second Return on an already-returned loan = nil error, want error")
	}
}

func TestLoan_Return_RejectsBeforeCheckoutDate(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	before := day(2025, time.December, 31)
	if err := l.Return(before); err == nil {
		t.Error("Return before checkout date = nil error, want error")
	}
	if l.Returned() {
		t.Error("a rejected Return must leave the loan unchanged")
	}
}

func TestLoan_IsOverdueAsOf(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	tests := []struct {
		name string
		asOf time.Time
		want bool
	}{
		{"before due date", day(2026, time.January, 14), false},
		{"on due date", day(2026, time.January, 15), false},
		{"after due date", day(2026, time.January, 16), true},
	}
	for _, tt := range tests {
		if got := l.IsOverdueAsOf(tt.asOf); got != tt.want {
			t.Errorf("%s: IsOverdueAsOf(%v) = %v, want %v", tt.name, tt.asOf, got, tt.want)
		}
	}
}

func TestLoan_IsOverdueAsOf_ReturnedLoanNeverOverdue(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	if err := l.Return(day(2026, time.January, 20)); err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}
	if l.IsOverdueAsOf(day(2026, time.June, 1)) {
		t.Error("a returned loan must never be reported overdue, regardless of asOf")
	}
}

func TestLoan_DaysOverdueAsOf(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	tests := []struct {
		name string
		asOf time.Time
		want int64
	}{
		{"not yet due", day(2026, time.January, 10), 0},
		{"exactly on due date", day(2026, time.January, 15), 0},
		{"one day late", day(2026, time.January, 16), 1},
		{"ten days late", day(2026, time.January, 25), 10},
	}
	for _, tt := range tests {
		if got := l.DaysOverdueAsOf(tt.asOf); got != tt.want {
			t.Errorf("%s: DaysOverdueAsOf(%v) = %d, want %d", tt.name, tt.asOf, got, tt.want)
		}
	}
}

func TestLoan_LateFeeAsOf_NotOverdue(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	fee := l.LateFeeAsOf(day(2026, time.January, 15))
	if want := MustNewMoney(0); fee != want {
		t.Errorf("LateFeeAsOf(due date) = %s, want %s", fee, want)
	}
}

func TestLoan_LateFeeAsOf_ChargesTwentyFiveCentsPerDayLate(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	fee := l.LateFeeAsOf(day(2026, time.January, 19))
	if want := MustNewMoney(100); fee != want {
		t.Errorf("LateFeeAsOf(4 days late) = %s, want %s", fee, want)
	}
}

func TestLoan_LateFeeAsOf_FrozenAtReturn(t *testing.T) {
	l, err := NewLoan(validLoanSpec())
	if err != nil {
		t.Fatalf("NewLoan returned unexpected error: %v", err)
	}
	if err := l.Return(day(2026, time.January, 19)); err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}
	want := MustNewMoney(100)
	if fee := l.LateFeeAsOf(day(2026, time.January, 19)); fee != want {
		t.Errorf("LateFeeAsOf(return date) = %s, want %s", fee, want)
	}
	if fee := l.LateFeeAsOf(day(2026, time.December, 31)); fee != want {
		t.Errorf("LateFeeAsOf(long after return) = %s, want %s (fee must stay frozen)", fee, want)
	}
}
