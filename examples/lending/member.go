package lending

import (
	"fmt"
	"time"
)

// maxActiveLoansPerMember is how many books a member may have on loan at
// once. An active loan is one that hasn't been returned yet.
const maxActiveLoansPerMember = 3

// Member is a library member and the aggregate root for their loans.
// "At most 3 books on loan at once" is a rule that spans the member's
// whole group of loans, so it can only be enforced where that whole group
// is visible: here, at construction and re-established after every
// checkout. A member's set of loans grows and changes over their lifetime
// (more checkouts, more returns), so Member is a mutable, lifecycle
// aggregate — CheckOut and Return are its root-guarded transitions, and
// nothing outside the aggregate holds or mutates a Loan directly.
type Member struct {
	id    MemberID
	loans []Loan
	_     [0]func() // non-comparable — a member is never compared by value
}

// MemberSpec carries construction data across the layer boundary. Loans is
// how a repository reconstructs a member's existing loan history; a
// brand-new member has none.
type MemberSpec struct {
	ID    string
	Loans []LoanSpec
}

// NewMember validates spec and constructs a Member. Every loan is built
// through NewLoan — never re-validated here — and the
// at-most-3-active-loans invariant is checked once the whole set is
// assembled, so a member reconstructed from storage with too many active
// loans is unrepresentable.
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

// ID returns the Member's identity.
func (m Member) ID() MemberID { return m.id }

// Loans returns a defensive copy of the member's loans, past and present;
// mutating the result never affects the member.
func (m Member) Loans() []Loan {
	out := make([]Loan, len(m.loans))
	copy(out, m.loans)
	return out
}

// CheckOut records a new loan of bookID starting on checkoutDate, due 14
// days later, and returns it. It is the guarded transition that
// re-establishes the at-most-3-active-loans invariant: a member already
// at the limit is rejected and left unchanged.
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

// Return records that bookID came back on returnDate, against the
// member's one matching active loan for that book, and reports the late
// fee assessed on it. It errors — leaving the member unchanged — if the
// member has no active loan for that book.
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

// TotalLateFees sums the late fees owed across every loan the member
// currently has outstanding, as of asOf. A rule that spans the member's
// whole set of loans belongs on the aggregate root, not a loop in a
// service — see application-services.md#domain-logic-leakage-checks. Fees
// on already-returned loans were fixed and (in the real world) settled at
// return time, so they don't count toward what the member currently owes.
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

// activeLoanCount counts the member's not-yet-returned loans.
func activeLoanCount(loans []Loan) int {
	count := 0
	for _, loan := range loans {
		if !loan.returned {
			count++
		}
	}
	return count
}

// newLoanID mints an identity for a new loan. No use case supplies an
// external loan ID (check-out takes only a member, a book, and a date), so
// the aggregate that owns loan identity assigns it: the member, the book,
// and the checkout instant concatenated is unique by construction, so this
// builds the value object directly rather than round-tripping through
// NewLoanID — the same domain-behavior-enforces-its-own-consistency
// pattern as Money.Add.
func newLoanID(memberID MemberID, bookID BookID, checkoutDate time.Time) LoanID {
	return LoanID{value: fmt.Sprintf("%s:%s:%d", memberID, bookID, checkoutDate.UnixNano())}
}
