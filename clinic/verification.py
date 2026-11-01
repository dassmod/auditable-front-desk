"""Replay clinic decisions and check relationships across a booking trace."""

from replay.engine import replay_trace

from clinic.table import TABLE

BOOKING_GUARDS = (
    "slot_is_free",
    "within_opening_hours",
    "not_in_past",
)
PENDING_STEPS = {
    "pending_after_proposal",
    "pending_proposal_matches",
    "pending_after_resolution",
}


def verify_trace(trace):
    """Return deterministic step verdicts and clinic-specific trace checks."""
    step_verdicts = replay_trace(trace, TABLE)
    return step_verdicts + _check_pending_state(trace) + _check_confirmations(
        trace, step_verdicts
    )


def _check_pending_state(trace):
    """Check that recorded pending-slot transitions form one continuous state."""
    verdicts = []
    pending = None
    pending_at_turn_start = None

    for position, step in enumerate(trace["steps"]):
        name = step["name"]
        if name == "user_message":
            pending_at_turn_start = pending
            continue
        if name not in PENDING_STEPS:
            continue

        inputs = step["inputs"]
        outputs = step["outputs"]
        issues = []

        if name == "pending_after_proposal":
            if inputs.get("pending_start") != pending:
                issues.append("proposal did not start from the current pending slot")
            expected_pending = inputs.get("proposed_start")
            if outputs.get("pending_start") != expected_pending:
                issues.append("proposal output does not equal the proposed slot")
            pending = expected_pending

        elif name == "pending_proposal_matches":
            if inputs.get("pending_start") != pending:
                issues.append(
                    "confirmation check does not use the current pending slot"
                )
            if inputs.get("pending_at_turn_start") != pending_at_turn_start:
                issues.append("confirmation check does not use the turn-start slot")
            expected_decision = (
                "allow"
                if pending is not None and pending == pending_at_turn_start
                else "deny"
            )
            if outputs.get("decision") != expected_decision:
                issues.append("confirmation decision conflicts with pending state")

        else:
            if inputs.get("pending_start") != pending:
                issues.append("resolution did not start from the current pending slot")
            if inputs.get("pending_at_turn_start") != pending_at_turn_start:
                issues.append("resolution does not use the turn-start slot")
            expected_pending = (
                None if pending is not None and pending == pending_at_turn_start
                else pending
            )
            if outputs.get("pending_start") != expected_pending:
                issues.append("resolution output conflicts with pending state")
            pending = expected_pending

        verdicts.append({
            "index": step.get("index", position),
            "name": "pending_state_chain",
            "status": "inconsistent" if issues else "match",
            "issues": issues,
        })

    return verdicts


def _check_confirmations(trace, step_verdicts):
    """Check that each accepted confirmation has its complete booking sequence."""
    steps = trace["steps"]
    issues_by_position = {}
    for position, verdict in enumerate(step_verdicts):
        if verdict["status"] != "match":
            issues_by_position[position] = verdict["status"]

    flow_verdicts = []
    for decision_position, decision_step in enumerate(steps):
        if (
            decision_step["name"] != "model_decision"
            or decision_step["outputs"].get("tool_name") != "confirm_appointment"
        ):
            continue

        turn_start = decision_position
        while turn_start > 0 and steps[turn_start]["name"] != "user_message":
            turn_start -= 1
        if steps[turn_start]["name"] != "user_message":
            turn_start = decision_position

        turn_end = decision_position + 1
        while turn_end < len(steps) and steps[turn_end]["name"] != "user_message":
            turn_end += 1
        turn_steps = [
            (position, step)
            for position, step in enumerate(steps[decision_position + 1:turn_end],
                                            start=decision_position + 1)
        ]

        issues = []
        checks = [item for item in turn_steps
                  if item[1]["name"] == "pending_proposal_matches"]
        if not checks:
            issues.append("missing pending_proposal_matches")
            flow_status = "missing_step"
        elif len(checks) > 1:
            issues.append("duplicate pending_proposal_matches")
            flow_status = "inconsistent"
        else:
            check_position, check = checks[0]
            decision = check["outputs"].get("decision")
            recorded_start = check["inputs"].get("pending_at_turn_start")
            current_state = _pending_before(steps, decision_position)
            turn_start_state = _pending_before(steps, turn_start)
            if recorded_start != turn_start_state:
                issues.append("confirmation does not match state at turn start")
            if check["inputs"].get("pending_start") != current_state:
                issues.append("confirmation does not use the preceding pending state")
            prior_position = _pending_transition_before(steps, turn_start)
            if recorded_start is not None:
                if (
                    prior_position is None
                    or steps[prior_position]["name"] != "pending_after_proposal"
                ):
                    issues.append("no earlier proposal establishes the confirmed slot")
                elif (
                    steps[prior_position]["outputs"].get("pending_start")
                    != recorded_start
                    or issues_by_position.get(prior_position) not in (None, "match")
                ):
                    issues.append("earlier proposal does not match the confirmed slot")
            if issues_by_position.get(check_position) not in (None, "match"):
                issues.append("pending_proposal_matches did not replay as a match")

            if decision != "allow":
                guards = [item for item in turn_steps
                          if item[1]["name"] in BOOKING_GUARDS]
                effects = [item for item in turn_steps
                           if item[1]["name"] == "book_appointment"]
                if guards or effects:
                    issues.append(
                        "a denied confirmation continued to guards or booking"
                    )
                resolutions = [item for item in turn_steps
                               if item[1]["name"] == "pending_after_resolution"]
                if not resolutions:
                    issues.append("missing pending_after_resolution")
                elif len(resolutions) > 1:
                    issues.append("duplicate pending_after_resolution")
                elif issues_by_position.get(resolutions[0][0]) not in (None, "match"):
                    issues.append("pending resolution did not replay as a match")
                flow_status = "inconsistent" if issues else "match"
            else:
                flow_status = _check_allowed_confirmation(
                    turn_steps, check, issues, issues_by_position
                )

        flow_verdicts.append({
            "index": decision_step.get("index", decision_position),
            "name": "confirmation_flow",
            "status": flow_status,
            "issues": issues,
        })

    return flow_verdicts


