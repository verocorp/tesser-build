// Package lending models a small book-lending domain for a library: a
// Member (an aggregate root — the entry point for all their loans, and the
// only place the "at most 3 books on loan at once" invariant can live,
// since it spans the member's whole set of loans) who checks out and
// returns Loans (entities — the system must track each specific checkout
// by identity, since two loans of the same book by the same member on the
// same day are still two different loans), each of which can owe a Money
// late fee (a value object — a whole number of cents, never a float, so it
// never drifts). Members are persisted and reconstructed through a
// MemberRepository (InMemoryMemberRepository in this package), and
// LendingService coordinates the library's use cases: check out a book,
// return a book, total the late fees a member owes, and list every
// overdue loan across the library.
package lending
