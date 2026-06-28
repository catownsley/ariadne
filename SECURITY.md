# Security

## Reporting a vulnerability

If you find a security issue in this project, please report it privately to the maintainer through the contact on the GitHub profile rather than opening a public issue. Please include enough detail to reproduce the problem.

## Responsible use

This is an offensive security tool. Run it only against systems you own or are explicitly authorized to test. Unauthorized testing of systems you do not control may be unlawful.

## Built in safety controls

Ariadne is a command line agent that makes outbound requests, so its safety model guards what the agent is allowed to do rather than protecting an inbound API. The runtime controls of a web service, such as authentication, session tokens, CORS, and security headers, do not apply here. The controls that do apply are these.

| Control | Where it lives |
|---|---|
| Scope allowlist enforced in code | The ScopeGuard checks every request host and port against the allowed list before the request is sent, in pentester/safety.py |
| Append only audit log | Every action is written as one JSON object per line, in pentester/safety.py |
| Per host request budget | The ScopeGuard caps how many requests can reach any one host |
| Outbound rate limiting | A bounded semaphore and a per second throttle bound concurrency and pace, in pentester/tools.py |
| Untrusted responses | Response bodies are handled as data and never as instructions to the agent, in pentester/tools.py |
| No secrets in the repository | The API key is read from the environment and is never written to a file |

## Threat model

A full threat model is in THREAT_MODEL.md. It models the agent threat surface with STRIDE, with the OWASP Top 10 for LLM Applications, and with MITRE ATLAS, and it separates the controls that exist in code today from the hardening that is planned.

## Automated security scanning

| Scan | Tool | When | Mode |
|---|---|---|---|
| Static analysis | CodeQL | Pull request and push to main | Python queries, results in the Security tab |
| Static analysis | Bandit | Pull request and push to main | All severities, uploaded as SARIF |
| Dependency vulnerabilities | pip-audit | Pull request and push to main | Audits the declared dependencies |
| Static analysis, deep | CodeQL | Nightly | Security and quality query suite |
| Static analysis, deep | Bandit | Nightly | Medium severity and confidence, fails the build |
| Dependency vulnerabilities, deep | pip-audit | Nightly | Strict, fails the build on any finding |

The quick scans run on every pull request and on every push to main. The deep scans run nightly and are stricter, so they fail the build where the quick scans only report. Continuous integration also lints with ruff, checks formatting with black, type checks with mypy, and runs the tests.

## Supply chain integrity

The file requirements.lock pins every direct and transitive dependency to an exact version and a set of SHA256 hashes. Continuous integration verifies those hashes with a require hashes dry run install, so a tampered or swapped package on the index fails the build. A lock file sync check regenerates the lock from requirements.txt and fails if the committed lock has drifted, which keeps the pinned set honest. After you change a dependency, regenerate the lock with the following.

    pip-compile --generate-hashes --no-annotate --output-file=requirements.lock requirements.txt

## Dependency updates

Dependabot opens grouped weekly pull requests for the Python packages and for the GitHub Actions. Minor and patch updates are grouped and merge automatically once the checks pass, through the Dependabot auto merge workflow. Major updates arrive as separate pull requests for deliberate review.

## Branch protection

The main branch is protected. It blocks force pushes and deletion, it requires a pull request before merging, and it requires the lint and test job, CodeQL, Bandit, pip-audit, and the lock file sync to pass before anything can merge. Auto merge is enabled on the repository, which is what lets the Dependabot minor and patch updates land on their own once those required checks are green.

## Local security checks

```
source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check .
black --check .
mypy pentester
bandit -r pentester
pip-audit -r requirements.txt
pytest
```
