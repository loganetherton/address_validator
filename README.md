# Address Validator

This address validator is a simple application designed to showcase a prospective solution to 
submitting one or more CSV files, parsing each, attempting to validate each line as an address,
and then outputting the validation results to `stdout` and, optionally, to an output CSV file.

The `Typer` library is used as a framework for the CLI interface. `Typer` makes use of
type hinting to automate away most of the setup, `argv` parsing, and documentation of
CLI applications. However, it does not, by default, handle `async` functions, as the
decorators provided by `Typer` return a response as soon as execution of the wrapped function
completes. To address this, an intermediary `async` function is wrapped in the outer
function decorated by `Typer`.

To address the issue of multiple addresses being validated during a single run, the
[`asyncio.gather`](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather) function 
is used. This function accepts a list of async function called and pauses execution when 
encountering an `await` statement until all `async` function calls in the list have completed,
guaranteeing ordered responses and allowing for the ordering of output values, both to `stdout`
and to an output CSV.

The unit test suite covers the major error cases, such as missing CSV files, missing
CSV headers, as well as the major success cases, such as successfully waiting for the rate
limiting window to conclude and a new rate limiting batch to begin, successful caching,
and successful new validation requests.

## Setup

### Environment Variables

Create a file called `.env` and populate it with the keys found in `.template-env`. Insert
values as necessary. Values for Redis-related keys can be left blank, or the keys can be removed, 
as the default values are configured to work with a `docker-compose` build.

### CSV Files

Once the appropriate values are in the `.env` file, put any desired CSV files into the directory 
`csv/` before starting the Docker containers. By default, the CLI interface will run addresses
from all non-header lines in all CSVs found in the `csv/` directory.

## Containers

The Docker composition is comprised of two containers: one for the application logic,
and one for Redis, which acts as a cache to prevent duplicate requests.

The application itself is built using the [`Typer`](https://typer.tiangolo.com/) library,
which is itself built on the [`Click`](https://click.palletsprojects.com/en/8.1.x/) library,
created for [`Flask`](https://flask.palletsprojects.com/en/2.1.x/).

The Redis container will start up first, and once that is complete, the application container
will start. Redis is not strictly required for successful usage. However, by including
Redis as a cache, we can prevent duplicate requests. Only exact requests which have been seen
before will be returned from cache, as even minor changes in the incoming address result in
differing responses from the validation API.

## Testing

During the build phase, all unit tests will be run. These tests were built using the
[`pytest`](https://docs.pytest.org/en/7.1.x/) framework. During testing, responses are mocked
using the [`responses`](https://github.com/getsentry/responses) library. Due to the nature of
the application being written for CLI usage, the validation function typically called via
`Typer` is instead imported and called directly in the `pytest` suite.

## Start

When setup is complete, run the application via `docker-compose` (or `docker compose`) as 
follows:

```
docker-compose up
```

If you wish to recreate both containers and not use any cached values, enter:

```
docker-compose up --build
```

## Dependencies

### Typer

[Documentation](https://typer.tiangolo.com/)

`Typer` is the primary application library, which serves as a framework for Python CLI 
applications. Typer makes use of type hinting to eliminate boilerplate code for CLI
applications. 

`Typer` comes with a couple of optional dependencies, which serve as niceties when running
CLI applications in differing environments. This is the default installation in the
`requirements.txt` file. To install `Typer` with both optional dependencies, run:

`pip install 'typer[all]'`

This will install [Colorama](https://github.com/tartley/colorama), which handles terminal
formatting and colors, and [Shellingham](https://github.com/sarugaku/shellingham), which
attempts to abstract away the variables in different environments (`POSIX`, `COMPSEC`, etc).

### pytest

The library on which the suite of unit tests is built is 
[`pytest`](https://docs.pytest.org/en/7.1.x/), a simple but mature unit testing framework
for Python applications. All files that follow the glob `test_*` will be gathered and run
as containing unit tests.

Environment variables are set during unit testing via 
[`pytest-env`](https://github.com/MobileDynasty/pytest-env).

### Responses

During testing, HTTP request responses are mocked by the 
[`responses`](https://github.com/getsentry/responses) library, which shims `requests`
to allow for the construction of expected responses.

### redis-py

Redis connection and operations are handled by the 
[`redis-py`](https://github.com/redis/redis-py) library.