"""Session application is distinct from rule evaluation (docs/12 §3)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Eval:
    session: str
    valid: bool
    passes: bool
    hard_risk: bool = False
    ordinal: int = 0
    previous_session: str | None = None
    final: bool = True
    suspended: bool = False


def step(status, pending, ev, last_confirmed=None, enter_count=2, exit_count=2):
    changes = []
    if ev.hard_risk:
        if status != 'OUT':
            changes.append({'from': status, 'to': 'OUT', 'reason': 'RISK'})
        return 'OUT', 0, changes
    if ev.suspended or not ev.valid:
        target = 'SUSPENDED' if ev.suspended else 'UNKNOWN'
        if status != target:
            changes.append({'from': status, 'to': target, 'reason': 'SUSPENDED' if ev.suspended else 'MISSING_DATA'})
        # The synthetic s0 has no known baseline and remains silent OUT.
        if status == 'OUT' and last_confirmed is None and not ev.suspended:
            return 'OUT', 0, []
        return target, 0, changes
    if status in ('UNKNOWN', 'SUSPENDED'):
        status = last_confirmed or 'OUT'
    if last_confirmed is None and status == 'OUT':
        return ('IN' if ev.passes else 'OUT'), 0, changes
    if ev.passes:
        if status in ('IN', 'EXIT_PENDING'):
            return 'IN', 0, changes
        count = pending + 1 if status == 'ENTER_PENDING' else 1
        if count >= enter_count:
            changes.append({'from': status, 'to': 'IN', 'reason': 'ENTER'})
            return 'IN', 0, changes
        return 'ENTER_PENDING', count, changes
    if status in ('OUT', 'ENTER_PENDING'):
        return 'OUT', 0, changes
    count = pending + 1 if status == 'EXIT_PENDING' else 1
    if count >= exit_count:
        changes.append({'from': status, 'to': 'OUT', 'reason': 'EXIT'})
        return 'OUT', 0, changes
    return 'EXIT_PENDING', count, changes


def apply_session(state, ev, enter_count=2, exit_count=2):
    """State exposes status/pending_count/last_confirmed/last_session/last_ordinal.

    Calendar supplies ordinal and predecessor. Never infer expected sessions from
    weekdays. Re-evaluations and late results remain historical, not applied.
    """
    if not ev.final:
        return [], 'provisional'
    if state.last_session == ev.session or ev.ordinal <= state.last_ordinal:
        return [], 'superseded'
    if state.last_session and ev.previous_session != state.last_session:
        state.pending_count = 0
        state.status = state.last_confirmed or 'OUT'
    status, count, changes = step(state.status, state.pending_count, ev,
                                  state.last_confirmed, enter_count, exit_count)
    state.status, state.pending_count = status, count
    if status in ('IN', 'OUT') and (ev.valid or ev.hard_risk):
        state.last_confirmed = status
    state.last_session, state.last_ordinal = ev.session, ev.ordinal
    return changes, 'applied'


GOLDEN = [
    Eval('s0', True, False, ordinal=0),
    Eval('s1', True, True, ordinal=1, previous_session='s0'),
    Eval('s1', True, True, ordinal=1, previous_session='s0'),
    Eval('s2', True, True, ordinal=2, previous_session='s1'),
    Eval('s3', False, False, ordinal=3, previous_session='s2'),
    Eval('s4', True, True, ordinal=4, previous_session='s3'),
    Eval('s5', True, False, ordinal=5, previous_session='s4'),
    Eval('s6', True, False, ordinal=6, previous_session='s5'),
    Eval('s7', True, True, ordinal=7, previous_session='s6'),
    Eval('s8', True, True, ordinal=8, previous_session='s7'),
    Eval('s9', True, True, hard_risk=True, ordinal=9, previous_session='s8'),
]
