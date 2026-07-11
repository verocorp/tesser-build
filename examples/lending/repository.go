package lending

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"
)

// ErrMemberNotFound is returned by Load when no member with the given ID
// has been saved yet.
var ErrMemberNotFound = errors.New("lending: member not found")

// MemberRepository is the persistence boundary for the Member aggregate:
// it moves whole Members between the domain and storage. It also answers
// the one read concern that spans every member — which loans are overdue
// right now — as a projection, never as domain computation
// (repositories.md).
type MemberRepository interface {
	// Save persists the whole member; the repository decomposes it into
	// storage, never the caller.
	Save(ctx context.Context, member Member) error
	// Load reconstructs a member by identity through NewMember, so every
	// invariant is re-established on the way out.
	Load(ctx context.Context, id MemberID) (Member, error)
	// FindOverdueLoans is a read concern spanning every member: a
	// persistence-selection filter (which loans are overdue as of asOf),
	// answered by asking each Loan itself via IsOverdueAsOf rather than
	// deciding the rule in the repository. Returns a projection, not a
	// domain aggregate.
	FindOverdueLoans(ctx context.Context, asOf time.Time) ([]OverdueLoan, error)
}

// OverdueLoan is a read projection pairing one overdue Loan with the
// member who owes it. It is not a Spec (its leaves are domain value
// objects, not primitives) and not an aggregate (it enforces no invariant
// of its own; it just carries a query result across the boundary).
type OverdueLoan struct {
	MemberID MemberID
	Loan     Loan
}

// memberRecord and loanRecord are storage rows, shaped by persistence, not
// by the domain (value-objects.md's "persistence/row model" near-miss).
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

// decomposeMember flattens a Member into storage rows. It is the single
// site that knows the aggregate's internal shape; callers (the service,
// other repository methods) never extract children themselves.
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

// InMemoryMemberRepository is an in-memory MemberRepository: a map keyed
// by identity, safe for concurrent use. A database-backed implementation
// would satisfy the same interface.
type InMemoryMemberRepository struct {
	mu      sync.Mutex
	members map[string]memberRecord
}

// NewInMemoryMemberRepository constructs an empty in-memory repository.
func NewInMemoryMemberRepository() *InMemoryMemberRepository {
	return &InMemoryMemberRepository{members: make(map[string]memberRecord)}
}

// Save persists the whole member, overwriting any previously saved state
// for the same MemberID.
func (r *InMemoryMemberRepository) Save(ctx context.Context, member Member) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.members[member.ID().String()] = decomposeMember(member)
	return nil
}

// Load reconstructs a member by identity through NewMember, or returns
// ErrMemberNotFound if nothing has been saved for id yet.
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

// FindOverdueLoans reconstructs every saved member and returns the loans
// among them that are overdue as of asOf, each paired with its member.
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
