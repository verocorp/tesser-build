package lending

import (
	"context"
	"reflect"
	"testing"
	"time"
)

func TestLendingService_CheckOutBook_CreatesMemberOnFirstUse(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()

	resp, err := svc.CheckOutBook(ctx, CheckOutBookRequest{
		MemberID:     "member-1",
		BookID:       "book-1",
		CheckoutDate: day(2026, time.January, 1),
	})
	if err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}
	if resp.LoanID == "" {
		t.Error("CheckOutBook: LoanID is empty, want a generated loan id")
	}
	if want := day(2026, time.January, 15); !resp.DueDate.Equal(want) {
		t.Errorf("CheckOutBook: DueDate = %v, want %v", resp.DueDate, want)
	}
	if reflect.TypeOf(resp) != reflect.TypeOf(CheckOutBookResponse{}) {
		t.Error("CheckOutBook must return a CheckOutBookResponse DTO")
	}
}

func TestLendingService_CheckOutBook_InvalidMemberIDPropagates(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	_, err := svc.CheckOutBook(context.Background(), CheckOutBookRequest{
		MemberID:     "",
		BookID:       "book-1",
		CheckoutDate: day(2026, time.January, 1),
	})
	if err == nil {
		t.Error("CheckOutBook with an empty member id = nil error, want error")
	}
}

func TestLendingService_CheckOutBook_FourthBookRejected(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()
	checkoutDate := day(2026, time.January, 1)

	for i, bookID := range []string{"book-1", "book-2", "book-3"} {
		if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: bookID, CheckoutDate: checkoutDate}); err != nil {
			t.Fatalf("CheckOutBook #%d returned unexpected error: %v", i+1, err)
		}
	}

	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: "book-4", CheckoutDate: checkoutDate}); err == nil {
		t.Error("4th CheckOutBook = nil error, want error")
	}
}

func TestLendingService_ReturnBook_Succeeds_ComputesLateFee(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()

	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{
		MemberID:     "member-1",
		BookID:       "book-1",
		CheckoutDate: day(2026, time.January, 1),
	}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}

	resp, err := svc.ReturnBook(ctx, ReturnBookRequest{
		MemberID:   "member-1",
		BookID:     "book-1",
		ReturnDate: day(2026, time.January, 19),
	})
	if err != nil {
		t.Fatalf("ReturnBook returned unexpected error: %v", err)
	}
	if want := int64(100); resp.LateFeeCents != want {
		t.Errorf("ReturnBook: LateFeeCents = %d, want %d", resp.LateFeeCents, want)
	}
}

func TestLendingService_ReturnBook_UnknownMemberErrors(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	_, err := svc.ReturnBook(context.Background(), ReturnBookRequest{
		MemberID:   "member-1",
		BookID:     "book-1",
		ReturnDate: day(2026, time.January, 1),
	})
	if err == nil {
		t.Error("ReturnBook for an unknown member = nil error, want error")
	}
}

func TestLendingService_ReturnBook_NoActiveLoanRejected(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()
	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: "book-1", CheckoutDate: day(2026, time.January, 1)}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}
	if _, err := svc.ReturnBook(ctx, ReturnBookRequest{MemberID: "member-1", BookID: "book-2", ReturnDate: day(2026, time.January, 2)}); err == nil {
		t.Error("ReturnBook for a book not on loan = nil error, want error")
	}
}

func TestLendingService_GetTotalLateFees_SumsOutstandingOverdueLoans(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()
	checkoutDate := day(2026, time.January, 1)

	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: "book-1", CheckoutDate: checkoutDate}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}
	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: "book-2", CheckoutDate: checkoutDate}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}

	resp, err := svc.GetTotalLateFees(ctx, GetTotalLateFeesRequest{MemberID: "member-1", AsOf: day(2026, time.January, 19)})
	if err != nil {
		t.Fatalf("GetTotalLateFees returned unexpected error: %v", err)
	}
	if want := int64(200); resp.TotalLateFeeCents != want {
		t.Errorf("GetTotalLateFees: TotalLateFeeCents = %d, want %d", resp.TotalLateFeeCents, want)
	}
}

func TestLendingService_GetTotalLateFees_UnknownMemberReturnsZero(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	resp, err := svc.GetTotalLateFees(context.Background(), GetTotalLateFeesRequest{MemberID: "member-1", AsOf: day(2026, time.January, 1)})
	if err != nil {
		t.Fatalf("GetTotalLateFees for an unknown member returned unexpected error: %v", err)
	}
	if resp.TotalLateFeeCents != 0 {
		t.Errorf("GetTotalLateFees for an unknown member: TotalLateFeeCents = %d, want 0", resp.TotalLateFeeCents)
	}
}

func TestLendingService_ListOverdueLoans_AcrossMultipleMembers(t *testing.T) {
	svc := NewLendingService(NewInMemoryMemberRepository())
	ctx := context.Background()
	checkoutDate := day(2026, time.January, 1)

	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-1", BookID: "book-1", CheckoutDate: checkoutDate}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}
	if _, err := svc.CheckOutBook(ctx, CheckOutBookRequest{MemberID: "member-2", BookID: "book-2", CheckoutDate: checkoutDate}); err != nil {
		t.Fatalf("CheckOutBook returned unexpected error: %v", err)
	}
	if _, err := svc.ReturnBook(ctx, ReturnBookRequest{MemberID: "member-2", BookID: "book-2", ReturnDate: day(2026, time.January, 16)}); err != nil {
		t.Fatalf("ReturnBook returned unexpected error: %v", err)
	}

	resp, err := svc.ListOverdueLoans(ctx, ListOverdueLoansRequest{AsOf: day(2026, time.January, 19)})
	if err != nil {
		t.Fatalf("ListOverdueLoans returned unexpected error: %v", err)
	}
	if len(resp.Loans) != 1 {
		t.Fatalf("len(ListOverdueLoans.Loans) = %d, want 1", len(resp.Loans))
	}
	row := resp.Loans[0]
	if row.MemberID != "member-1" || row.BookID != "book-1" {
		t.Errorf("ListOverdueLoans row = %+v, want member-1's book-1 loan", row)
	}
	if row.DaysOverdue != 4 {
		t.Errorf("ListOverdueLoans row.DaysOverdue = %d, want 4", row.DaysOverdue)
	}
	if row.LateFeeCents != 100 {
		t.Errorf("ListOverdueLoans row.LateFeeCents = %d, want 100", row.LateFeeCents)
	}
}
