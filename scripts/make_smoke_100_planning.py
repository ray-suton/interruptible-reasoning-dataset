#!/usr/bin/env python3
"""Generate BlocksWorld and Logistics candidates for the smoke-100 batch.

DOMAIN CHOICE
-------------
Two recognised planning domains rather than the five homegrown families the
pilot used (grid / door / delivery / crate).  `converged_paper_plan.md` names
BlocksWorld and Logistics; they are IPC/PlanBench domains, so a reader placing
this dataset does not have to take our word for what the task is.

Instances are still *generated* rather than imported.  That is deliberate and it
is the property the plan calls decisive: admission requires the target model to
solve the base task with no update, so difficulty has to be dialled until that
holds.  A fixed imported instance set cannot be dialled, and
`docs/source_import_policy.md` would additionally require a provenance review
before its raw text could land here.  Generated-in-a-standard-domain gets the
recognisability without either cost.

Every statement is rendered from the solver parameters
(`scripts/planning_statements.py`), so a statement cannot disagree with the
problem it describes.  Every gold plan comes from BFS and is re-executed before
it is emitted; nothing is typed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from planning_domains import execute_plan, format_plan, make_problem, solve_bfs
from planning_statements import render_statement

BLOCK_NAMES = ("A", "B", "C", "D", "E")

# --- BlocksWorld -----------------------------------------------------------
# Varied along the axes that change what is falsifiable: how deep the initial
# tower is, whether the goal inverts it, and whether a block must be moved out
# of the way before the goal tower can be built bottom-up.
BLOCKS_SPECS: list[dict[str, Any]] = [
    dict(blocks=("A","B","C","D"), on={"D":"C"}, on_table={"A","B","C"},
         holding=None, goals_on={"A":"B","B":"C"}),
    dict(blocks=("A","B","C"), on={"A":"B","B":"C"}, on_table={"C"},
         holding=None, goals_on={"C":"B","B":"A"}),
    dict(blocks=("A","B","C","D"), on={"B":"A","D":"C"}, on_table={"A","C"},
         holding=None, goals_on={"A":"D","C":"B"}),
    dict(blocks=("A","B","C","D"), on={"C":"B","B":"A"}, on_table={"A","D"},
         holding=None, goals_on={"D":"C","C":"A"}),
    dict(blocks=("A","B","C","D","E"), on={"E":"D"}, on_table={"A","B","C","D"},
         holding=None, goals_on={"A":"B","B":"C","C":"D"}),
    # C is in the gripper, so it is NOT on the table. The first version listed it
    # in both, which describes an impossible world; planning_domains now refuses
    # it. Changing the spec changes the content-derived id, so this is a NEW
    # instance and is unscreened until a run covers it.
    dict(blocks=("A","B","C","D"), on={"A":"B"}, on_table={"B","D"},
         holding="C", goals_on={"C":"D","D":"A"}),
    dict(blocks=("A","B","C","D"), on={"D":"A","A":"B"}, on_table={"B","C"},
         holding=None, goals_on={"B":"C","A":"B"}),
    dict(blocks=("A","B","C","D","E"), on={"B":"A","D":"C"}, on_table={"A","C","E"},
         holding=None, goals_on={"E":"B","B":"D"}),
    dict(blocks=("A","B","C"), on={"C":"A"}, on_table={"A","B"},
         holding=None, goals_on={"A":"B","B":"C"}),
    dict(blocks=("A","B","C","D"), on={"B":"C","C":"D"}, on_table={"A","D"},
         holding=None, goals_on={"D":"B","A":"D"}),
    dict(blocks=("A","B","C","D"), on={"A":"C"}, on_table={"B","C","D"},
         holding=None, goals_on={"B":"A","D":"B"}),
    dict(blocks=("A","B","C","D","E"), on={"C":"B","E":"D"}, on_table={"A","B","D"},
         holding=None, goals_on={"A":"C","C":"E"}),
    dict(blocks=("A","B","C","D"), on={"D":"B","B":"A"}, on_table={"A","C"},
         holding=None, goals_on={"C":"D","A":"C"}),
    dict(blocks=("A","B","C"), on={"B":"A"}, on_table={"A","C"},
         holding=None, goals_on={"A":"C","C":"B"}),
]

# --- Logistics -------------------------------------------------------------
def _city(name: str, n_depots: int = 1) -> tuple[dict, dict]:
    locs = tuple([f"{name}_airport"] + [f"{name}_depot{i+1}" for i in range(n_depots)])
    return {name: locs}, {name: f"{name}_airport"}


def _logistics(spec: dict[str, Any]) -> dict[str, Any]:
    cities: dict[str, tuple] = {}
    airports: dict[str, str] = {}
    for name, n in spec["cities"]:
        c, a = _city(name, n)
        cities.update(c)
        airports.update(a)
    return dict(cities=cities, airports=airports, trucks=spec["trucks"],
                airplanes=spec["airplanes"], packages=spec["packages"],
                goals=spec["goals"])


LOGISTICS_SPECS: list[dict[str, Any]] = [
    _logistics(dict(cities=[("lisbon",1),("oslo",1)],
                    trucks={"truck_lis":"lisbon_depot1","truck_osl":"oslo_airport"},
                    airplanes={"plane1":"lisbon_airport"},
                    packages={"pkg1":"lisbon_depot1"}, goals={"pkg1":"oslo_depot1"})),
    _logistics(dict(cities=[("lisbon",1),("oslo",1)],
                    trucks={"truck_lis":"lisbon_airport","truck_osl":"oslo_depot1"},
                    airplanes={"plane1":"oslo_airport"},
                    packages={"pkg1":"lisbon_depot1"}, goals={"pkg1":"oslo_depot1"})),
    _logistics(dict(cities=[("kyoto",2),("perth",1)],
                    trucks={"truck_kyo":"kyoto_depot2","truck_per":"perth_airport"},
                    airplanes={"plane1":"kyoto_airport"},
                    packages={"pkg1":"kyoto_depot1"}, goals={"pkg1":"perth_depot1"})),
    _logistics(dict(cities=[("kyoto",1),("perth",1)],
                    trucks={"truck_kyo":"kyoto_depot1","truck_per":"perth_depot1"},
                    airplanes={"plane1":"kyoto_airport"},
                    packages={"pkg1":"kyoto_depot1","pkg2":"perth_depot1"},
                    goals={"pkg1":"perth_depot1","pkg2":"kyoto_depot1"})),
    _logistics(dict(cities=[("cairo",1),("dublin",1)],
                    trucks={"truck_cai":"cairo_depot1","truck_dub":"dublin_depot1"},
                    airplanes={"plane1":"dublin_airport"},
                    packages={"pkg1":"cairo_depot1"}, goals={"pkg1":"dublin_depot1"})),
    _logistics(dict(cities=[("cairo",2),("dublin",1)],
                    trucks={"truck_cai":"cairo_airport","truck_dub":"dublin_airport"},
                    airplanes={"plane1":"cairo_airport"},
                    packages={"pkg1":"cairo_depot2"}, goals={"pkg1":"dublin_depot1"})),
    _logistics(dict(cities=[("lima",1),("nairobi",1)],
                    trucks={"truck_lim":"lima_depot1","truck_nai":"nairobi_airport"},
                    airplanes={"plane1":"nairobi_airport"},
                    packages={"pkg1":"lima_airport"}, goals={"pkg1":"nairobi_depot1"})),
    _logistics(dict(cities=[("lima",1),("nairobi",1)],
                    trucks={"truck_lim":"lima_airport","truck_nai":"nairobi_depot1"},
                    airplanes={"plane1":"lima_airport"},
                    packages={"pkg1":"lima_depot1","pkg2":"lima_depot1"},
                    goals={"pkg1":"nairobi_depot1","pkg2":"lima_airport"})),
    _logistics(dict(cities=[("oporto",2),("bergen",1)],
                    trucks={"truck_opo":"oporto_depot1","truck_ber":"bergen_depot1"},
                    airplanes={"plane1":"oporto_airport"},
                    packages={"pkg1":"oporto_depot2"}, goals={"pkg1":"bergen_depot1"})),
    _logistics(dict(cities=[("oporto",1),("bergen",1)],
                    trucks={"truck_opo":"oporto_depot1","truck_ber":"bergen_airport"},
                    airplanes={"plane1":"bergen_airport"},
                    packages={"pkg1":"oporto_depot1","pkg2":"bergen_airport"},
                    goals={"pkg1":"bergen_depot1","pkg2":"oporto_depot1"})),
    _logistics(dict(cities=[("quito",1),("tromso",1)],
                    trucks={"truck_qui":"quito_airport","truck_tro":"tromso_airport"},
                    airplanes={"plane1":"quito_airport"},
                    packages={"pkg1":"quito_depot1"}, goals={"pkg1":"tromso_depot1"})),
    _logistics(dict(cities=[("quito",2),("tromso",1)],
                    trucks={"truck_qui":"quito_depot2","truck_tro":"tromso_depot1"},
                    airplanes={"plane1":"tromso_airport"},
                    packages={"pkg1":"quito_depot1"}, goals={"pkg1":"tromso_depot1"})),
    _logistics(dict(cities=[("hanoi",1),("malmo",1)],
                    trucks={"truck_han":"hanoi_depot1","truck_mal":"malmo_depot1"},
                    airplanes={"plane1":"hanoi_airport"},
                    packages={"pkg1":"hanoi_depot1","pkg2":"hanoi_airport"},
                    goals={"pkg1":"malmo_depot1","pkg2":"malmo_depot1"})),
    _logistics(dict(cities=[("hanoi",1),("malmo",2)],
                    trucks={"truck_han":"hanoi_airport","truck_mal":"malmo_depot2"},
                    airplanes={"plane1":"malmo_airport"},
                    packages={"pkg1":"hanoi_depot1"}, goals={"pkg1":"malmo_depot1"})),
]


# Screening at Qwen3-14B-FP8 solved 14/14 blocks and 7/14 logistics, with every
# logistics failure at a gold plan of 10 actions or more.  Difficulty is the dial
# the generated-instance choice exists to provide, so the second tier stays
# inside the band that admitted: one package, one depot per city, and a start
# that does not require a truck leg at both ends.
LOGISTICS_SPECS += [
    _logistics(dict(cities=[("accra",1),("riga",1)],
                    trucks={"truck_acc":"accra_depot1","truck_rig":"riga_airport"},
                    airplanes={"plane1":"accra_airport"},
                    packages={"pkg1":"accra_airport"}, goals={"pkg1":"riga_airport"})),
    _logistics(dict(cities=[("accra",1),("riga",1)],
                    trucks={"truck_acc":"accra_airport","truck_rig":"riga_airport"},
                    airplanes={"plane1":"accra_airport"},
                    packages={"pkg1":"accra_depot1"}, goals={"pkg1":"riga_airport"})),
    _logistics(dict(cities=[("sofia",1),("davao",1)],
                    trucks={"truck_sof":"sofia_airport","truck_dav":"davao_airport"},
                    airplanes={"plane1":"sofia_airport"},
                    packages={"pkg1":"sofia_airport"}, goals={"pkg1":"davao_depot1"})),
    _logistics(dict(cities=[("sofia",1),("davao",1)],
                    trucks={"truck_sof":"sofia_depot1","truck_dav":"davao_airport"},
                    airplanes={"plane1":"sofia_airport"},
                    packages={"pkg1":"sofia_depot1"}, goals={"pkg1":"davao_airport"})),
    _logistics(dict(cities=[("tunis",1),("galway",1)],
                    trucks={"truck_tun":"tunis_airport","truck_gal":"galway_depot1"},
                    airplanes={"plane1":"galway_airport"},
                    packages={"pkg1":"tunis_airport"}, goals={"pkg1":"galway_depot1"})),
    _logistics(dict(cities=[("tunis",1),("galway",1)],
                    trucks={"truck_tun":"tunis_depot1","truck_gal":"galway_airport"},
                    airplanes={"plane1":"tunis_airport"},
                    packages={"pkg1":"tunis_airport"}, goals={"pkg1":"galway_depot1"})),
    _logistics(dict(cities=[("minsk",1),("belem",1)],
                    trucks={"truck_min":"minsk_airport","truck_bel":"belem_airport"},
                    airplanes={"plane1":"minsk_airport"},
                    packages={"pkg1":"minsk_depot1"}, goals={"pkg1":"belem_airport"})),
    _logistics(dict(cities=[("minsk",1),("belem",1)],
                    trucks={"truck_min":"minsk_airport","truck_bel":"belem_depot1"},
                    airplanes={"plane1":"belem_airport"},
                    packages={"pkg1":"minsk_airport"}, goals={"pkg1":"belem_depot1"})),
    _logistics(dict(cities=[("ankara",1),("cusco",1)],
                    trucks={"truck_ank":"ankara_airport","truck_cus":"cusco_airport"},
                    airplanes={"plane1":"ankara_airport"},
                    packages={"pkg1":"ankara_depot1"}, goals={"pkg1":"cusco_depot1"})),
    _logistics(dict(cities=[("ankara",1),("cusco",1)],
                    trucks={"truck_ank":"ankara_depot1","truck_cus":"cusco_airport"},
                    airplanes={"plane1":"cusco_airport"},
                    packages={"pkg1":"ankara_airport"}, goals={"pkg1":"cusco_airport"})),
]


# Third tier, added for the P5 slice. Same admitting band: blocks of 4-8 gold
# actions, logistics with one package and one depot per city.
BLOCKS_SPECS += [
    dict(blocks=("A","B","C"), on={"C":"B"}, on_table={"A","B"},
         holding=None, goals_on={"B":"A","A":"C"}),
    dict(blocks=("A","B","C","D"), on={"B":"D"}, on_table={"A","C","D"},
         holding=None, goals_on={"D":"A","A":"C"}),
    dict(blocks=("A","B","C","D"), on={"A":"D"}, on_table={"B","C","D"},
         holding=None, goals_on={"C":"A","B":"C"}),
    dict(blocks=("A","B","C"), on={"A":"C"}, on_table={"B","C"},
         holding=None, goals_on={"C":"B","B":"A"}),
]
LOGISTICS_SPECS += [
    _logistics(dict(cities=[("porto",1),("bergenz",1)],
                    trucks={"truck_por":"porto_airport","truck_ber":"bergenz_airport"},
                    airplanes={"plane1":"porto_airport"},
                    packages={"pkg1":"porto_depot1"}, goals={"pkg1":"bergenz_airport"})),
    _logistics(dict(cities=[("dakar",1),("izmir",1)],
                    trucks={"truck_dak":"dakar_airport","truck_izm":"izmir_airport"},
                    airplanes={"plane1":"izmir_airport"},
                    packages={"pkg1":"dakar_airport"}, goals={"pkg1":"izmir_depot1"})),
    _logistics(dict(cities=[("dakar",1),("izmir",1)],
                    trucks={"truck_dak":"dakar_depot1","truck_izm":"izmir_airport"},
                    airplanes={"plane1":"dakar_airport"},
                    packages={"pkg1":"dakar_depot1"}, goals={"pkg1":"izmir_airport"})),
]


def _blocks_consequence(params: dict[str, Any], plan: list[str]) -> tuple[str, str]:
    """Derive the note from the SOLVED plan, not from a reading of the prose."""
    on = params["on"]
    goals_on = params["goals_on"]
    blocked = [top for top, sup in on.items() if sup in goals_on or sup in goals_on.values()]
    unstacks = [a for a in plan if a.startswith("unstack")]
    if blocked:
        first = sorted(blocked)[0]
        note = (
            f"{on[first]} is NOT clear in the initial state because {first} sits on it, "
            f"so nothing can be stacked onto {on[first]} until {first} is removed; the "
            f"BFS gold plan is {len(plan)} actions and uses {len(unstacks)} unstack "
            f"action(s). BFS gives the shortest plan, so that length is minimal, but the "
            f"unstack count alone does not prove it"
        )
        return note, "false_precondition"
    note = (
        f"the goal rearranges the initial configuration; the BFS gold plan is "
        f"{len(plan)} actions and, because BFS explores by depth, that length is minimal. "
        f"It uses {len(unstacks)} unstack action(s) -- recorded as a fact about this plan, "
        f"not as a proof of the bound"
    )
    return note, "false_reachability"


def _logistics_consequence(params: dict[str, Any], plan: list[str]) -> tuple[str, str]:
    flies = [a for a in plan if a.startswith("fly")]
    drives = [a for a in plan if a.startswith("drive")]
    cross_city = []
    for pkg, dest in params["goals"].items():
        start = params["packages"][pkg]
        if start.split("_")[0] != dest.split("_")[0]:
            cross_city.append(pkg)
    if cross_city:
        # Do NOT claim trucking at both ends: whether a leg is needed depends on
        # where the package and the airports actually are, and it is false for
        # several instances. State what the SOLVED plan contains instead.
        note = (
            f"{_and(cross_city)} must change city, and an airplane only lands at an "
            f"airport, so any city change needs a flight between airports plus whatever "
            f"truck legs the package's own position requires; this instance's gold plan "
            f"uses {len(flies)} flight(s) and {len(drives)} drive(s), "
            f"{len(plan)} actions in total"
        )
        return note, "false_precondition"
    note = (
        f"every package is already in its destination city, so no flight is required; "
        f"the gold plan is {len(plan)} actions and uses {len(drives)} drive(s) and no flight"
    )
    return note, "false_reachability"


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def build(prefix: str, locator_base: str = "data/smoke_100/candidates/source_groups_planning_candidates.jsonl") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    table = ([("plan_blocks", s) for s in BLOCKS_SPECS]
             + [("plan_logistics", s) for s in LOGISTICS_SPECS])
    # Ids are derived from the instance's SOLVER PARAMETERS, never from its
    # position in the table.  An index-derived id renumbers every later instance
    # the moment one is inserted -- which is precisely how batch_100's id space
    # drifted out from under its own screening traces.  A content-derived id is
    # stable under insertion, reordering and regeneration.
    for index, (family, params) in enumerate(table):
        fingerprint = hashlib.sha256(
            json.dumps({"family": family, "params": params}, sort_keys=True,
                       default=lambda o: sorted(o) if isinstance(o, (set, frozenset)) else list(o)
                       ).encode()).hexdigest()[:8]
        problem = make_problem(family, **params)
        plan = solve_bfs(problem)
        reached, _ = execute_plan(problem, plan)
        if not reached:
            raise AssertionError(f"{family}[{index}] BFS plan does not re-execute to the goal")
        statement = render_statement(family, params)
        note, pfm_family = (_blocks_consequence if family == "plan_blocks"
                            else _logistics_consequence)(params, plan)
        out.append({
            "stable_source_id": f"{prefix}-PLAN-{fingerprint}",
            "task_group_id": f"{prefix.lower()}_{family}_{fingerprint}",
            "statement_text_included": True,
            # Derived from where this file is actually being written. Hardcoding
            # it meant the emitted locator still said data/smoke_80 after the
            # batch was renamed, pointing every planning source at a path that
            # no longer exists.
            "source_record_locator": f"{locator_base}#{fingerprint}",
            "source_family": family,
            "source_dataset": f"authored_pddl_{prefix.lower()}_2026_09_06",
            "source_year": 2026,
            "domain": "planning",
            "statement": statement,
            "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
            "original_answer": format_plan(plan),
            "answer_form": "plan",
            "answer_equivalence": (
                "Compare action sequences up to (a) reordering of independent actions and "
                "(b) synonymous action spellings. A plan is equivalent iff it is executable "
                "from the initial state and reaches the goal; prefer a validator over string match."),
            "plan_actions": len(plan),
            "solver_params": json.loads(json.dumps(params, default=lambda o: sorted(o)
                                                   if isinstance(o, (set, frozenset)) else list(o))),
            "consequence_note": note,
            "candidate_pfm_family": pfm_family,
            "expected_authored_rows": 4,
            "source_admission_status": "authored_admissible",
            "owner_id": None,
            "split": "development",
            "report_partition": "development",
            "screening": {
                "status": "pending",
                "no_update_solved": None,
                "consequence_confirmed": False,
                "consequence_confirmed_basis":
                    "consequence_note derived from the solved gold plan; not yet confirmed by a human",
                "grading_method": "plan_equivalence",
                "plan_actions": len(plan),
            },
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--prefix", default="S80")
    args = ap.parse_args()
    rows = build(args.prefix, locator_base=str(Path(args.output)))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    lengths = [r["plan_actions"] for r in rows]
    print(f"wrote {len(rows)} candidates to {path}")
    print(f"  plan lengths: min {min(lengths)} median {sorted(lengths)[len(lengths)//2]} max {max(lengths)}")
    for fam in ("plan_blocks", "plan_logistics"):
        n = sum(1 for r in rows if r["source_family"] == fam)
        print(f"  {fam}: {n}")


if __name__ == "__main__":
    main()
