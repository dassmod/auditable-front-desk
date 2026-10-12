from clinic.parser import parse_booking, parse_arguments

NOW = "2026-10-01T09:12"

assert parse_booking("book tuesday 15:00", NOW) == "2026-10-06T15:00"
assert parse_booking("book tuesday 9:00", NOW) == "2026-10-06T09:00"
assert parse_booking("book tuesday banana", NOW) == None
assert parse_booking("book banana 15:00", NOW) == None
assert parse_booking("book thursday 10:00", NOW) == "2026-10-08T10:00"
assert parse_arguments('{"start": "2026-10-12T10:00"}') == "ok"
assert parse_arguments('{}') == "missing_start"
assert parse_arguments('not json') == "invalid_json"
assert parse_arguments('[]') == "not_an_object"

print("ok")