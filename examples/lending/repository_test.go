package lending

import (
	"context"
	"errors"
	"testing"
	"time"
)

func TestInMemoryMemberRepository_Load_NotFound(t *testing.T) {
	repo := NewInMemoryMemberRepository()
	_, err := repo.Load(context.Background(), MustNewMemberID("member-1"))
	if !errors.Is(err, ErrMemberNotFound) {
		t.Errorf("Load of an unsaved member: err = %v, want ErrMemberNotFound", err)
	}
}

// TestInMemoryMemberRepository_SaveAndLoad_RoundTrip proves a member with
// both active and returned loans survives Save then Load with every
// invariant (and every loan's state) intact — reconstructed through
// NewMember, not by field-poking.
func TestInMemoryMemberRepository_SaveAndLoad_RoundTrip(t *testing.T) {
	repo := NewInMemoryMemberRepository()
	ctx := context.Background()

	member, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	checkoutDate := day(2026, time.January, 1)
	if _, err := member.CheckOut(MustNewBookID("book-1"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if _, err := member.CheckOut(MustNewBookID("book-2"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if _, err := member.Return(MustNewBookID("book-1"), day(2026, time.January, 5)); err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}

	if err := repo.Save(ctx, member); err != nil {
		t.Fatalf("Save returned unexpected error: %v", err)
	}

	loaded, err := repo.Load(ctx, member.ID())
	if err != nil {
		t.Fatalf("Load returned unexpected error: %v", err)
	}

	if got, want := loaded.ID().String(), member.ID().String(); got != want {
		t.Errorf("loaded ID() = %q, want %q", got, want)
	}
	loans := loaded.Loans()
	if got, want := len(loans), 2; got != want {
		t.Fatalf("len(loaded.Loans()) = %d, want %d", got, want)
	}
	for _, l := range loans {
		if l.BookID().String() == "book-1" && !l.Returned() {
			t.Error("loaded loan for book-1 should have come back Returned")
		}
		if l.BookID().String() == "book-2" && l.Returned() {
			t.Error("loaded loan for book-2 should still be outstanding")
		}
	}
}

func TestInMemoryMemberRepository_Save_Overwrites(t *testing.T) {
	repo := NewInMemoryMemberRepository()
	ctx := context.Background()

	member, err := NewMember(MemberSpec{ID: "member-1"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	if _, err := member.CheckOut(MustNewBookID("book-1"), day(2026, time.January, 1)); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if err := repo.Save(ctx, member); err != nil {
		t.Fatalf("first Save returned unexpected error: %v", err)
	}

	if _, err := member.CheckOut(MustNewBookID("book-2"), day(2026, time.January, 2)); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if err := repo.Save(ctx, member); err != nil {
		t.Fatalf("second Save returned unexpected error: %v", err)
	}

	loaded, err := repo.Load(ctx, member.ID())
	if err != nil {
		t.Fatalf("Load returned unexpected error: %v", err)
	}
	if got, want := len(loaded.Loans()), 2; got != want {
		t.Errorf("len(loaded.Loans()) = %d, want %d (second Save must overwrite, not append)", got, want)
	}
}

// TestInMemoryMemberRepository_FindOverdueLoans_AcrossMultipleMembers
// proves the read query spans every saved member, includes only loans
// that are actually overdue as of the given date, and excludes returned
// loans.
func TestInMemoryMemberRepository_FindOverdueLoans_AcrossMultipleMembers(t *testing.T) {
	repo := NewInMemoryMemberRepository()
	ctx := context.Background()
	checkoutDate := day(2026, time.January, 1) // due 2026-01-15
	asOf := day(2026, time.January, 20)

	overdueMember, err := NewMember(MemberSpec{ID: "member-overdue"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	if _, err := overdueMember.CheckOut(MustNewBookID("book-1"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if err := repo.Save(ctx, overdueMember); err != nil {
		t.Fatalf("Save returned unexpected error: %v", err)
	}

	settledMember, err := NewMember(MemberSpec{ID: "member-settled"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	if _, err := settledMember.CheckOut(MustNewBookID("book-2"), checkoutDate); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if _, err := settledMember.Return(MustNewBookID("book-2"), day(2026, time.January, 16)); err != nil {
		t.Fatalf("Return returned unexpected error: %v", err)
	}
	if err := repo.Save(ctx, settledMember); err != nil {
		t.Fatalf("Save returned unexpected error: %v", err)
	}

	onTimeMember, err := NewMember(MemberSpec{ID: "member-on-time"})
	if err != nil {
		t.Fatalf("NewMember returned unexpected error: %v", err)
	}
	if _, err := onTimeMember.CheckOut(MustNewBookID("book-3"), day(2026, time.January, 15)); err != nil {
		t.Fatalf("CheckOut returned unexpected error: %v", err)
	}
	if err := repo.Save(ctx, onTimeMember); err != nil {
		t.Fatalf("Save returned unexpected error: %v", err)
	}

	got, err := repo.FindOverdueLoans(ctx, asOf)
	if err != nil {
		t.Fatalf("FindOverdueLoans returned unexpected error: %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("len(FindOverdueLoans) = %d, want 1", len(got))
	}
	if got[0].MemberID.String() != "member-overdue" || got[0].Loan.BookID().String() != "book-1" {
		t.Errorf("FindOverdueLoans = %+v, want the overdue member's book-1 loan", got[0])
	}
}
