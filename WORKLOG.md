# WORKLOG

## 2026-09-29

**Stopped at:** Step 2 done. `clinic/trace.py` has a `Recorder` with `record` and `save`. Broke it on purpose: recorded `BOOKED`, then appended to it, and the saved trace showed 15:00 in `booked` next to `allow`, a false divergence on an honest run. Aliasing. Fixed by copying at record time with a JSON round trip.

**Next move:** Step 3. Create `clinic/scripted.py`: a `while True` loop with `input()` that parses `book tuesday 15:00`.

**Open:**

## 2026-09-28

**Stopped at:** Step 1 done. `clinic/world.py` and three pure guards in `clinic/guards.py` (`slot_is_free`, `within_opening_hours`, `not_in_past`), each tested with an allow and a deny. Broke `within_opening_hours` on 23:45 (wrapped past midnight, fixed with a same-day check).

**Next move:** Step 2. Create `clinic/trace.py` with a `Recorder` class: `record(kind, name, inputs, outputs)` and `save(path)`.

**Open:** the `not_in_past_bad` flip, if you did not run it yet. Why `strftime` dropping the date made 23:45 pass.