# Salus

-------

## Background

An application to remove YouTube channels that haven't uploaded recently from
your subscription list.

## Requirements

- Google OAuth client ID & secret from [here](https://console.developers.google.com/)
- Python 3 from [here](https://www.python.org/)

## Usage

`salus.py MAX_AGE` where `MAX_AGE` can be any number followed by `y` for years
or `m` for months.

For example, `salus.py 1y` to remove all channels that haven't posted in over a
year.