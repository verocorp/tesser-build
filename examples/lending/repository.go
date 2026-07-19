package lending

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"
)

var ErrMemberNotFound = errors.New("lending: member not found")

type MemberRepository interface {
	Save(ctx context.Context, member Member) error

	Load(ctx context.Context, id MemberID) (Member, error)

	FindOverdueLoans(ctx context.Context, asOf time.Time) ([]OverdueLoan, error)
}

type OverdueLoan struct {
	MemberID MemberID
	Loan     Loan
}

type memberRecord struct {
	id    string
	loans []loanRecord
}

type loanRecord struct {
	id           string
	bookID       string
	checkoutDate time.Time
	returned     bool
	returnDate   time.Time
}

func (r memberRecord) toSpec() MemberSpec {
	loanSpecs := make([]LoanSpec, 0, len(r.loans))
	for _, lr := range r.loans {
		loanSpecs = append(loanSpecs, LoanSpec{
			ID:           lr.id,
			BookID:       lr.bookID,
			CheckoutDate: lr.checkoutDate,
			Returned:     lr.returned,
			ReturnDate:   lr.returnDate,
		})
	}
	return MemberSpec{ID: r.id, Loans: loanSpecs}
}

func decomposeMember(member Member) memberRecord {
	loans := member.Loans()
	loanRecs := make([]loanRecord, 0, len(loans))
	for _, loan := range loans {
		returnDate, _ := loan.ReturnDate()
		loanRecs = append(loanRecs, loanRecord{
			id:           loan.ID().String(),
			bookID:       loan.BookID().String(),
			checkoutDate: loan.CheckoutDate(),
			returned:     loan.Returned(),
			returnDate:   returnDate,
		})
	}
	return memberRecord{id: member.ID().String(), loans: loanRecs}
}

type InMemoryMemberRepository struct {
	mu      sync.Mutex
	members map[string]memberRecord
}

func NewInMemoryMemberRepository() *InMemoryMemberRepository {
	return &InMemoryMemberRepository{members: make(map[string]memberRecord)}
}

func (r *InMemoryMemberRepository) Save(ctx context.Context, member Member) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.members[member.ID().String()] = decomposeMember(member)
	return nil
}

func (r *InMemoryMemberRepository) Load(ctx context.Context, id MemberID) (Member, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	rec, ok := r.members[id.String()]
	if !ok {
		return Member{}, ErrMemberNotFound
	}
	member, err := NewMember(rec.toSpec())
	if err != nil {
		return Member{}, fmt.Errorf("reconstruct member %s: %w", id, err)
	}
	return member, nil
}

func (r *InMemoryMemberRepository) FindOverdueLoans(ctx context.Context, asOf time.Time) ([]OverdueLoan, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	var overdue []OverdueLoan
	for _, rec := range r.members {
		member, err := NewMember(rec.toSpec())
		if err != nil {
			return nil, fmt.Errorf("reconstruct member %s: %w", rec.id, err)
		}
		for _, loan := range member.Loans() {
			if loan.IsOverdueAsOf(asOf) {
				overdue = append(overdue, OverdueLoan{MemberID: member.ID(), Loan: loan})
			}
		}
	}
	return overdue, nil
}
