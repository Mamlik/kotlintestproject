from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
import sys


class LibraryError(Exception):
    """exception for library operations"""
    pass

VIRTUAL_DAY_SECONDS = 10

@dataclass
class Book:
    title: str
    author: str
    isbn: str
    genre: Optional[str] = None
    available: bool = True


@dataclass
class BorrowRecord:
    user_id: str
    isbn: str
    borrow_date: datetime
    return_date: Optional[datetime] = None


class User(ABC):
    def __init__(self, name: str, user_id: str, email: str):
        self.name = name
        self.user_id = user_id
        self.email = email
        self.borrowed_isbns = []

    @abstractmethod
    def get_max_books(self) -> int:
        pass

    @abstractmethod
    def get_borrow_days(self) -> int:
        pass

    def can_borrow(self, library: "Library") -> bool:
        return (len(self.borrowed_isbns) < self.get_max_books()) and (not self.has_overdue(library))
    
    def has_overdue(self, library: "Library") -> bool:
        today = datetime.now()
        for isbn in self.borrowed_isbns:
            rec = library.active_loans.get(isbn)
            if not rec:
                continue
            due = rec.borrow_date + timedelta(seconds=self.get_borrow_days() * VIRTUAL_DAY_SECONDS)
            if today > due:
                return True
        return False
    
    def get_overdue_isbns(self, library: "Library") -> list[str]:
        res: list[str] = []
        today = datetime.now()
        for isbn in self.borrowed_isbns:
            rec = library.active_loans.get(isbn)
            if not rec:
                continue
            due = rec.borrow_date + timedelta(seconds=self.get_borrow_days() * VIRTUAL_DAY_SECONDS)
            if today > due:
                res.append(isbn)
        return res
    

class Student(User):
    def get_max_books(self) -> int:
        return 3

    def get_borrow_days(self) -> int:
        return 14

class Faculty(User):
    def get_max_books(self) -> int:
        return 10

    def get_borrow_days(self) -> int:
        return 30

class Guest(User):
    def get_max_books(self) -> int:
        return 1

    def get_borrow_days(self) -> int:
        return 7
    

