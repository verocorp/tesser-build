package lending

import (
	"context"
	"errors"
	"fmt"
	"time"
)

type LendingService struct {
	repo MemberRepository
}

func NewLendingService(repo MemberRepository) *LendingService {
	return &LendingService{repo: repo}
}

type CheckOutBookRequest struct {
	MemberID     string
	BookID       string
	CheckoutDate time.Time
}

type CheckOutBookResponse struct {
	LoanID  string
	DueDate time.Time
}

func (s *LendingService) CheckOutBook(ctx context.Context, req CheckOutBookRequest) (CheckOutBookResponse, error) {
	memberID, err := NewMemberID(req.MemberID)
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("invalid member id: %w", err)
	}
	bookID, err := NewBookID(req.BookID)
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("invalid book id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID)
	if errors.Is(err, ErrMemberNotFound) {
		member, err = NewMember(MemberSpec{ID: req.MemberID})
		if err != nil {
			return CheckOutBookResponse{}, fmt.Errorf("create member %s: %w", req.MemberID, err)
		}
	} else if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	loan, err := member.CheckOut(bookID, req.CheckoutDate)
	if err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("check out rejected: %w", err)
	}

	if err := s.repo.Save(ctx, member); err != nil {
		return CheckOutBookResponse{}, fmt.Errorf("persist member %s: %w", req.MemberID, err)
	}

	return CheckOutBookResponse{LoanID: loan.ID().String(), DueDate: loan.DueDate()}, nil
}

type ReturnBookRequest struct {
	MemberID   string
	BookID     string
	ReturnDate time.Time
}

type ReturnBookResponse struct {
	LateFeeCents int64
}

func (s *LendingService) ReturnBook(ctx context.Context, req ReturnBookRequest) (ReturnBookResponse, error) {
	memberID, err := NewMemberID(req.MemberID)
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("invalid member id: %w", err)
	}
	bookID, err := NewBookID(req.BookID)
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("invalid book id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID)
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	fee, err := member.Return(bookID, req.ReturnDate)
	if err != nil {
		return ReturnBookResponse{}, fmt.Errorf("return rejected: %w", err)
	}

	if err := s.repo.Save(ctx, member); err != nil {
		return ReturnBookResponse{}, fmt.Errorf("persist member %s: %w", req.MemberID, err)
	}

	return ReturnBookResponse{LateFeeCents: fee.Cents()}, nil
}

type GetTotalLateFeesRequest struct {
	MemberID string
	AsOf     time.Time
}

type GetTotalLateFeesResponse struct {
	TotalLateFeeCents int64
}

func (s *LendingService) GetTotalLateFees(ctx context.Context, req GetTotalLateFeesRequest) (GetTotalLateFeesResponse, error) {
	memberID, err := NewMemberID(req.MemberID)
	if err != nil {
		return GetTotalLateFeesResponse{}, fmt.Errorf("invalid member id: %w", err)
	}

	member, err := s.repo.Load(ctx, memberID)
	if errors.Is(err, ErrMemberNotFound) {
		return GetTotalLateFeesResponse{TotalLateFeeCents: 0}, nil
	}
	if err != nil {
		return GetTotalLateFeesResponse{}, fmt.Errorf("load member %s: %w", req.MemberID, err)
	}

	total := member.TotalLateFees(req.AsOf)
	return GetTotalLateFeesResponse{TotalLateFeeCents: total.Cents()}, nil
}

type ListOverdueLoansRequest struct {
	AsOf time.Time
}

type OverdueLoanView struct {
	MemberID     string
	BookID       string
	LoanID       string
	CheckoutDate time.Time
	DueDate      time.Time
	DaysOverdue  int64
	LateFeeCents int64
}

type ListOverdueLoansResponse struct {
	Loans []OverdueLoanView
}

func (s *LendingService) ListOverdueLoans(ctx context.Context, req ListOverdueLoansRequest) (ListOverdueLoansResponse, error) {
	records, err := s.repo.FindOverdueLoans(ctx, req.AsOf)
	if err != nil {
		return ListOverdueLoansResponse{}, fmt.Errorf("find overdue loans: %w", err)
	}

	views := make([]OverdueLoanView, 0, len(records))
	for _, rec := range records {
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
	return ListOverdueLoansResponse{Loans: views}, nil
}
