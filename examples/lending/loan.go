package lending

import (
	"fmt"
	"time"
)

const loanPeriodDays = 14

const lateFeeCentsPerDay = 25

type Loan struct {
	id           LoanID
	bookID       BookID
	checkoutDate time.Time
	dueDate      time.Time
	returned     bool
	returnDate   time.Time
}

type LoanSpec struct {
	ID           string
	BookID       string
	CheckoutDate time.Time
	Returned     bool
	ReturnDate   time.Time
}

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

func (l Loan) ID() LoanID { return l.id }

func (l Loan) BookID() BookID { return l.bookID }

func (l Loan) CheckoutDate() time.Time { return l.checkoutDate }

func (l Loan) DueDate() time.Time { return l.dueDate }

func (l Loan) Returned() bool { return l.returned }

func (l Loan) ReturnDate() (time.Time, bool) { return l.returnDate, l.returned }

func (l Loan) Equal(other Loan) bool {
	return l.id == other.id
}

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

func (l Loan) IsOverdueAsOf(asOf time.Time) bool {
	if l.returned {
		return false
	}
	return asOf.After(l.dueDate)
}

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

func (l Loan) LateFeeAsOf(asOf time.Time) Money {
	days := l.DaysOverdueAsOf(asOf)
	if days <= 0 {
		return Money{}
	}

	return Money{cents: days * lateFeeCentsPerDay}
}