class Library:
    def __init__(self):
        self.books: dict[str, Book] = {} # isbn -> Book
        self.users: dict[str, User] = {} # user_id -> User
        self.books_by_author: dict[str, set[str]] = {} # author -> set of isbns
        self.books_by_title: dict[str, set[str]] = {} # title -> set of isbns

        self.active_loans: dict[str, BorrowRecord] = {} # isbn -> BorrowRecord (active loans)
        self.history: list[BorrowRecord] = []
    
    def _add_to_index(self, d, key: str, isbn: str) -> None:
        if key in d:
            d[key].add(isbn)
        else:
            d[key] = {isbn}

    def _remove_from_index(self, d, key: str, isbn: str) -> None:
        if key in d and isbn in d[key]:
            d[key].remove(isbn)
            if not d[key]:
                del d[key]
    
    def add_book(self, title: str, author: str, isbn: str, genre: Optional[str] = None) -> bool:
        if isbn in self.books:
            raise LibraryError("Book with this ISBN already exists.")
        book = Book(title=title, author=author, isbn=isbn, genre=genre)
        self.books[isbn] = book
        self._add_to_index(self.books_by_author, author.lower().strip(), isbn)
        self._add_to_index(self.books_by_title, title.lower().strip(), isbn)
        return True
    
    def remove_book(self, isbn: str) -> bool:
        book = self.books.get(isbn)
        if not book:
            raise LibraryError("Book with this ISBN does not exist.")
        if not book.available:
            raise LibraryError("Cannot remove a book that is currently borrowed.")
        self._remove_from_index(self.books_by_author, book.author.lower().strip(), isbn)
        self._remove_from_index(self.books_by_title, book.title.lower().strip(), isbn)
        del self.books[isbn]
        return True
    
    def find_book(self, isbn: str) -> Optional[Book]:
        return self.books.get(isbn)
    
    def search_books(self, query: str) -> list[Book]:
        query = query.lower().strip()
        if query in self.books:
            return [self.books[query]]
        if query in self.books_by_author:
            return [self.books[isbn] for isbn in self.books_by_author[query]]
        if query in self.books_by_title:
            return [self.books[isbn] for isbn in self.books_by_title[query]]
        return []
    
    def register_user(self, name: str, user_id: str, email: str, user_type: str) -> bool:
        if user_id in self.users:
            raise LibraryError("User with this ID already exists.")
        user_type = user_type.lower().strip()
        if user_type == "student":
            user = Student(name=name, user_id=user_id, email=email)
        elif user_type == "faculty":
            user = Faculty(name=name, user_id=user_id, email=email)
        elif user_type == "guest":
            user = Guest(name=name, user_id=user_id, email=email)
        else:
            raise LibraryError("Invalid user type.")
        self.users[user_id] = user
        return True
    
    def find_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    def borrow_book(self, user_id: str, isbn: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            raise LibraryError("User not found.")
        book = self.books.get(isbn)
        if not book:
            raise LibraryError("Book not found.")
        if not book.available:
            raise LibraryError("Book is currently not available.")
        if not user.can_borrow(self):
            raise LibraryError("User cannot borrow more books or has overdue books.")
        
        book.available = False
        user.borrowed_isbns.append(isbn)
        borrow_record = BorrowRecord(user_id=user_id, isbn=isbn, borrow_date=datetime.now())
        self.active_loans[isbn] = borrow_record
        return True
    
    def return_book(self, user_id: str, isbn: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            raise LibraryError("User not found.")
        book = self.books.get(isbn)
        if not book:
            raise LibraryError("Book not found.")
        if isbn not in user.borrowed_isbns:
            raise LibraryError("This user did not borrow this book.")
        
        book.available = True
        user.borrowed_isbns.remove(isbn)
        rec = self.active_loans.pop(isbn, None)
        if rec:
            rec.return_date = datetime.now()
            self.history.append(rec)
        else:
            self.history.append(BorrowRecord(user_id=user_id, isbn=isbn, borrow_date=datetime.now(), return_date=datetime.now()))
        return True
    
    def get_overdue(self) -> list[BorrowRecord]:
        today = datetime.now()
        overdue_records: list[BorrowRecord] = []
        for rec in self.active_loans.values():
            user = self.users.get(rec.user_id)
            if not user:
                continue
            due = rec.borrow_date + timedelta(seconds=user.get_borrow_days() * VIRTUAL_DAY_SECONDS)
            if today > due:
                overdue_records.append(rec)
        return overdue_records


#console
def input_nonempty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("Input cannot be empty. Please try again.")

def main_menu(lib: Library):
    while True:
        print("\n=== Library ===")
        print("1) Add book")
        print("2) Remove book")
        print("3) Register user")
        print("4) Borrow book")
        print("5) Return book")
        print("6) Search books (exact ISBN / exact author / exact title; fallback: partial)")
        print("7) List overdue")
        print("0) Exit")
        choice = input("Choice: ").strip()
        try:
            if choice == "1":
                title = input_nonempty("Title: ")
                author = input_nonempty("Author: ")
                isbn = input_nonempty("ISBN: ")
                genre = input("Genre (optional): ").strip() or None
                ok = lib.add_book(title, author, isbn, genre)
                print("Added." if ok else "ISBN already exists.")
            elif choice == "2":
                isbn = input_nonempty("ISBN to remove: ")
                ok = lib.remove_book(isbn)
                print("Removed." if ok else "Cannot remove (not found or borrowed).")
            elif choice == "3":
                name = input_nonempty("Name: ")
                user_id = input_nonempty("User ID: ")
                email = input_nonempty("Email: ")
                print("Types: student, faculty, guest")
                utype = input_nonempty("Type: ")
                ok = lib.register_user(name, user_id, email, utype)
                print("Registered." if ok else "Failed (maybe ID exists or invalid type).")
            elif choice == "4":
                uid = input_nonempty("User ID: ")
                isbn = input_nonempty("ISBN: ")
                ok = lib.borrow_book(uid, isbn)
                print("Borrowed." if ok else "Cannot borrow (check user/book/limits/availability).")
            elif choice == "5":
                uid = input_nonempty("User ID: ")
                isbn = input_nonempty("ISBN: ")
                ok = lib.return_book(uid, isbn)
                print("Returned." if ok else "Cannot return (book not borrowed by user?).")
            elif choice == "6":
                q = input_nonempty("Search query (exact title/author/isbn preferred): ")
                found = lib.search_books(q)
                if not found:
                    print("No results.")
                else:
                    for b in found:
                        print(f"{b.isbn} | {b.title} by {b.author} | {'Available' if b.available else 'Borrowed'}")
            elif choice == "7":
                overdue = lib.get_overdue()
                if not overdue:
                    print("No overdue books.")
                else:
                    for r in overdue:
                        user = lib.find_user(r.user_id)
                        due = r.borrow_date + timedelta(seconds=user.get_borrow_days() * VIRTUAL_DAY_SECONDS) if user else "?"
                        print(f"{r.isbn} borrowed by {r.user_id} on {r.borrow_date} due {due}")
            elif choice == "0":
                print("Bye")
                break
            else:
                print("Invalid choice.")
        except LibraryError as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")



if __name__ == "__main__":
    library = Library()
    library.add_book("Book 1", "Autor 1", "9155", "Programming")
    library.add_book("Book2", "Autor 1", "0266", "Programming")
    library.register_user("Sasha", "123", "sasha@yandex.ru", "guest")

    try:
        main_menu(library)
    except KeyboardInterrupt:
        print("\nExit.")
        sys.exit(0)
