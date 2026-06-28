# Copyright (C) 2026 Charlotte Townsley
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Tests for the exploration graph and the typed findings."""

from pentester.context import (
    Context,
    InformationDisclosureFinding,
    SQLInjectionFinding,
    XSSFinding,
)


def test_graph_is_rooted():
    ctx = Context(target_base_url="http://target")
    assert "/" in ctx.nodes


def test_frontier_tracks_where_we_have_not_been():
    ctx = Context(target_base_url="http://target")
    ctx.mark_reached("/login", 200)
    # Reached but no parameters mapped, so the frontier flags it.
    assert any("/login" in item for item in ctx.frontier())

    ctx.add_params("/login", ["username"])
    ctx.mark_tested("/login", "sqli", "clear")
    # One vector still untested, so it stays on the frontier.
    assert any("xss" in item for item in ctx.frontier())

    ctx.mark_tested("/login", "xss", "clear")
    # Fully tested, so /login leaves the frontier.
    assert not any("/login" in item for item in ctx.frontier())


def test_typed_findings_carry_their_own_metadata():
    assert SQLInjectionFinding.cwe == "CWE-89"
    assert XSSFinding.cwe == "CWE-79"
    assert InformationDisclosureFinding.cwe == "CWE-200"

    f = SQLInjectionFinding(url="http://target/search", evidence="sql error returned")
    assert f.severity == "high"
    assert f.title == "SQL Injection"
    assert f.remediation


def test_findings_attach_to_their_node():
    ctx = Context(target_base_url="http://target")
    ctx.add_finding(
        InformationDisclosureFinding(
            url="http://target/api/Feedbacks",
            evidence="returned all records without auth",
            confirmed=True,
        )
    )
    assert len(ctx.findings) == 1
    assert ctx.findings[0].confirmed
