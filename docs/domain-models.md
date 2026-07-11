# Domain Models

The `game_assistant.core` package defines the shared domain contract for the
osu!mania MVP. These models are intentionally independent of CLI flows, storage,
OCR, replay parsing, recommendation logic, report generation, network calls, and
game adapter implementations.

## Shared Rules

- Models use frozen dataclasses and deterministic equality. Collection inputs
  are defensively copied to tuples; source metadata is copied to a read-only
  mapping.
- Constructors validate values immediately and raise `DomainValidationError`,
  a `ValueError` subclass. Error messages identify the model field that failed.
- Required identifiers and human-readable strings are stripped and must not be
  empty. Optional text fields are stripped and blank values become `None`.
- Datetimes must be timezone-aware UTC. Naive datetimes and non-UTC offsets are
  rejected. JSON dictionaries serialize datetimes as ISO 8601 strings ending in
  `Z`.
- Enums serialize to stable string values. Unknown enum strings in `from_dict()`
  fail clearly.
- Numeric fields reject booleans, NaN, and infinities. Bounded fields enforce
  their documented ranges.
- Relationships remain as string identifiers such as `profile_id`,
  `session_id`, `map_id`, and `score_id`. Constructors do not check databases,
  filesystems, network URIs, or cross-record existence.
- Callers supply stable ids. The explicit `new_id()` helper may be used when a
  caller wants a generated id; constructors never generate ids implicitly.

Every public record exposes `to_dict()` and `from_dict()` for JSON-compatible
representations made only of strings, numbers, booleans, `None`, lists, and
dictionaries.

## Enums And Value Types

- `GameId`: currently `osu_mania`. Future games can extend this contract later
  without introducing adapter behavior here.
- `KeyMode`: exactly `4k` and `7k` for the MVP.
- `SessionStatus`: `active`, `completed`, or `abandoned`.
- `EvidenceSource`: the type of record being referenced as evidence, such as a
  score, replay metadata record, map metadata record, practice session, analysis
  result, training plan, or manual note.
- `WeaknessCategory`: stable coaching categories such as timing, reading,
  consistency, speed, stamina, jack control, long-note control, and accuracy
  control.
- `ReplaySupportStatus`: `unsupported`, `metadata_only`, or `supported`. This is
  metadata only; it does not parse replay files.
- `EvidenceRef`: a `(source, record_id, message)` reference used to ground
  weaknesses, tasks, and reports without nesting full records.

## Public Records

`PlayerProfile` stores a player's display name, primary game, creation time,
optional 4K/7K focus modes, optional current PP, and free-form goals. PP is
finite and non-negative. Focus modes must not contain duplicates.

`PracticeSession` stores a session id, profile id, UTC start time, status, and
optional UTC end time, notes, and focus modes. End time cannot be earlier than
start time.

`ScoreRecord` stores one played score with session and map identifiers, UTC play
time, key mode, non-negative integer score, and accuracy from 0 to 100
inclusive. Optional combo and misses are non-negative integers. Grade and mods
are text. Source metadata accepts only string, boolean, or null values; numeric
metadata belongs in bounded model fields.

`MapMetadata` stores map identity, game, title, artist, creator, version, key
mode, optional non-negative difficulty, and optional source identifier or URI.
The URI is stored as text only and is not fetched or validated against the
network.

`ReplayMetadata` stores replay registration metadata: id, game, file name, UTC
registration time, support status, optional links to session/score/map ids,
checksum, non-negative file size, and optional UTC played-at time. It never
reads the replay file.

`WeaknessSignal` stores a category, normalized severity and confidence in the
0-1 inclusive range, a summary, and at least one evidence reference. Duplicate
evidence ids are rejected.

`AnalysisResult` stores a generated analysis for a profile, the covered session
and score ids, weakness signals, and an `insufficient_evidence` flag. A valid
analysis with no detected weaknesses uses `insufficient_evidence=False` and an
empty weakness list; insufficient evidence is represented explicitly with
`insufficient_evidence=True`.

`TrainingTask` stores one ordered task with an id, goal, positive duration in
minutes, optional evidence references, and optional weakness categories.

`TrainingPlan` stores a profile plan for one date. Its tasks must be non-empty
and have unique ids. `total_duration_minutes` is derived from tasks; serialized
data may include it, and reconstruction validates that it matches the task sum.

`CoachReport` stores a generated summary with evidence references and optional
analysis and plan ids. `grounded_in_evidence=True` is rejected when the evidence
collection is empty.
