package lending

import (
	"fmt"
	"time"
)

// loanPeriodDays is how many days after checkout a loan is due.
const loanPeriodDays = 14

// lateFeeCentsPerDay is the fee assessed for each whole day a loan is
// overdue, counted from (but not including) its due date.
const lateFeeCentsPerDay = 25

// Loan is one specific checkout of one book: two loans of the same book by
// the same member on the same day are still two different loans, so the
// system tracks a Loan by identity (LoanID), not by its attributes. A loan
// records the fact it started (checkout date, due date) and has exactly
// one further lifecycle event — being returned — so it is a mutable
// entity whose Return method guards that one transition.
type Loan struct {
	id           LoanID
	bookID       BookID
	checkoutDate time.Time
	dueDate      time.Time
	returned     bool
	returnDate   time.Time
}

// LoanSpec carries construction data across the layer boundary. Returned
// and ReturnDate are populated only when reconstructing an
// already-returned loan from storage; a fresh checkout leaves them zero.
type LoanSpec struct {
	ID           string
	BookID       string
	CheckoutDate time.Time
	Returned     bool
	ReturnDate   time.Time
}

// NewLoan validates spec and constructs a Loan. The due date is always
// computed from the checkout date — never taken as input — so a Loan
// whose due date doesn't match "14 days after checkout" is unrepresentable.
func NewLoan(spec LoanSpec) (Loan, error) {
	id, err := NewLoanID(spec.ID)
	if err != nil {
		return Loan{}, fmt.Errorf("invalid loan id: %w", err)
	}
	bookID, err := NewBookID(spec.BookID)
	if err != nil {
		return Loan{}, fmt.Errorf("invalid book id: %w", err)
	}
	if spec.CheckoutDate.IsZero() {
		return Loan{}, fmt.Errorf("loan %s: checkout date is required", id)
	}
	if spec.Returned {
		if spec.ReturnDate.IsZero() {
			return Loan{}, fmt.Errorf("loan %s: return date is required for a returned loan", id)
		}
		if spec.ReturnDate.Before(spec.CheckoutDate) {
			return Loan{}, fmt.Errorf("loan %s: return date %s is before checkout date %s", id, spec.ReturnDate, spec.CheckoutDate)
		}
	}

	return Loan{
		id:           id,
		bookID:       bookID,
		checkoutDate: spec.CheckoutDate,
		dueDate:      spec.CheckoutDate.AddDate(0, 0, loanPeriodDays),
		returned:     spec.Returned,
		returnDate:   spec.ReturnDate,
	}, nil
}

// ID returns the Loan's identity.
func (l Loan) ID() LoanID { return l.id }

// BookID returns the book this loan is for.
func (l Loan) BookID() BookID { return l.bookID }

// CheckoutDate returns the date the book was checked out.
func (l Loan) CheckoutDate() time.Time { return l.checkoutDate }

// DueDate returns the date the book is due — always 14 days after
// checkout.
func (l Loan) DueDate() time.Time { return l.dueDate }

// Returned reports whether the book has been returned.
func (l Loan) Returned() bool { return l.returned }

// ReturnDate returns the date the book was returned and true, or the zero
// time and false if it hasn't been returned yet.
func (l Loan) ReturnDate() (time.Time, bool) { return l.returnDate, l.returned }

// Equal reports whether two Loans are the same checkout. Identity is by
// LoanID alone — never by dates or return status — so Equal, not native
// `==` (which time.Time's monotonic reading makes an unsafe comparison
// anyway), is the correct comparison for Loan identity.
func (l Loan) Equal(other Loan) bool {
	return l.id == other.id
}

// Return records that the book came back on returnDate. It is the loan's
// one lifecycle transition and can only happen once: returning an
// already-returned loan, or on a date before checkout, is rejected and
// leaves the loan unchanged.
func (l *Loan) Return(returnDate time.Time) error {
	if l.returned {
		return fmt.Errorf("loan %s: already returned", l.id)
	}
	if returnDate.Before(l.checkoutDate) {
		return fmt.Errorf("loan %s: return date %s is before checkout date %s", l.id, returnDate, l.checkoutDate)
	}
	l.returned = true
	l.returnDate = returnDate
	return nil
}

// IsOverdueAsOf reports whether the loan is overdue as of asOf: still
// outstanding (not returned) and past its due date. A returned loan is
// never overdue — its outcome is already settled.
func (l Loan) IsOverdueAsOf(asOf time.Time) bool {
	if l.returned {
		return false
	}
	return asOf.After(l.dueDate)
}

// DaysOverdueAsOf returns how many whole days past the due date the loan
// is — evaluated as of asOf if still outstanding, or as of its actual
// return date if already returned (a returned loan's tally is fixed at
// the moment it came back). It is 0 when the loan isn't overdue.
func (l Loan) DaysOverdueAsOf(asOf time.Time) int64 {
	effective := asOf
	if l.returned {
		effective = l.returnDate
	}
	if !effective.After(l.dueDate) {
		return 0
	}
	return int64(effective.Sub(l.dueDate).Hours() / 24)
}

// LateFeeAsOf computes the late fee owed on this loan: 25 cents for every
// day it is overdue (see DaysOverdueAsOf for how "as of" is resolved once
// a loan has been returned). This is domain behavior on the type, not the
// application service — see
// application-services.md#domain-logic-leakage-checks.
func (l Loan) LateFeeAsOf(asOf time.Time) Money {
	days := l.DaysOverdueAsOf(asOf)
	if days <= 0 {
		return Money{}
	}
	// days > 0, so the product is always non-negative: built directly,
	// the same domain-behavior-enforces-its-own-consistency pattern as
	// Money.Add, rather than round-tripping through NewMoney.
	return Money{cents: days * lateFeeCentsPerDay}
}
