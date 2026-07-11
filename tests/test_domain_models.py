import importlib
import json
import math
import socket
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

from game_assistant.core import (
    AnalysisResult,
    CoachReport,
    DomainValidationError,
    EvidenceRef,
    EvidenceSource,
    GameId,
    KeyMode,
    MapMetadata,
    PlayerProfile,
    PracticeSession,
    ReplayMetadata,
    ReplaySupportStatus,
    ScoreRecord,
    SessionStatus,
    TrainingPlan,
    TrainingTask,
    WeaknessCategory,
    WeaknessSignal,
    new_id,
)


UTC = timezone.utc
START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
END = datetime(2026, 1, 1, 13, 0, tzinfo=UTC)
PLAN_DATE = date(2026, 1, 2)


def evidence(record_id: str = "score-1") -> EvidenceRef:
    return EvidenceRef(
        source=EvidenceSource.SCORE_RECORD,
        record_id=record_id,
        message="Accuracy dropped in the final third.",
    )


def score(**overrides: object) -> ScoreRecord:
    values: dict[str, object] = {
        "id": "score-1",
        "session_id": "session-1",
        "map_id": "map-1",
        "played_at": START,
        "key_mode": KeyMode.FOUR_K,
        "score": 987654,
        "accuracy": 98.76,
    }
    values.update(overrides)
    return ScoreRecord(**values)


def weakness(**overrides: object) -> WeaknessSignal:
    values: dict[str, object] = {
        "category": WeaknessCategory.TIMING,
        "severity": 0.5,
        "confidence": 0.75,
        "summary": "Late timing appears in dense sections.",
        "evidence_refs": [evidence()],
    }
    values.update(overrides)
    return WeaknessSignal(**values)


class DomainHappyPathTests(unittest.TestCase):
    def test_happy_path_construction_for_every_public_model(self) -> None:
        ref = evidence()
        profile = PlayerProfile(
            id="profile-1",
            display_name="Mira",
            primary_game=GameId.OSU_MANIA,
            created_at=START,
            focus_modes=[KeyMode.FOUR_K, "7k"],
            current_pp=1234.5,
            goals=["Improve rice stamina", "Clean LN releases"],
        )
        session = PracticeSession(
            id="session-1",
            profile_id=profile.id,
            started_at=START,
            status=SessionStatus.COMPLETED,
            ended_at=END,
            notes="Focused on timing",
            focus_modes=["4k"],
        )
        played_score = score(
            combo=1200,
            misses=0,
            grade="S",
            mods=["Mirror"],
            source=EvidenceSource.SCORE_RECORD,
            source_identifier="screenshot-1",
            source_metadata={"client": "osu", "verified": True},
        )
        map_metadata = MapMetadata(
            id="map-1",
            game=GameId.OSU_MANIA,
            title="Spring Signal",
            artist="Example Artist",
            creator="Mapper",
            version="Another",
            key_mode="4k",
            difficulty=4.25,
            source_identifier="12345",
            source_uri="https://example.invalid/beatmap/12345",
        )
        replay = ReplayMetadata(
            id="replay-1",
            game=GameId.OSU_MANIA,
            file_name="play.osr",
            registered_at=START,
            support_status=ReplaySupportStatus.METADATA_ONLY,
            session_id=session.id,
            score_id=played_score.id,
            map_id=map_metadata.id,
            checksum="abc123",
            file_size_bytes=0,
            played_at=START,
        )
        signal = weakness(evidence_refs=[ref])
        analysis = AnalysisResult(
            id="analysis-1",
            profile_id=profile.id,
            generated_at=END,
            covered_session_ids=[session.id],
            covered_score_ids=[played_score.id],
            weakness_signals=[signal],
            insufficient_evidence=False,
            notes="Enough score evidence for initial timing signal.",
        )
        task = TrainingTask(
            id="task-1",
            goal="Play two slower timing-control maps.",
            duration_minutes=20,
            evidence_refs=[ref],
            weakness_categories=[WeaknessCategory.TIMING],
        )
        plan = TrainingPlan(
            id="plan-1",
            profile_id=profile.id,
            created_at=END,
            plan_date=PLAN_DATE,
            tasks=[task],
            notes="Keep it short.",
        )
        report = CoachReport(
            id="report-1",
            profile_id=profile.id,
            generated_at=END,
            summary="Timing is the main near-term focus.",
            evidence_refs=[ref],
            analysis_id=analysis.id,
            plan_id=plan.id,
        )

        models = [
            ref,
            profile,
            session,
            played_score,
            map_metadata,
            replay,
            signal,
            analysis,
            task,
            plan,
            report,
        ]
        for model in models:
            with self.subTest(model=type(model).__name__):
                json.dumps(model.to_dict())

        self.assertEqual(profile.focus_modes, (KeyMode.FOUR_K, KeyMode.SEVEN_K))
        self.assertEqual(played_score.source_metadata["client"], "osu")
        self.assertEqual(plan.total_duration_minutes, 20)

    def test_new_id_is_explicit_and_prefix_validated(self) -> None:
        generated = new_id("profile")

        self.assertTrue(generated.startswith("profile_"))
        self.assertEqual(len(generated), len("profile_") + 36)
        with self.assertRaisesRegex(DomainValidationError, "new_id.prefix"):
            new_id("bad prefix")


