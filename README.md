## Simulating concurrent writes to sqlite3 with multiprocessing and pytest ##

I have a frequently-called process that I would like to record some metrics about. I've decided that the process will report its metrics once it has completed its main tasks. 

I do not expect more than 1000 calls to this process per-day.

The schema for the table is simple, the data does not need to be exposed to any other application, and I would like a minimum of connection issues (transient, though they may be). 

How about **sqlite3**?

**POTENTIAL PROBLEM: will this support concurrent writes?**

It *is* possible for 2 or more processes to finish and try to insert records into the data at the same time.   

How many of these inserts can be handled successfully? What is the upper limit?

Let's ask this question in a more technically rigorous way: How many concurrent 1-record inserts can I run on a local sqlite3 database without throwing the `sqlite3.OperationalError: database is locked` exception? 

That is: how do we test _multiple invocations_ of this function at the same time?

    def insert_row(record):
        with sqlite3.connect(PATH_TO_DB) as conn:
            c = conn.cursor()

            c.execute(
                """
                INSERT INTO messages 
                (msg) 
                VALUES
                (?);
                """,
                record,
            )
            conn.commit()


### multiprocessing: a Pythonic Path to Parallelization ###
 
Enter `multiprocessing.Pool.map()`. I'll refer to this as `map()` from here on out.

`map()` has two required arguments: _func_ and _iterable_. (There's a third, optional argument `chunksize` we won't touch on here.) 
According to its Python3.6 docstring:

	Apply `func` to each element in `iterable`, collecting the results
	in a list that is returned.


`insert_row` is the function that is **applied** in this case. 

The iterable `args_list` is a list of one-element tuples. Each tuple contains a serialized UUID4 that will be inserted into the sqlite3 db in the `msg` column.

The call to `map()` spawns the parallel processes and returns the results in a list, one item per process.

The function `insert_rows_in_parallel` looks like this:

    def insert_rows_in_parallel(args_list):
        num_procs = len(args_list)

        print(f"Spawning {num_procs} processes...")

        pool = multiprocessing.Pool(num_procs)

        results = pool.map(insert_row, args_list)

        pool.close()
        pool.join()

        print(f"{num_procs} processes complete.")


The size of the `multiprocessing.Pool` is set by the number of elements in args_list. 

`generate_example_rows()` is a helper function used to provide sample input data.

Creating a batch of 50 unique test records prepped for database insertion looks like:

    test_records = generate_example_rows(50)

Spawn 50 calls to `insert_row` to simulate 50 processes reporting in simultaneously.

    insert_rows_in_parallel(test_records)
 
There are a few other helper functions to do things like:

* create a fresh db: `database.create_table()`
* get the number of rows: `database.row_count()`

We now have the ability to:

* build and tear down the local db
* insert data, both sequentially _and_ in parallel
* verify record counts

Time to tie it all together.

### Using pytest to drive ###

`pytest` is a testing framework that is delightfully easy to get started with. 

Each of my tests will be in the form of a function that lives in `test_parallel_writes.py`.

Here's a snippet to demonstrate.


    import pytest


    from database import create_table, row_count, insert_row
    from utils import insert_rows_in_parallel, generate_example_rows


    def test_adding_5_rows_in_parallel_to_new_db():
        # Create a new `messages` sqlite3 table,
        # dropping it if one already exists.
        create_table()

        assert row_count() == 0

        # Run 5 parallel instances of `insert_rows`
        # by way of `insert_rows_in_parallel`
        insert_rows_in_parallel(generate_example_rows(5))

        assert row_count() == 5


If either `assert` fails, the whole test fails. Because tear down / setup is so easy, we can simulate that this works with a populated database as well.

    def test_adding_10000_rows_sequentially_then_100_rows_in_parallel():
        create_table()

        assert row_count() == 0

        for example_row in generate_example_rows(10000):
            insert_row(example_row)

        assert row_count() == 10000

        insert_rows_in_parallel(generate_example_rows(100))

        assert row_count() == 10100


This could certainly be done without `pytest`, but I find the conventions make it nice to follow.


### Conclusion: Will it Do the Trick? ###

I _did_ finally start hitting failures once I started trying to feed it 500 new records simultaneously. 

In this case, though, I think that is a tradeoff I am willing to live with. 

I have increased confidence that my solution will work once put into a real workload scenario. These tests also give me an idea of when I might start seeing failures. In the unlikely scenario that 500+ processes wanted to write to this database at the same time, there would be a potential for data loss.


### BONUS SECTION: Enabling / Testing WAL Mode ###


After initially publishing this, I learned the sqlite3 supports a WAL (Write-Ahead Logging) mode.

Here are some reasons to give it a try, straight from the [sqlite3 documentation](https://www.sqlite.org/wal.html):

    
    There are advantages and disadvantages to using WAL instead of a rollback journal. Advantages include:

    * WAL is significantly faster in most scenarios.
    * WAL provides more concurrency as readers do not block writers and a writer does not block readers. Reading and writing can proceed concurrently.
    * Disk I/O operations tends to be more sequential using WAL.
    * WAL uses many fewer fsync() operations and is thus less vulnerable to problems on systems where the fsync() system call is broken


Enabling WAL mode is straightforward. I added an optional argument to `create_database`. The implementation now looks like:


    def create_table(enable_wal_mode=False):
        with sqlite3.connect(PATH_TO_DB) as conn:
            c = conn.cursor()

            c.execute("""DROP TABLE IF EXISTS messages;""")
            conn.commit()

            c.execute(
                """
                CREATE TABLE messages (
                    ts DATE DEFAULT (datetime('now','localtime')),
                    msg TEXT 
                );
                """
            )
            conn.commit()

            if enable_wal_mode:
                c.execute("""pragma journal_mode=wal;""")
                conn.commit()


As I understand it, WAL mode mostly helps with concurrent _reads_. My testing showed I wasn't able to succesfully insert more rows in parallel using WAL mode than without. Still something to be cognizant of.


### DOUBLE-PLUS EXTRA BONUS SECTION: Parallelization using concurrent.futures ###

It's worth knowing there is _at least_ one more way of leveraging multiprocessing in the standard library: `concurrent.futures`.

I'll be using the `ProcessPoolExecutor` class to manage parallel execution like so:


    def insert_rows_in_parallel_cf(args_list):
        num_procs = len(args_list)

        print(f"Spawning {num_procs} processes...")

        with concurrent.futures.ProcessPoolExecutor(max_workers=num_procs) as executor:
            executor.map(insert_row, args_list)

        print(f"{num_procs} processes complete.")


That's one tidy API! Just another tool to consider when you need parallel execution.


### Using the Code ###

If you would like to run this locally, clone down the repo, install `pytest` in a virtualenv and run `pytest`.


    git clone git@github.com:joedougherty/sqlite3_concurrent_writes_test_suite.git
    cd sqlite3_concurrent_writes_test_suite
    python3 -m venv venv
    source venv/bin/activate
    python -m pip install pytest
    pytest 


### Further Reading: ###

[multiprocessing.Pool.map documentation](https://docs.python.org/3/library/multiprocessing.html#multiprocessing.pool.Pool.map)

[https://www.sqlite.org/cgi/src/doc/begin-concurrent/doc/begin_concurrent.md](https://www.sqlite.org/cgi/src/doc/begin-concurrent/doc/begin_concurrent.md)

[https://charlesleifer.com/blog/going-fast-with-sqlite-and-python/](https://charlesleifer.com/blog/going-fast-with-sqlite-and-python/)

