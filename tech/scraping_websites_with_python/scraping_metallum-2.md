# Scraping Websites with Python

In the [last entry of this series](https://github.com/z3c0/blog/blob/main/tech/scraping_websites_with_python/scraping_metallum-1.md)

## Part 3: Networked Multithreading (using `thread` and `queue`)

### `thread`/`queue` vs `multiprocessing`

In this excercise, we're going to be utilizing the standard libraries `thread` and `queue` - however, there are times when the `multiprocessing` library is a far better choice. [Here's a good blog post on the subject](https://timber.io/blog/multiprocessing-vs-multithreading-in-python-what-you-need-to-know/) to help you understand the very large distinction between the two seemingly-similar approaches.

### Why multithread at all?

By default, Python is a single-threaded language, meaning that one can't *truly* multithread with Python as one would in one of the heftier lower-level languages. This is due to Python's [Global Interpreter Lock](https://realpython.com/python-gil/), or "GIL". In short, the GIL ensures that the Python interpreter is only able to be accessed by one thread at a time, meaning that no matter how many threads you create, they're still going to have to wait their turn to run statements against the Python interpreter. So why do it at all?

Whether or not threading is a good solution for you comes down to the problem that you're trying to solve. The problem we're solving - downloading a set of lists of varying lengths - just so happens to be a problem that is better solved with threading.

Here's a rough count of the number of records for letter A through F:

| letter    | records
|:-         |:-
| A         | 13000
| B         | 9000
| C         | 9000
| D         | 12000
| E         | 7000
| F         | 5000