class DomainValidationTests(unittest.TestCase):
    def assert_validation(self, pattern: str, factory: object) -> None:
        with self.assertRaisesRegex(DomainValidationError, pattern):
            factory()

    def test_required_field_and_blank_string_failures(self) -> None:
        self.assert_validation(
            "PlayerProfile.id",
            lambda: PlayerProfile(
                id=" ",
                display_name="Mira",
                primary_game=GameId.OSU_MANIA,
                created_at=START,
            ),
        )
        self.assert_validation(
            "PlayerProfile.display_name",
            lambda: PlayerProfile(
                id="profile-1",
                display_name=" ",
                primary_game=GameId.OSU_MANIA,
                created_at=START,
            ),
        )
        self.assert_validation(
            "PracticeSession.profile_id",
            lambda: PracticeSession(
                id="session-1",
                profile_id=" ",
                started_at=START,
                status=SessionStatus.ACTIVE,
            ),
        )
        self.assert_validation(
            "MapMetadata.title",
            lambda: MapMetadata(
                id="map-1",
                game=GameId.OSU_MANIA,
                title=" ",
                artist="Artist",
                creator="Mapper",
                version="Hard",
                key_mode=KeyMode.FOUR_K,
            ),
        )
        self.assert_validation(
            "ScoreRecord.accuracy",
            lambda: ScoreRecord.from_dict(
                {
                    "id": "score-1",
                    "session_id": "session-1",
                    "map_id": "map-1",
                    "played_at": "2026-01-01T12:00:00Z",
                    "key_mode": "4k",
                    "score": 100,
                }
            ),
        )
        self.assert_validation(
            "WeaknessSignal.evidence_refs",
            lambda: weakness(evidence_refs=[]),
        )
        self.assert_validation(
            "TrainingPlan.tasks",
            lambda: TrainingPlan(
                id="plan-1",
                profile_id="profile-1",
                created_at=START,
                plan_date=PLAN_DATE,
                tasks=[],
            ),
        )
        self.assert_validation(
            "CoachReport.summary",
            lambda: CoachReport(
                id="report-1",
                profile_id="profile-1",
                generated_at=START,
                summary=" ",
                evidence_refs=[evidence()],
            ),
        )

    def test_boundaries_for_key_modes_accuracy_normalized_values_and_zeroes(
        self,
    ) -> None:
        for mode in (KeyMode.FOUR_K, KeyMode.SEVEN_K):
            with self.subTest(mode=mode):
                self.assertEqual(score(key_mode=mode, accuracy=0).accuracy, 0.0)

        self.assertEqual(score(accuracy=100).accuracy, 100.0)
        self.assertEqual(score(score=0, combo=0, misses=0).score, 0)
        self.assertEqual(
            MapMetadata(
                id="map-1",
                game=GameId.OSU_MANIA,
                title="Song",
                artist="Artist",
                creator="Mapper",
                version="Easy",
                key_mode=KeyMode.SEVEN_K,
                difficulty=0,
            ).difficulty,
            0.0,
        )
        self.assertEqual(
            ReplayMetadata(
                id="replay-1",
                game=GameId.OSU_MANIA,
                file_name="play.osr",
                registered_at=START,
                support_status=ReplaySupportStatus.UNSUPPORTED,
                file_size_bytes=0,
            ).file_size_bytes,
            0,
        )
        self.assertEqual(weakness(severity=0, confidence=1).severity, 0.0)
        self.assertEqual(weakness(severity=1, confidence=0).confidence, 0.0)
        self.assertEqual(
            TrainingTask(id="task-1", goal="Warm up", duration_minutes=1)
            .duration_minutes,
            1,
        )
        self.assert_validation(
            "TrainingTask.duration_minutes",
            lambda: TrainingTask(id="task-1", goal="Warm up", duration_minutes=0),
        )

    def test_invalid_numeric_values_are_rejected(self) -> None:
        invalid_cases = [
            ("ScoreRecord.score", lambda: score(score=-1)),
            ("ScoreRecord.score", lambda: score(score=True)),
            ("ScoreRecord.accuracy", lambda: score(accuracy=-0.1)),
            ("ScoreRecord.accuracy", lambda: score(accuracy=100.1)),
            ("ScoreRecord.accuracy", lambda: score(accuracy=math.nan)),
            ("ScoreRecord.accuracy", lambda: score(accuracy=math.inf)),
            ("ScoreRecord.combo", lambda: score(combo=-1)),
            ("ScoreRecord.misses", lambda: score(misses=True)),
            (
                "PlayerProfile.current_pp",
                lambda: PlayerProfile(
                    id="profile-1",
                    display_name="Mira",
                    primary_game=GameId.OSU_MANIA,
                    created_at=START,
                    current_pp=-1,
                ),
            ),
            (
                "PlayerProfile.current_pp",
                lambda: PlayerProfile(
                    id="profile-1",
                    display_name="Mira",
                    primary_game=GameId.OSU_MANIA,
                    created_at=START,
                    current_pp=math.inf,
                ),
            ),
            (
                "MapMetadata.difficulty",
                lambda: MapMetadata(
                    id="map-1",
                    game=GameId.OSU_MANIA,
                    title="Song",
                    artist="Artist",
                    creator="Mapper",
                    version="Hard",
                    key_mode=KeyMode.FOUR_K,
                    difficulty=math.nan,
                ),
            ),
            (
                "ReplayMetadata.file_size_bytes",
                lambda: ReplayMetadata(
                    id="replay-1",
                    game=GameId.OSU_MANIA,
                    file_name="play.osr",
                    registered_at=START,
                    support_status=ReplaySupportStatus.UNSUPPORTED,
                    file_size_bytes=-1,
                ),
            ),
            ("WeaknessSignal.severity", lambda: weakness(severity=-0.01)),
            ("WeaknessSignal.confidence", lambda: weakness(confidence=1.01)),
            ("WeaknessSignal.confidence", lambda: weakness(confidence=True)),
            (
                "ScoreRecord.source_metadata",
                lambda: score(source_metadata={"unbounded_numeric": 4}),
            ),
        ]

        for pattern, factory in invalid_cases:
            with self.subTest(pattern=pattern):
                self.assert_validation(pattern, factory)

    def test_timezone_awareness_and_session_ordering(self) -> None:
        naive = datetime(2026, 1, 1, 12, 0)
        non_utc = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=7)))

        self.assert_validation("PlayerProfile.created_at", lambda: PlayerProfile(
            id="profile-1",
            display_name="Mira",
            primary_game=GameId.OSU_MANIA,
            created_at=naive,
        ))
        self.assert_validation("PlayerProfile.created_at", lambda: PlayerProfile(
            id="profile-1",
            display_name="Mira",
            primary_game=GameId.OSU_MANIA,
            created_at=non_utc,
        ))
        self.assert_validation("PracticeSession.ended_at", lambda: PracticeSession(
            id="session-1",
            profile_id="profile-1",
            started_at=END,
            ended_at=START,
            status=SessionStatus.COMPLETED,
        ))

    def test_duplicate_values_are_rejected_within_aggregates(self) -> None:
        duplicate_ref = evidence("score-1")
        self.assert_validation(
            "PlayerProfile.focus_modes",
            lambda: PlayerProfile(
                id="profile-1",
                display_name="Mira",
                primary_game=GameId.OSU_MANIA,
                created_at=START,
                focus_modes=["4k", KeyMode.FOUR_K],
            ),
        )
        self.assert_validation(
            "WeaknessSignal.evidence_refs",
            lambda: weakness(evidence_refs=[evidence("score-1"), duplicate_ref]),
        )
        self.assert_validation(
            "AnalysisResult.covered_score_ids",
            lambda: AnalysisResult(
                id="analysis-1",
                profile_id="profile-1",
                generated_at=START,
                covered_session_ids=[],
                covered_score_ids=["score-1", "score-1"],
                weakness_signals=[],
            ),
        )
        self.assert_validation(
            "TrainingPlan.tasks",
            lambda: TrainingPlan(
                id="plan-1",
                profile_id="profile-1",
                created_at=START,
                plan_date=PLAN_DATE,
                tasks=[
                    TrainingTask(id="task-1", goal="Warm up", duration_minutes=5),
                    TrainingTask(id="task-1", goal="Repeat", duration_minutes=5),
                ],
            ),
        )


