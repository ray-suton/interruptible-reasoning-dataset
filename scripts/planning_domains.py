#!/usr/bin/env python3
"""Executable planning domains — the solver contributors author against.

Lifted out of the smoke-20 pilot generator so that a contributor authoring a
planning row has an import point that is not named for a finished batch.
`author_smoke_20_planning.py` imports from here, so the pilot stays byte-
reproducible.

WHAT THIS IS FOR
----------------
`workflow.md` §3 step 4: *derive every answer by executing a solver; never type
an answer.*  For planning that means `solve_bfs` for the gold plan and
`execute_plan` for any plan you did not generate — including the wrong-branch
plan a PFM signature points at, which must be shown to FAIL rather than merely
asserted to.

Adding an instance is a dict entry in INSTANCES, not a new if-branch.  Every
builder is parameterised; none of them knows about a batch.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable

State = Hashable
Successors = Callable[[State], Iterable[tuple[str, State]]]
GoalTest = Callable[[State], bool]

@dataclass(frozen=True)
class PlanningProblem:
    initial: State
    successors: Successors
    is_goal: GoalTest

def solve_bfs(problem: PlanningProblem) -> list[str]:
    queue = deque([(problem.initial, [])])
    visited = {problem.initial}
    while queue:
        state, plan = queue.popleft()
        if problem.is_goal(state):
            return plan
        for action, next_state in problem.successors(state):
            if next_state in visited:
                continue
            visited.add(next_state)
            queue.append((next_state, [*plan, action]))
    raise ValueError("planning problem has no solution")


def execute_plan(problem: PlanningProblem, plan: list[str]) -> tuple[bool, State]:
    state = problem.initial
    for action in plan:
        available = list(problem.successors(state))
        matches = [
            candidate_state
            for candidate, candidate_state in available
            if candidate.lower() == action.lower()
        ]
        # The one-door source's pinned spelling is simply "unlock door".  It is
        # unambiguous at that state, so accept it exactly when one unlock action
        # is available; multi-door plans must continue naming the door.
        if not matches and action.lower() == "unlock door":
            matches = [
                candidate_state
                for candidate, candidate_state in available
                if candidate.lower().startswith("unlock door ")
            ]
        if len(matches) != 1:
            return False, state
        state = matches[0]
    return problem.is_goal(state), state


def format_plan(plan: list[str]) -> str:
    return "; ".join(plan)

def blocks_problem(
    *,
    blocks: tuple[str, ...],
    on: dict[str, str],
    on_table: set[str],
    holding: str | None,
    goals_on: dict[str, str],
    goals_clear: set[str] | None = None,
) -> PlanningProblem:
    # The initial state must describe a POSSIBLE world. Nothing checked this, and
    # one instance shipped with holding="C" alongside on_table={"B","C","D"} --
    # C in the gripper and on the table at once. BFS solved it anyway (the state
    # tuple tracks the three facts independently and "put down C" was a no-op on
    # a set that already held C), the statement rendered the contradiction as
    # prose, and the model then "solved" a task that cannot exist. A base task
    # that is not well-posed cannot support any row built on it.
    supported_by = set(on.values())
    if holding is not None:
        if holding in on_table:
            raise AssertionError(
                f"initial state impossible: the arm holds {holding!r} and it is also on "
                f"the table")
        if holding in on:
            raise AssertionError(
                f"initial state impossible: the arm holds {holding!r} and it is also on "
                f"{on[holding]!r}")
        if holding in supported_by:
            raise AssertionError(
                f"initial state impossible: the arm holds {holding!r} and another block "
                f"rests on it")
    for top, support in on.items():
        if top in on_table:
            raise AssertionError(
                f"initial state impossible: {top!r} is on {support!r} and on the table")
    if len(supported_by) != len(list(on.values())):
        raise AssertionError("initial state impossible: two blocks rest on the same block")
    missing = (set(on) | set(on_table) | supported_by) - set(blocks)
    if missing:
        raise AssertionError(f"initial state names blocks not declared: {sorted(missing)}")

    initial = (tuple(sorted(on.items())), tuple(sorted(on_table)), holding)
    required_clear = frozenset(goals_clear or set())

    def unpack(state: State) -> tuple[dict[str, str], set[str], str | None]:
        state_on, state_table, state_holding = state  # type: ignore[misc]
        return dict(state_on), set(state_table), state_holding

    def clear_blocks(state_on: dict[str, str], state_holding: str | None) -> set[str]:
        supported = set(state_on.values())
        return set(blocks) - supported - ({state_holding} if state_holding else set())

    def successors(state: State) -> Iterable[tuple[str, State]]:
        state_on, state_table, state_holding = unpack(state)
        clear = clear_blocks(state_on, state_holding)
        if state_holding:
            for target in sorted(clear - {state_holding}):
                new_on = dict(state_on)
                new_on[state_holding] = target
                yield (
                    f"stack {state_holding} on {target}",
                    (tuple(sorted(new_on.items())), tuple(sorted(state_table)), None),
                )
            new_table = set(state_table)
            new_table.add(state_holding)
            yield (
                f"put down {state_holding} on table",
                (tuple(sorted(state_on.items())), tuple(sorted(new_table)), None),
            )
            return
        for top, support in sorted(state_on.items()):
            if top not in clear:
                continue
            new_on = dict(state_on)
            del new_on[top]
            yield (
                f"unstack {top} from {support}",
                (tuple(sorted(new_on.items())), tuple(sorted(state_table)), top),
            )
        for block in sorted(state_table & clear):
            new_table = set(state_table)
            new_table.remove(block)
            yield (
                f"pick up {block} from table",
                (tuple(sorted(state_on.items())), tuple(sorted(new_table)), block),
            )

    def is_goal(state: State) -> bool:
        state_on, _state_table, state_holding = unpack(state)
        clear = clear_blocks(state_on, state_holding)
        return (
            state_holding is None
            and all(state_on.get(top) == support for top, support in goals_on.items())
            and required_clear.issubset(clear)
        )

    return PlanningProblem(initial, successors, is_goal)

def grid_problem(*, goal: tuple[int, int], blocked: set[tuple[int, int]], bound: int = 3) -> PlanningProblem:
    steps = (
        ("move north", (0, 1)),
        ("move east", (1, 0)),
        ("move south", (0, -1)),
        ("move west", (-1, 0)),
    )

    def successors(state: State) -> Iterable[tuple[str, State]]:
        x, y = state  # type: ignore[misc]
        for action, (dx, dy) in steps:
            nxt = (x + dx, y + dy)
            if 0 <= nxt[0] <= bound and 0 <= nxt[1] <= bound and nxt not in blocked:
                yield action, nxt

    return PlanningProblem((0, 0), successors, lambda state: state == goal)

def delivery_problem(
    *, rooms: tuple[str, ...], robot: str, package: str, goal: str
) -> PlanningProblem:
    adjacency = {room: set() for room in rooms}
    for left, right in zip(rooms, rooms[1:]):
        adjacency[left].add(right)
        adjacency[right].add(left)

    def successors(state: State) -> Iterable[tuple[str, State]]:
        state_robot, state_package, held = state  # type: ignore[misc]
        if held:
            yield "drop package", (state_robot, state_robot, False)
            for destination in sorted(adjacency[state_robot]):
                yield f"move {state_robot} to {destination}", (destination, destination, True)
        else:
            if state_package == state_robot:
                yield "pick package", (state_robot, state_package, True)
            for destination in sorted(adjacency[state_robot]):
                yield f"move {state_robot} to {destination}", (destination, state_package, False)

    return PlanningProblem(
        (robot, package, False),
        successors,
        lambda state: state[1] == goal and state[2] is False,  # type: ignore[index]
    )

def door_problem(
    *, rooms: tuple[str, ...], unlocked: set[str], goal: str
) -> PlanningProblem:
    doors = {"S-T"} if len(rooms) == 2 else {"S-T", "T-U"}
    adjacency = {room: set() for room in rooms}
    for left, right in zip(rooms, rooms[1:]):
        adjacency[left].add(right)
        adjacency[right].add(left)

    def canonical_door(left: str, right: str) -> str:
        candidate = f"{left}-{right}"
        return candidate if candidate in doors else f"{right}-{left}"

    def successors(state: State) -> Iterable[tuple[str, State]]:
        room, holding, state_unlocked = state  # type: ignore[misc]
        unlocked_set = set(state_unlocked)
        if not holding and room == "S":
            yield "pick key", (room, True, tuple(sorted(unlocked_set)))
        if holding:
            for destination in sorted(adjacency[room]):
                door = canonical_door(room, destination)
                if door not in unlocked_set:
                    newly_unlocked = {*unlocked_set, door}
                    yield f"unlock door {door}", (room, True, tuple(sorted(newly_unlocked)))
        for destination in sorted(adjacency[room]):
            door = canonical_door(room, destination)
            if door in unlocked_set:
                yield f"move {room} to {destination}", (destination, holding, tuple(sorted(unlocked_set)))

    return PlanningProblem(
        ("S", False, tuple(sorted(unlocked))),
        successors,
        lambda state: state[0] == goal,  # type: ignore[index]
    )

def crate_problem(*, destinations: dict[str, str], capacity: int = 1) -> PlanningProblem:
    initial = (("X", "Y"), (), (), ())

    def successors(state: State) -> Iterable[tuple[str, State]]:
        floor, carried, shelf, pallet = (set(part) for part in state)  # type: ignore[arg-type]
        if len(carried) < capacity:
            for crate in sorted(floor):
                new_floor, new_carried = set(floor), set(carried)
                new_floor.remove(crate)
                new_carried.add(crate)
                yield (
                    f"load {crate}",
                    (tuple(sorted(new_floor)), tuple(sorted(new_carried)), tuple(sorted(shelf)), tuple(sorted(pallet))),
                )
        for crate in sorted(carried):
            for destination in ("shelf", "pallet"):
                new_carried, new_shelf, new_pallet = set(carried), set(shelf), set(pallet)
                new_carried.remove(crate)
                (new_shelf if destination == "shelf" else new_pallet).add(crate)
                yield (
                    f"place {crate} on {destination}",
                    (tuple(sorted(floor)), tuple(sorted(new_carried)), tuple(sorted(new_shelf)), tuple(sorted(new_pallet))),
                )

    def is_goal(state: State) -> bool:
        _floor, carried, shelf, pallet = (set(part) for part in state)  # type: ignore[arg-type]
        placements = {crate: "shelf" for crate in shelf} | {crate: "pallet" for crate in pallet}
        return not carried and all(placements.get(crate) == destination for crate, destination in destinations.items())

    return PlanningProblem(initial, successors, is_goal)


def logistics_problem(
    *,
    cities: dict[str, tuple[str, ...]],
    airports: dict[str, str],
    trucks: dict[str, str],
    airplanes: dict[str, str],
    packages: dict[str, str],
    goals: dict[str, str],
) -> PlanningProblem:
    """IPC Logistics.

    Packages move within a city by truck and between cities by airplane, which
    can only land at airports.  `cities` maps a city to its locations,
    `airports` a city to the one location in it that is an airport, `trucks` a
    truck to its starting location, `airplanes` a plane to its starting airport,
    `packages` a package to its starting location, and `goals` a package to
    where it must end up.

    A package's position is a location name while it sits on the ground and a
    vehicle name while it is loaded, which is what lets one flat dict describe
    both.
    """
    location_city = {loc: city for city, locs in cities.items() for loc in locs}
    airport_set = set(airports.values())
    truck_city = {truck: location_city[loc] for truck, loc in trucks.items()}

    initial = (
        tuple(sorted(packages.items())),
        tuple(sorted(trucks.items())),
        tuple(sorted(airplanes.items())),
    )

    def unpack(state: State) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        pkg_at, truck_at, plane_at = state  # type: ignore[misc]
        return dict(pkg_at), dict(truck_at), dict(plane_at)

    def pack(pkg_at, truck_at, plane_at) -> State:
        return (
            tuple(sorted(pkg_at.items())),
            tuple(sorted(truck_at.items())),
            tuple(sorted(plane_at.items())),
        )

    def successors(state: State) -> Iterable[tuple[str, State]]:
        pkg_at, truck_at, plane_at = unpack(state)

        for pkg in sorted(pkg_at):
            where = pkg_at[pkg]
            for truck in sorted(truck_at):
                if where == truck_at[truck]:
                    new = dict(pkg_at)
                    new[pkg] = truck
                    yield f"load {pkg} into {truck} at {where}", pack(new, truck_at, plane_at)
                elif where == truck:
                    at = truck_at[truck]
                    new = dict(pkg_at)
                    new[pkg] = at
                    yield f"unload {pkg} from {truck} at {at}", pack(new, truck_at, plane_at)
            for plane in sorted(plane_at):
                if where == plane_at[plane]:
                    new = dict(pkg_at)
                    new[pkg] = plane
                    yield f"load {pkg} into {plane} at {where}", pack(new, truck_at, plane_at)
                elif where == plane:
                    at = plane_at[plane]
                    new = dict(pkg_at)
                    new[pkg] = at
                    yield f"unload {pkg} from {plane} at {at}", pack(new, truck_at, plane_at)

        for truck in sorted(truck_at):
            here = truck_at[truck]
            for dest in cities[truck_city[truck]]:
                if dest == here:
                    continue
                new = dict(truck_at)
                new[truck] = dest
                yield f"drive {truck} from {here} to {dest}", pack(pkg_at, new, plane_at)

        for plane in sorted(plane_at):
            here = plane_at[plane]
            for dest in sorted(airport_set):
                if dest == here:
                    continue
                new = dict(plane_at)
                new[plane] = dest
                yield f"fly {plane} from {here} to {dest}", pack(pkg_at, truck_at, new)

    def is_goal(state: State) -> bool:
        pkg_at, _truck_at, _plane_at = unpack(state)
        return all(pkg_at.get(pkg) == dest for pkg, dest in goals.items())

    return PlanningProblem(initial, successors, is_goal)


BUILDERS = {
    "plan_blocks": blocks_problem,
    "plan_logistics": logistics_problem,
    "plan_grid": grid_problem,
    "plan_delivery": delivery_problem,
    "plan_door": door_problem,
    "plan_crate": crate_problem,
}


def make_problem(family: str, **params) -> PlanningProblem:
    """Build a problem from a family name and a parameter dict.

    The entry point for new instances: add a spec, not an if-branch.
    """
    try:
        builder = BUILDERS[family]
    except KeyError:
        raise KeyError(f"unknown planning family: {family!r}") from None
    return builder(**params)