def _check_allowed_confirmation(turn_steps, check, issues, issues_by_position):
    """Check guards, booking effect and resolution for an allowed confirmation."""
    start = check["inputs"].get("pending_at_turn_start")
    check_position = next(
        position for position, step in turn_steps
        if step is check
    )
    if start is None or check["inputs"].get("pending_start") != start:
        issues.append("allowed confirmation has no matching pending proposal")

    found_guards = {}
    for position, step in turn_steps:
        if step["name"] in BOOKING_GUARDS:
            found_guards.setdefault(step["name"], []).append((position, step))

    for name in BOOKING_GUARDS:
        if name not in found_guards:
            issues.append(f"missing {name}")
        elif len(found_guards[name]) > 1:
            issues.append(f"duplicate {name}")

    guard_steps = []
    for name in BOOKING_GUARDS:
        entries = found_guards.get(name, [])
        if not entries:
            continue
        position, step = entries[0]
        guard_steps.append((position, step))
        if position <= check_position:
            issues.append(f"{name} ran before the pending-proposal check")
        if step["inputs"].get("start") != start:
            issues.append(f"{name} checked a different slot")
        if step["outputs"].get("decision") not in ("allow", "deny"):
            issues.append(f"{name} has an unknown decision")
        if issues_by_position.get(position) not in (None, "match"):
            issues.append(f"{name} did not replay as a match")

    if guard_steps and [position for position, _ in guard_steps] != sorted(
        position for position, _ in guard_steps
    ):
        issues.append("booking guards are out of order")

    all_allowed = (
        len(guard_steps) == len(BOOKING_GUARDS)
        and all(step["outputs"].get("decision") == "allow"
                for _, step in guard_steps)
    )
    effects = [item for item in turn_steps
               if item[1]["name"] == "book_appointment"]
    if all_allowed:
        if not effects:
            issues.append("missing book_appointment effect")
        elif len(effects) > 1:
            issues.append("duplicate book_appointment effect")
        else:
            effect_position, effect = effects[0]
            if effect["inputs"].get("start") != start:
                issues.append("booking effect used a different slot")
            if effect["outputs"].get("booked") is not True:
                issues.append("booking effect did not record success")
            if guard_steps and effect_position <= max(pos for pos, _ in guard_steps):
                issues.append("booking effect came before all booking guards")
            if issues_by_position.get(effect_position) not in (None, "skipped"):
                issues.append("booking effect has an unexpected replay status")
    elif effects and len(guard_steps) == len(BOOKING_GUARDS):
        issues.append("booking effect exists although not all guards allowed")

    resolutions = [item for item in turn_steps
                   if item[1]["name"] == "pending_after_resolution"]
    if not resolutions:
        issues.append("missing pending_after_resolution")
    elif len(resolutions) > 1:
        issues.append("duplicate pending_after_resolution")
    else:
        resolution_position, resolution = resolutions[0]
        if resolution["inputs"].get("pending_start") != start:
            issues.append("resolution used a different pending slot")
        if resolution["outputs"].get("pending_start") is not None:
            issues.append("confirmed proposal was not cleared")
        last_action = max(
            [position for position, _ in guard_steps]
            + [position for position, _ in effects]
        ) if guard_steps or effects else None
        if last_action is not None and resolution_position <= last_action:
            issues.append("pending proposal resolved before the booking checks")
        if issues_by_position.get(resolution_position) not in (None, "match"):
            issues.append("pending resolution did not replay as a match")

    if issues:
        missing = any(issue.startswith("missing ") for issue in issues)
        return "missing_step" if missing else "inconsistent"
    return "match"


def _pending_before(steps, stop_position):
    """Return the pending slot implied by state transitions before a step."""
    position = _pending_transition_before(steps, stop_position)
    if position is None:
        return None
    return steps[position]["outputs"].get("pending_start")


def _pending_transition_before(steps, stop_position):
    """Return the last pending-state transition before a step, if any."""
    for position in range(stop_position - 1, -1, -1):
        if steps[position]["name"] in {
            "pending_after_proposal",
            "pending_after_resolution",
        }:
            return position
    return None

