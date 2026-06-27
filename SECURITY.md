# Security

## Reporting a vulnerability

If you find a security issue in this project, please report it privately to the
maintainer through the contact on the GitHub profile rather than opening a public
issue. Please include enough detail to reproduce the problem.

## Responsible use

This is an offensive security tool. Run it only against systems you own or are
explicitly authorized to test. Unauthorized testing of systems you do not control
may be unlawful.

## Controls in this repository

This repository runs static analysis with Bandit and CodeQL, dependency scanning
with pip audit and Dependabot, secret scanning and pre commit hooks, and
continuous integration that lints, type checks, and tests on every push and pull
request.
