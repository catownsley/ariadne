# Autonomous AI Pen Tester

An LLM planner runs an authorized penetration test end to end. It maps a target,
probes for vulnerabilities, confirms findings, and reports. Scope is enforced in
code, not in a prompt, so the agent cannot act outside the rules of engagement,
and every action is written to an audit log.

See [DESIGN.md](DESIGN.md) for the architecture and diagrams.

## Run

Requires Python, an authorized target, and `ANTHROPIC_API_KEY` in the environment.

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python -m pentester.main
```

## Disclaimer

This software is provided as is, without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability, fitness
for a particular purpose, and noninfringement. Use it only against systems you
own or are explicitly authorized to test.

## License

Copyright (C) 2026 Charlotte Townsley.

This program is free software. You can redistribute it and modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, version 3. The full license text is in the LICENSE file and at
https://www.gnu.org/licenses/gpl-3.0.html.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY, without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.
