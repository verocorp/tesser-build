package lending

import (
	"context"
	"errors"
	"fmt"
	"time"
)

// LendingService is the application service coordinating the library's
// use cases: check out a book, return a book, total the late fees a
// member owes, and list every overdue loan across the library. It holds
// no business logic of its own — every rule lives on Member and Loan;
// this type only converts, delegates, persists, and responds
// (application-services.md).
type LendingService struct {
	repo MemberRepository // injected — never constructed here
}

// NewLendingService constructs a LendingService over repo.
func NewLendingService(repo MemberRepository) *LendingService {
	return &LendingService{repo: repo}
}

// CheckOutBookRequest is the input to CheckOutBook.
type CheckOutBookRequest struct {
	MemberID     string
	BookID       string
	CheckoutDate time.Time
}

// CheckOutBookResponse is the output of CheckOutBook.
type CheckOutBookResponse struct {
	LoanID  string
	DueDate time.Time
}

// CheckOutBook checks out a book for a member. A member with no prior
// loans is created on first checkout — this domain doesn't otherwise model
// member enrollment as a separate use case.
func (s *LendingService) CheckOutBook(ctx context.Context, req CheckOutBookRequest) (CheckOutBookResponse, error) {
	memberID, err := NewMemberID(req.MemberID) // 1. Convert
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("invalid member id: %w", err)
	}
	bookID, err := NewBookID(req.BookID)
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("invalid book id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID) // 2a. load ...
	if errors.Is(err, ErrMemberNotFound) {
		member, err = NewMember(MemberSpec{ID: req.MemberID})
		if err != nil {
			return CheckOutBookResponse{}, fmt.Errorf("create member %s: %w", req.MemberID, err)
		}
	} else if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	loan, err := member.CheckOut(bookID, req.CheckoutDate) // ... 2b. call the guarded transition
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("check out rejected: %w", err)
	}

	if err := s.repo.Save(ctx, member); err != nil { // 3. Persist (whole aggregate)
		return CheckOutBookResponse{}, fmt.Errorf("persist member %s: %w", req.MemberID, err)
	}

	return CheckOutBookResponse{LoanID: loan.ID().String(), DueDate: loan.DueDate()}, nil // 4. Respond
}

// ReturnBookRequest is the input to ReturnBook.
type ReturnBookRequest struct {
	MemberID   string
	BookID     string
	ReturnDate time.Time
}

// ReturnBookResponse is the output of ReturnBook.
type ReturnBookResponse struct {
	LateFeeCents int64
}

// ReturnBook returns a book a member currently has on loan and reports
// the late fee assessed on it (zero if it wasn't overdue).
func (s *LendingService) ReturnBook(ctx context.Context, req ReturnBookRequest) (ReturnBookResponse, error) {
	memberID, err := NewMemberID(req.MemberID) // 1. Convert
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("invalid member id: %w", err)
	}
	bookID, err := NewBookID(req.BookID)
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("invalid book id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID) // 2a. load ...
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	fee, err := member.Return(bookID, req.ReturnDate) // ... 2b. call the guarded transition
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("return rejected: %w", err)
	}

	if err := s.repo.Save(ctx, member); err != nil { // 3. Persist (whole aggregate)
		return ReturnBookResponse{}, fmt.Errorf("persist member %s: %w", req.MemberID, err)
	}

	return ReturnBookResponse{LateFeeCents: fee.Cents()}, nil // 4. Respond
}

// GetTotalLateFeesRequest is the input to GetTotalLateFees.
type GetTotalLateFeesRequest struct {
	MemberID string
	AsOf     time.Time
}

// GetTotalLateFeesResponse is the output of GetTotalLateFees.
type GetTotalLateFeesResponse struct {
	TotalLateFeeCents int64
}

// GetTotalLateFees reports the total late fees a member currently owes
// across all their overdue loans, as of AsOf. A member who has never
// checked anything out (no saved record) owes nothing.
func (s *LendingService) GetTotalLateFees(ctx context.Context, req GetTotalLateFeesRequest) (GetTotalLateFeesResponse, error) {
	memberID, err := NewMemberID(req.MemberID) // 1. Convert
	if err != nil {
		return GetTotalLateFeesResponse{}, fmt.Errorf("invalid member id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID) // 2. Delegate (load)
	if errors.Is(err, ErrMemberNotFound) {
		return GetTotalLateFeesResponse{TotalLateFeeCents: 0}, nil
	}
	if err != nil {
		return GetTotalLateFeesResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	total := member.TotalLateFees(req.AsOf)                                // the domain computes it, not this loop
	return GetTotalLateFeesResponse{TotalLateFeeCents: total.Cents()}, nil // 4. Respond
}

// ListOverdueLoansRequest is the input to ListOverdueLoans.
type ListOverdueLoansRequest struct {
	AsOf time.Time
}

// OverdueLoanView is one row of ListOverdueLoansResponse: everything about
// one overdue loan a caller needs to display, with the late fee already
// computed by the domain.
type OverdueLoanView struct {
	MemberID     string
	BookID       string
	LoanID       string
	CheckoutDate time.Time
	DueDate      time.Time
	DaysOverdue  int64
	LateFeeCents int64
}

// ListOverdueLoansResponse is the output of ListOverdueLoans.
type ListOverdueLoansResponse struct {
	Loans []OverdueLoanView
}

// ListOverdueLoans lists every overdue loan across the whole library as of
// AsOf, regardless of which member holds it.
func (s *LendingService) ListOverdueLoans(ctx context.Context, req ListOverdueLoansRequest) (ListOverdueLoansResponse, error) {
	records, err := s.repo.FindOverdueLoans(ctx, req.AsOf) // 2. Delegate (query)
	if err != nil {
		return ListOverdueLoansResponse{}, fmt.Errorf("find overdue loans: %w", err)
	}

	views := make([]OverdueLoanView, 0, len(records))
	for _, rec := range records { // Respond: map each domain result to a DTO row; no summing/filtering here
		views = append(views, OverdueLoanView{
			MemberID:     rec.MemberID.String(),
			BookID:       rec.Loan.BookID().String(),
			LoanID:       rec.Loan.ID().String(),
			CheckoutDate: rec.Loan.CheckoutDate(),
			DueDate:      rec.Loan.DueDate(),
			DaysOverdue:  rec.Loan.DaysOverdueAsOf(req.AsOf),
			LateFeeCents: rec.Loan.LateFeeAsOf(req.AsOf).Cents(),
		})
	}
	return ListOverdueLoansResponse{Loans: views}, nil // 4. Respond
}
