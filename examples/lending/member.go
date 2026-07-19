package lending

import (
	"fmt"
	"time"
)

const maxActiveLoansPerMember = 3

type Member struct {
	id    MemberID
	loans []Loan
	_     [0]func()
}

type MemberSpec struct {
	ID    string
	Loans []LoanSpec
}

func NewMember(spec MemberSpec) (Member, error) {
	id, err := NewMemberID(spec.ID)
	if err != nil {
		return Member{}, fmt.Errorf("invalid member id: %w", err)
	}

	loans := make([]Loan, 0, len(spec.Loans))
	for i, loanSpec := range spec.Loans {
		loan, err := NewLoan(loanSpec)
		if err != nil {
			return Member{}, fmt.Errorf("member %s: invalid loan at index %d: %w", id, i, err)
		}
		loans = append(loans, loan)
	}
	if active := activeLoanCount(loans); active > maxActiveLoansPerMember {
		return Member{}, fmt.Errorf("member %s: %d active loans exceeds the limit of %d", id, active, maxActiveLoansPerMember)
	}

	return Member{id: id, loans: loans}, nil
}

func (m Member) ID() MemberID { return m.id }

func (m Member) Loans() []Loan {
	out := make([]Loan, len(m.loans))
	copy(out, m.loans)
	return out
}

func (m *Member) CheckOut(bookID BookID, checkoutDate time.Time) (Loan, error) {
	if active := activeLoanCount(m.loans); active >= maxActiveLoansPerMember {
		return Loan{}, fmt.Errorf("member %s: already has %d books on loan, the maximum allowed", m.id, maxActiveLoansPerMember)
	}

	loan, err := NewLoan(LoanSpec{
		ID:           newLoanID(m.id, bookID, checkoutDate).String(),
		BookID:       bookID.String(),
		CheckoutDate: checkoutDate,
	})
	if err != nil {
		return Loan{}, fmt.Errorf("member %s: check out book %s: %w", m.id, bookID, err)
	}

	m.loans = append(m.loans, loan)
	return loan, nil
}

func (m *Member) Return(bookID BookID, returnDate time.Time) (Money, error) {
	for i := range m.loans {
		if m.loans[i].returned || m.loans[i].bookID != bookID {
			continue
		}
		if err := m.loans[i].Return(returnDate); err != nil {
			return Money{}, fmt.Errorf("member %s: %w", m.id, err)
		}
		return m.loans[i].LateFeeAsOf(returnDate), nil
	}
	return Money{}, fmt.Errorf("member %s: no active loan found for book %s", m.id, bookID)
}

func (m Member) TotalLateFees(asOf time.Time) Money {
	total := Money{}
	for _, loan := range m.loans {
		if loan.returned {
			continue
		}
		total = total.Add(loan.LateFeeAsOf(asOf))
	}
	return total
}

func activeLoanCount(loans []Loan) int {
	count := 0
	for _, loan := range loans {
		if !loan.returned {
			count++
		}
	}
	return count
}

func newLoanID(memberID MemberID, bookID BookID, checkoutDate time.Time) LoanID {
	return LoanID{value: fmt.Sprintf("%s:%s:%d", memberID, bookID, checkoutDate.UnixNano())}
}
