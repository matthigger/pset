"""Derive the package version from the installed metadata."""

from importlib.metadata import PackageNotFoundError, version

# read from the installed metadata rather than repeating the number here,
# where it drifts from pyproject.toml the first time one of them is bumped
try:
    __version__ = version('pset')
except PackageNotFoundError:
    __version__ = '0+unknown'
