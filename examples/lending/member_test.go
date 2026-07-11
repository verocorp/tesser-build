package lending

import (
	"reflect"
	"testing"
	"time"
)

func validMemberSpec() MemberSpec {
	return MemberSpec{
		ID: "member-1",
		Loans: []LoanSpec{
			{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-2", BookID: "book-2", CheckoutDate: day(2026, time.January, 1)},
		},
	}
}

func TestNewMember_Valid(t *testing.T) {
	spec := validMemberSpec()
	m, err := NewMember(spec)
	if err != nil {
		t.Fatalf("NewMember(%+v) returned unexpected error: %v", spec, err)
	}
	if got, want := m.ID().String(), spec.ID; got != want {
		t.Errorf("ID() = %q, want %q", got, want)
	}
	if got, want := len(m.Loans()), len(spec.Loans); got != want {
		t.Errorf("len(Loans()) = %d, want %d", got, want)
	}
}

func TestNewMember_InvalidIDRejected(t *testing.T) {
	spec := validMemberSpec()
	spec.ID = ""
	if _, err := NewMember(spec); err == nil {
		t.Error("NewMember with empty ID = nil error, want error")
	}
}

func TestNewMember_InvalidLoanRejected(t *testing.T) {
	spec := validMemberSpec()
	spec.Loans[0].BookID = ""
	if _, err := NewMember(spec); err == nil {
		t.Error("NewMember with an invalid loan = nil error, want error")
	}
}

// TestNewMember_TooManyActiveLoansRejected is the aggregate's reason to
// exist: a member reconstructed with more than 3 active loans must be
// rejected by the constructor.
func TestNewMember_TooManyActiveLoansRejected(t *testing.T) {
	spec := MemberSpec{
		ID: "member-1",
		Loans: []LoanSpec{
			{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-2", BookID: "book-2", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-3", BookID: "book-3", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-4", BookID: "book-4", CheckoutDate: day(2026, time.January, 1)},
		},
	}
	if _, err := NewMember(spec); err == nil {
		t.Error("NewMember with 4 active loans = nil error, want error")
	}
}

// TestNewMember_ReturnedLoansDontCountTowardTheLimit proves the limit is
// on active loans, not total loan history.
func TestNewMember_ReturnedLoansDontCountTowardTheLimit(t *testing.T) {
	spec := MemberSpec{
		ID: "member-1",
		Loans: []LoanSpec{
			{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1), Returned: true, ReturnDate: day(2026, time.January, 5)},
			{ID: "loan-2", BookID: "book-2", CheckoutDate: day(2026, time.January, 1), Returned: true, ReturnDate: day(2026, time.January, 5)},
			{ID: "loan-3", BookID: "book-3", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-4", BookID: "book-4", CheckoutDate: day(2026, time.January, 1)},
			{ID: "loan-5", BookID: "book-5", CheckoutDate: day(2026, time.January, 1)},
		},
	}
	if _, err := NewMember(spec); err != nil {
		t.Errorf("NewMember with 2 returned + 3 active loans returned unexpected error: %v", err)
	}
}

// TestMember_Loans_DefensiveCopy mutates the slice returned by Loans() and
// asserts the member itself is unaffected.
func TestMember_Loans_DefensiveCopy(t *testing.T) {
	m, err := NewMember(validMemberSpec())
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	got := m.Loans()
	got[0] = Loan{}

	again := m.Loans()
	if again[0].ID().String() != "loan-1" {
		t.Error("mutating the slice returned by Loans() must not affect the member")
	}
}

// TestMember_Equality_Blocked asserts native `==` on Member does not
// compile-time compare by value; the aggregate is not comparable.
func TestMember_Equality_Blocked(t *testing.T) {
	if reflect.TypeFor[Member]().Comparable() {
		t.Fatal("Member must be non-comparable")
	}
}

func TestMember_CheckOut_Succeeds(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	loan, err := m.CheckOut(MustNewBookID("book-1"), checkoutDate)
	if err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if got, want := loan.DueDate(), day(2026, time.January, 15); !got.Equal(want) {
		t.Errorf("CheckOut: loan DueDate() = %v, want %v", got, want)
	}
	if got, want := len(m.Loans()), 1; got != want {
		t.Errorf("len(Loans()) after CheckOut = %d, want %d", got, want)
	}
}

// TestMember_CheckOut_RejectsFourthBook is the aggregate's reason to
// exist, exercised through its transition: a member who already has 3
// books on loan cannot check out a 4th, and the attempt leaves the member
// unchanged.
func TestMember_CheckOut_RejectsFourthBook(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	for i, bookID := range []string{"book-1", "book-2", "book-3"} {
		if _, err := m.CheckOut(MustNewBookID(bookID), checkoutDate); err != nil {
			t.Fatalf("CheckOut #%d returned unexpected error: %v", i+1, err)
		}
	}

	if _, err := m.CheckOut(MustNewBookID("book-4"), checkoutDate); err == nil {
		t.Error("4th CheckOut = nil error, want error")
	}
	if got, want := len(m.Loans()), 3; got != want {
		t.Errorf("len(Loans()) after rejected 4th CheckOut = %d, want %d (no partial mutation)", got, want)
	}
}

// TestMember_CheckOut_AllowsAnotherAfterReturn proves the limit is on
// active loans: returning one of 3 frees a slot for a new checkout.
func TestMember_CheckOut_AllowsAnotherAfterReturn(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	for _, bookID := range []string{"book-1", "book-2", "book-3"} {
		if _, err := m.CheckOut(MustNewBookID(bookID), checkoutDate); err != nil {
			t.Fatalf("CheckOut returned unexpected error: %v", err)
		}
	}

	if _, err := m.Return(MustNewBookID("book-1"), day(2026, time.January, 5)); err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}

	if _, err := m.CheckOut(MustNewBookID("book-4"), day(2026, time.January, 6)); err != nil {
		t.Errorf("CheckOut after a Return returned unexpected error: %v", err)
	}
}

func TestMember_Return_Succeeds(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	if _, err := m.CheckOut(MustNewBookID("book-1"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}

	returnDate := day(2026, time.January, 19) // due 1/15, 4 days late
	fee, err := m.Return(MustNewBookID("book-1"), returnDate)
	if err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}
	if want := MustNewMoney(100); fee != want {
		t.Errorf("Return fee = %s, want %s", fee, want)
	}
}

func TestMember_Return_RejectsNoActiveLoanForBook(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	if _, err := m.Return(MustNewBookID("book-1"), day(2026, time.January, 1)); err == nil {
		t.Error("Return with no active loan = nil error, want error")
	}
}

func TestMember_Return_RejectsAlreadyReturnedBook(t *testing.T) {
	m, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	if _, err := m.CheckOut(MustNewBookID("book-1"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if _, err := m.Return(MustNewBookID("book-1"), day(2026, time.January, 5)); err != nil {
		t.Fatalf("first Return returned unexpected error: %v", err)
	}
	if _, err := m.Return(MustNewBookID("book-1"), day(2026, time.January, 6)); err == nil {
		t.Error("second Return on the same book = nil error, want error")
	}
}

func TestMember_TotalLateFees_SumsOverdueLoans(t *testing.T) {
	spec := MemberSpec{
		ID: "member-1",
		Loans: []LoanSpec{
			// due 2026-01-15, 4 days overdue as of 2026-01-19 -> $1.00
			{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)},
			// due 2026-01-15, 2 days overdue as of 2026-01-19 (checked out later) -> $0.50
			{ID: "loan-2", BookID: "book-2", CheckoutDate: day(2026, time.January, 3)},
		},
	}
	m, err := NewMember(spec)
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	got := m.TotalLateFees(day(2026, time.January, 19))
	if want := MustNewMoney(150); got != want {
		t.Errorf("TotalLateFees = %s, want %s", got, want)
	}
}

func TestMember_TotalLateFees_ExcludesReturnedLoans(t *testing.T) {
	spec := MemberSpec{
		ID: "member-1",
		Loans: []LoanSpec{
			// returned late, but settled — must not count toward what's currently owed
			{ID: "loan-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1), Returned: true, ReturnDate: day(2026, time.January, 19)},
			// still outstanding and overdue
			{ID: "loan-2", BookID: "book-2", CheckoutDate: day(2026, time.January, 1)},
		},
	}
	m, err := NewMember(spec)
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	got := m.TotalLateFees(day(2026, time.January, 19))
	if want := MustNewMoney(100); got != want { // only loan-2's $1.00
		t.Errorf("TotalLateFees = %s, want %s (returned loan-1 must be excluded)", got, want)
	}
}

func TestMember_TotalLateFees_ZeroWhenNoneOverdue(t *testing.T) {
	m, err := NewMember(validMemberSpec()) // checked out 2026-01-01, due 2026-01-15
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	got := m.TotalLateFees(day(2026, time.January, 10))
	if want := MustNewMoney(0); got != want {
		t.Errorf("TotalLateFees(before due date) = %s, want %s", got, want)
	}
}
