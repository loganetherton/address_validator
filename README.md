# Address Validator

This address validator is a simple application designed to showcase
a prospective solution to submitting one or more CSV files,
parsing each, attempting to validate each line as an address,
and then outputting the validation results to `stdout` and,
optionally, to an output CSV file.

## Deps

### Typer

[`Typer` docs](https://typer.tiangolo.com/)

`pip install 'typer[all]'`

Install Typer with [Colorama](https://github.com/tartley/colorama) and 
[Shellingham](https://github.com/sarugaku/shellingham).