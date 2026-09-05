#!/usr/bin/env python3
"""Render a planning instance's prose statement FROM its solver parameters.

WHY THIS EXISTS
---------------
`make_planning_sources.py` used a hand-written statement beside each parameter
dict and a `check_statement_matches_params` parser to catch them disagreeing.
That is the right instinct -- a statement saying a cell is blocked while the
builder was handed a different set produces a source whose gold plan does not
answer the question asked -- but it scales badly: every new instance is two
hand-written artefacts plus a parser branch to keep them honest.

Rendering the statement from the parameters removes the failure mode instead of
detecting it.  There is one artefact, so there is nothing to disagree with.
`check_statement_matches_params` is kept as a redundant check over the rendered
text; it should now be incapable of firing, which is the point.
"""
from __future__ import annotations

from typing import Any

BLOCKS_ACTIONS = (
    "Primitive actions are pick up X from table, put down X on table, "
    "unstack X from Y, and stack X on Y."
)
LOGISTICS_ACTIONS = (
    "Primitive actions are load P into V at L, unload P from V at L, "
    "drive T from L1 to L2 (within one city), and fly A from L1 to L2 "
    "(airport to airport)."
)


def _english_list(items: list[str]) -> str:
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _blocks_statement(p: dict[str, Any]) -> str:
    on, on_table = p["on"], set(p["on_table"])
    blocks, holding = p["blocks"], p.get("holding")
    supported = set(on.values())
    clear = sorted(set(blocks) - supported - ({holding} if holding else set()))

    facts = [f"{top} is on {support}" for top, support in sorted(on.items())]
    facts += [f"{b} is on the table" for b in sorted(on_table)]
    initial = "Initially " + ", ".join(facts)
    initial += f", {_english_list(clear)} {'is' if len(clear) == 1 else 'are'} clear"
    initial += f", and the arm is {'holding ' + holding if holding else 'empty'}."

    goals = [f"{top} on {support}" for top, support in sorted(p["goals_on"].items())]
    for b in sorted(p.get("goals_clear") or []):
        goals.append(f"{b} clear")
    return (
        f"Blocks task. {initial} {BLOCKS_ACTIONS} "
        f"Goal: {_english_list(goals)}. Give a valid primitive-action plan."
    )


def _logistics_statement(p: dict[str, Any]) -> str:
    cities, airports = p["cities"], p["airports"]
    city_bits = []
    for city in sorted(cities):
        locs = list(cities[city])
        city_bits.append(
            f"{city} contains {_english_list(sorted(locs))}, of which "
            f"{airports[city]} is the airport"
        )
    where = [
        f"{t} starts at {loc}" for t, loc in sorted(p["trucks"].items())
    ] + [
        f"{a} starts at {loc}" for a, loc in sorted(p["airplanes"].items())
    ] + [
        f"{pkg} starts at {loc}" for pkg, loc in sorted(p["packages"].items())
    ]
    goals = [f"{pkg} at {loc}" for pkg, loc in sorted(p["goals"].items())]
    return (
        "Logistics task. "
        + "; ".join(city_bits)
        + ". A truck may only drive between locations in its own city, and an "
        "airplane may only fly between airports. A package that is loaded into a "
        "vehicle is inside it, not at a location, so it must be unloaded before "
        "it can be loaded into a different vehicle. "
        + "Positions: " + ", ".join(where)
        + f". {LOGISTICS_ACTIONS} "
        f"Goal: {_english_list(goals)}. Give a valid primitive-action plan."
    )


RENDERERS = {
    "plan_blocks": _blocks_statement,
    "plan_logistics": _logistics_statement,
}


def render_statement(family: str, params: dict[str, Any]) -> str:
    try:
        return RENDERERS[family](params)
    except KeyError:
        raise KeyError(f"no statement renderer for family {family!r}") from None
