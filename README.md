# Library Management System (Python)
Учебная библиотечная система на Python.  
Поддерживает хранение книг, быстрый поиск и базовые операции с коллекцией.
## Возможности
- Добавление книг с указанием:
  - названия
  - автора
  - ISBN
  - жанра (опционально)
- Удаление книг (по ISBN)
- Поиск:
  - по ISBN — `O(1)`
  - по автору — `O(1)`
  - по названию — `O(1)`
- Проверка доступности книги (флаг `available`)

## Использование

```python
from library import Library

lib = Library()

# Добавляем книги
lib.add_book("Война и мир", "Л. Толстой", "1111")
lib.add_book("Анна Каренина", "Л. Толстой", "2222")

# Поиск
book = lib.find_book("1111")  # поиск по ISBN
print(book)

# Поиск по автору
books = lib.books_by_author.get("л. толстой")
print([lib.books[isbn] for isbn in books])

# Удаление
lib.remove_book("2222")
```
## СТруктура проекта
```
User
  -Guest
  -Student
  -Faculty
Library
  -add/remove book
  -search book
  -register user
  -borrow/return book
  -get overdue books
Book
Borrow Record
  -user id
  -isbn