class DomainSerializationTests(unittest.TestCase):
    def test_immutable_collection_and_defensive_copy_behavior(self) -> None:
        modes = [KeyMode.FOUR_K]
        goals = ["Improve timing"]
        metadata = {"client": "osu"}
        profile = PlayerProfile(
            id="profile-1",
            display_name="Mira",
            primary_game=GameId.OSU_MANIA,
            created_at=START,
            focus_modes=modes,
            goals=goals,
        )
        played_score = score(source_metadata=metadata)

        modes.append(KeyMode.SEVEN_K)
        goals.append("Late mutation")
        metadata["client"] = "changed"

        self.assertEqual(profile.focus_modes, (KeyMode.FOUR_K,))
        self.assertEqual(profile.goals, ("Improve timing",))
        self.assertEqual(played_score.source_metadata["client"], "osu")
        self.assertIsInstance(profile.focus_modes, tuple)
        with self.assertRaises(TypeError):
            played_score.source_metadata["new"] = "value"

    def test_enum_serialization_and_unknown_enum_reconstruction(self) -> None:
        profile = PlayerProfile(
            id="profile-1",
            display_name="Mira",
            primary_game=GameId.OSU_MANIA,
            created_at=START,
            focus_modes=[KeyMode.FOUR_K],
        )

        self.assertEqual(profile.to_dict()["primary_game"], "osu_mania")
        self.assertEqual(profile.to_dict()["focus_modes"], ["4k"])
        self.assert_validation(
            "PlayerProfile.primary_game",
            lambda: PlayerProfile.from_dict(
                {
                    **profile.to_dict(),
                    "primary_game": "future_game",
                }
            ),
        )
        self.assert_validation(
            "ScoreRecord.key_mode",
            lambda: ScoreRecord.from_dict(
                {
                    **score().to_dict(),
                    "key_mode": "6k",
                }
            ),
        )

    def assert_validation(self, pattern: str, factory: object) -> None:
        with self.assertRaisesRegex(DomainValidationError, pattern):
            factory()

    def test_deterministic_to_dict_and_round_trip_for_nested_aggregates(self) -> None:
        signal = weakness()
        analysis = AnalysisResult(
            id="analysis-1",
            profile_id="profile-1",
            generated_at=END,
            covered_session_ids=["session-1"],
            covered_score_ids=["score-1"],
            weakness_signals=[signal],
        )
        plan = TrainingPlan(
            id="plan-1",
            profile_id="profile-1",
            created_at=END,
            plan_date=PLAN_DATE,
            tasks=[
                TrainingTask(
                    id="task-1",
                    goal="Play timing drills.",
                    duration_minutes=15,
                    evidence_refs=[evidence()],
                    weakness_categories=[WeaknessCategory.TIMING],
                )
            ],
        )
        report = CoachReport(
            id="report-1",
            profile_id="profile-1",
            generated_at=END,
            summary="Timing needs attention.",
            evidence_refs=[evidence()],
            analysis_id=analysis.id,
            plan_id=plan.id,
        )

        expected_analysis = {
            "id": "analysis-1",
            "profile_id": "profile-1",
            "generated_at": "2026-01-01T13:00:00Z",
            "covered_session_ids": ["session-1"],
            "covered_score_ids": ["score-1"],
            "weakness_signals": [signal.to_dict()],
            "insufficient_evidence": False,
            "notes": None,
        }
        self.assertEqual(analysis.to_dict(), expected_analysis)
        self.assertEqual(AnalysisResult.from_dict(analysis.to_dict()), analysis)
        self.assertEqual(TrainingPlan.from_dict(plan.to_dict()), plan)
        self.assertEqual(CoachReport.from_dict(report.to_dict()), report)
        self.assertEqual(plan.to_dict()["total_duration_minutes"], 15)

    def test_training_plan_rejects_contradictory_serialized_total(self) -> None:
        plan_dict = TrainingPlan(
            id="plan-1",
            profile_id="profile-1",
            created_at=END,
            plan_date=PLAN_DATE,
            tasks=[TrainingTask(id="task-1", goal="Warm up", duration_minutes=15)],
        ).to_dict()
        plan_dict["total_duration_minutes"] = 14

        self.assert_validation(
            "TrainingPlan.total_duration_minutes",
            lambda: TrainingPlan.from_dict(plan_dict),
        )

    def test_analysis_distinguishes_no_weaknesses_from_insufficient_evidence(
        self,
    ) -> None:
        no_detected_weakness = AnalysisResult(
            id="analysis-1",
            profile_id="profile-1",
            generated_at=END,
            covered_session_ids=["session-1"],
            covered_score_ids=[],
            weakness_signals=[],
            insufficient_evidence=False,
        )
        insufficient = AnalysisResult(
            id="analysis-2",
            profile_id="profile-1",
            generated_at=END,
            covered_session_ids=["session-1"],
            covered_score_ids=[],
            weakness_signals=[],
            insufficient_evidence=True,
        )

        self.assertFalse(no_detected_weakness.insufficient_evidence)
        self.assertTrue(insufficient.insufficient_evidence)

    def test_report_cannot_claim_grounding_without_evidence(self) -> None:
        self.assert_validation(
            "CoachReport.grounded_in_evidence",
            lambda: CoachReport(
                id="report-1",
                profile_id="profile-1",
                generated_at=END,
                summary="Ungrounded note.",
                evidence_refs=[],
                grounded_in_evidence=True,
            ),
        )
        ungrounded = CoachReport(
            id="report-1",
            profile_id="profile-1",
            generated_at=END,
            summary="Ungrounded note.",
            evidence_refs=[],
            grounded_in_evidence=False,
        )
        self.assertFalse(ungrounded.grounded_in_evidence)


class DomainBoundaryTests(unittest.TestCase):
    def test_core_import_has_no_file_socket_or_network_side_effects(self) -> None:
        for module_name in ("game_assistant.core.domain", "game_assistant.core"):
            sys.modules.pop(module_name, None)

        with (
            mock.patch("builtins.open", side_effect=AssertionError("file I/O")),
            mock.patch.object(socket, "socket", side_effect=AssertionError("socket I/O")),
        ):
            self.assertIsNotNone(importlib.import_module("game_assistant.core"))

    def test_domain_import_does_not_introduce_adapter_or_persistence_behavior(
        self,
    ) -> None:
        for module_name in (
            "game_assistant.core.domain",
            "game_assistant.core",
            "game_assistant.adapters",
            "game_assistant.storage",
        ):
            sys.modules.pop(module_name, None)

        importlib.import_module("game_assistant.core")

        self.assertNotIn("game_assistant.adapters", sys.modules)
        self.assertNotIn("game_assistant.storage", sys.modules)


if __name__ == "__main__":
    unittest.main()
