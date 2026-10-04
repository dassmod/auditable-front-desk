# WORKLOG

## 2026-10-04

**Stopped at:** Step 3 done and tested. `parse_booking` is now a recorded step (`deterministic`, `text` and `now` in, `start` out), written before the `None` check so a refusal leaves its cause in the trace. `parser.py` rejects a time it cannot read with `strptime` inside a one-line `try` and rebuilds the string with `strftime`, so `9:00` becomes `T09:00` and `book tuesday banana` stops at the parser instead of crashing later in `within_opening_hours` with `Invalid isoformat string`. `test_parser.py` at the repo root holds five asserts and prints `ok`. The break, both halves: dropping `is_free == "allow" and` left the guard recorded as `deny` while the effect ran anyway (a stranger sees deny, then booked), and moving `BOOKED.append(start)` above the guards made an honest first request come back `Not booked` with the recorded `booked` list already holding the slot. Gate order, and the replay engine would have said `match` on both traces, because every recorded output follows from its recorded inputs.

**Next move:** Step 4, in `proof-of-agent-run`: open `replay/engine.py` and add a `guards` parameter to `replay_step`, so the guard table is passed in instead of read from the module constant.

**Open:** a failed parse records `null` but not which part failed (verb, day or time). `parse_booking` is `deterministic` but is not a guard, since it returns a date and not `allow` or `deny`, so how the engine's table admits it is a Step 4 question. The trace saves only on `quit`, so a crash loses the whole run. A bare `assert` names the line but not the value it got.

## 2026-10-02

**Stopped at:** Step 3 loop works. `clinic/scripted.py` reads `input("> ")`, parses with `parse_booking`, runs the three guards, records every step, books or refuses, saves on `quit`. `clinic/parser.py` turns `book tuesday 15:00` into `2026-10-06T15:00`, taking `now` as an argument (no hidden clock). An unreadable line records `user_message` and `agent_reply` only, then `continue` skips the guards. Bugs met: truthiness of `"deny"`, a stale `agent_reply` with no `else`, record names and keys that must match the guard's names, a tuple used where a dict was needed, `continue:` with a colon.

**Next move:** the break. Drop `is_free == "allow" and` from the `if`, book the same slot twice, read steps 7 and 10 as a stranger. Then restore it and move `BOOKED.append(start)` above the guards (gate order).

**Open:** the parse is not a recorded step, so `start` appears in the trace with no step that made it. `time_text` is not checked, so `book tuesday banana` reaches the guards.

## 2026-09-29

**Stopped at:** Step 2 done. `clinic/trace.py` has a `Recorder` with `record` and `save`. Broke it on purpose: recorded `BOOKED`, then appended to it, and the saved trace showed 15:00 in `booked` next to `allow`, a false divergence on an honest run. Aliasing. Fixed by copying at record time with a JSON round trip.

**Next move:** Step 3. Create `clinic/scripted.py`: a `while True` loop with `input()` that parses `book tuesday 15:00`.

**Open:**

## 2026-09-28

**Stopped at:** Step 1 done. `clinic/world.py` and three pure guards in `clinic/guards.py` (`slot_is_free`, `within_opening_hours`, `not_in_past`), each tested with an allow and a deny. Broke `within_opening_hours` on 23:45 (wrapped past midnight, fixed with a same-day check).

**Next move:** Step 2. Create `clinic/trace.py` with a `Recorder` class: `record(kind, name, inputs, outputs)` and `save(path)`.

**Open:** the `not_in_past_bad` flip, if you did not run it yet. Why `strftime` dropping the date made 23:45 pass.