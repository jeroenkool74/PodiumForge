from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.enums import (
    LeaderboardMetric,
    ScoreDirection,
    TournamentFormat,
    TournamentParticipantType,
)
from app.models import User
from app.repositories.tournaments import get_tournament_by_identifier
from app.schemas.match import MatchResultInput, MatchResultsUpsertRequest
from app.schemas.tournament import (
    ParticipantCreateRequest,
    PlacementPointsInput,
    TournamentCreateRequest,
)
from app.services.match_service import upsert_match_results
from app.services.progression_service import generate_next_round
from app.services.standings_service import (
    calculate_standings,
    serialize_dashboard,
    serialize_tournament_detail,
)
from app.services.tournament_builder import add_participant, create_tournament


def admin_user(db_session: Session) -> User:
    return db_session.query(User).filter(User.email == "admin@podiumforge.local").one()


def test_elimination_flow_assigns_qualified_and_classification_places(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Friday LAN FFA",
            description="demo",
            format=TournamentFormat.FFA_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=5,
            participants=["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
            points_scheme=[
                PlacementPointsInput(placement=1, points=10),
                PlacementPointsInput(placement=2, points=7),
                PlacementPointsInput(placement=3, points=5),
                PlacementPointsInput(placement=4, points=3),
                PlacementPointsInput(placement=5, points=1),
            ],
            advance_count=2,
        ),
        admin_user(db_session),
    )
    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }

    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=20),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=18),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=14),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=10),
                MatchResultInput(participant_id=a_lookup["E"], rank=5, score=7),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["F"], rank=1, score=19),
                MatchResultInput(participant_id=b_lookup["G"], rank=2, score=17),
                MatchResultInput(participant_id=b_lookup["H"], rank=3, score=13),
                MatchResultInput(participant_id=b_lookup["I"], rank=4, score=9),
                MatchResultInput(participant_id=b_lookup["J"], rank=5, score=6),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    standings = calculate_standings(refreshed)
    qualified = [
        entry["display_name"]
        for entry in standings
        if entry["current_status"] == "QUALIFIED"
    ]
    assert qualified == ["A", "F", "B", "G"]

    placements = {
        entry["display_name"]: entry["final_placement"] for entry in standings
    }
    assert placements["C"] == 5
    assert placements["H"] == 6
    assert placements["D"] == 7
    assert placements["E"] == 9

    generate_next_round(db_session, refreshed)
    final_tournament = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert final_tournament is not None
    assert final_tournament.status == "LIVE"
    final_round = sorted(
        final_tournament.stages[0].rounds, key=lambda item: item.number
    )[-1]
    final_match = final_round.matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in final_match.participants
    }
    upsert_match_results(
        db_session,
        final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=lookup["A"], rank=1, score=30),
                MatchResultInput(participant_id=lookup["F"], rank=2, score=28),
                MatchResultInput(participant_id=lookup["B"], rank=3, score=24),
                MatchResultInput(participant_id=lookup["G"], rank=4, score=21),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    final_standings = calculate_standings(completed)
    final_places = {
        entry["display_name"]: entry["final_placement"] for entry in final_standings
    }
    assert [
        final_places[name]
        for name in ["A", "F", "B", "G", "C", "H", "D", "I", "E", "J"]
    ] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def test_standalone_match_immediately_gets_full_ranking(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Showmatch",
            description="demo",
            format=TournamentFormat.STANDALONE_MATCH,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=5,
            participants=["Alpha", "Bravo", "Charlie", "Delta", "Echo"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
        ),
        admin_user(db_session),
    )
    match = tournament.stages[0].rounds[0].matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match.participants
    }
    upsert_match_results(
        db_session,
        match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=lookup["Charlie"], rank=1, score=10),
                MatchResultInput(participant_id=lookup["Alpha"], rank=2, score=9),
                MatchResultInput(participant_id=lookup["Echo"], rank=3, score=8),
                MatchResultInput(participant_id=lookup["Bravo"], rank=4, score=7),
                MatchResultInput(participant_id=lookup["Delta"], rank=5, score=6),
            ]
        ),
    )

    standings = calculate_standings(
        get_tournament_by_identifier(db_session, tournament.id, public_only=False)
    )
    placements = {
        entry["display_name"]: entry["final_placement"] for entry in standings
    }
    assert placements == {"Charlie": 1, "Alpha": 2, "Echo": 3, "Bravo": 4, "Delta": 5}


def test_group_points_advances_from_shared_leaderboard(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Points Race",
            description="demo",
            format=TournamentFormat.GROUP_POINTS,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F", "G", "H"],
            points_scheme=[
                PlacementPointsInput(placement=1, points=12),
                PlacementPointsInput(placement=2, points=8),
                PlacementPointsInput(placement=3, points=5),
                PlacementPointsInput(placement=4, points=2),
            ],
            advance_count=4,
        ),
        admin_user(db_session),
    )
    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }
    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=17),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=13),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=10),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=6),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["E"], rank=1, score=18),
                MatchResultInput(participant_id=b_lookup["F"], rank=2, score=14),
                MatchResultInput(participant_id=b_lookup["G"], rank=3, score=9),
                MatchResultInput(participant_id=b_lookup["H"], rank=4, score=5),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    next_round = generate_next_round(db_session, refreshed)
    assert next_round.name == "Final"

    after_generation = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_generation is not None
    assert after_generation.status == "LIVE"
    final_match = after_generation.stages[0].rounds[-1].matches[0]
    finalists = sorted(
        slot.participant.display_name for slot in final_match.participants
    )
    assert finalists == ["A", "B", "E", "F"]


def test_group_points_can_advance_from_score_leaderboard(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Score Ladder",
            description="demo",
            format=TournamentFormat.GROUP_POINTS,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F", "G", "H"],
            points_scheme=[],
            advance_count=4,
            leaderboard_metric=LeaderboardMetric.SCORE,
            score_direction=ScoreDirection.LOWER_IS_BETTER,
            score_label="Time",
        ),
        admin_user(db_session),
    )
    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }

    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=40),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=42),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=49),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=55),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["E"], rank=1, score=39),
                MatchResultInput(participant_id=b_lookup["F"], rank=2, score=41),
                MatchResultInput(participant_id=b_lookup["G"], rank=3, score=50),
                MatchResultInput(participant_id=b_lookup["H"], rank=4, score=57),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    next_round = generate_next_round(db_session, refreshed)
    assert next_round.name == "Final"

    after_generation = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_generation is not None
    final_match = after_generation.stages[0].rounds[-1].matches[0]
    finalists = sorted(
        slot.participant.display_name for slot in final_match.participants
    )
    assert finalists == ["A", "B", "E", "F"]


def test_leaderboard_series_uses_fixed_rounds_and_score_totals(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Measured Series",
            description="demo",
            format=TournamentFormat.LEADERBOARD_SERIES,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=3,
            participants=["A", "B", "C", "D", "E", "F"],
            points_scheme=[],
            round_count=3,
            leaderboard_metric=LeaderboardMetric.SCORE,
            score_direction=ScoreDirection.LOWER_IS_BETTER,
            score_label="Time",
        ),
        admin_user(db_session),
    )

    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }
    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=10),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=12),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=14),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["D"], rank=1, score=9),
                MatchResultInput(participant_id=b_lookup["E"], rank=2, score=13),
                MatchResultInput(participant_id=b_lookup["F"], rank=3, score=18),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    round_two = generate_next_round(db_session, refreshed)
    assert round_two.number == 2
    assert not round_two.is_final

    match_a, match_b = sorted(round_two.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }
    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=2, score=11),
                MatchResultInput(participant_id=a_lookup["B"], rank=1, score=10),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=16),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["D"], rank=1, score=8),
                MatchResultInput(participant_id=b_lookup["E"], rank=2, score=12),
                MatchResultInput(participant_id=b_lookup["F"], rank=3, score=14),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    round_three = generate_next_round(db_session, refreshed)
    assert round_three.number == 3
    assert round_three.is_final

    match_a, match_b = sorted(round_three.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }
    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=9),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=13),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=15),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["D"], rank=1, score=7),
                MatchResultInput(participant_id=b_lookup["E"], rank=2, score=11),
                MatchResultInput(participant_id=b_lookup["F"], rank=3, score=16),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert completed is not None
    standings = calculate_standings(completed)
    placements = {
        entry["display_name"]: entry["final_placement"] for entry in standings
    }
    totals = {entry["display_name"]: entry["score_total"] for entry in standings}
    assert [placements[name] for name in ["D", "A", "B", "E", "C", "F"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert totals == {
        "D": 24,
        "A": 30,
        "B": 35,
        "E": 36,
        "C": 45,
        "F": 48,
    }


def test_round_robin_completes_full_schedule_and_uses_table_for_final_places(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="League Night",
            description="demo",
            format=TournamentFormat.ROUND_ROBIN,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D"],
        ),
        admin_user(db_session),
    )

    round_one = tournament.stages[0].rounds[0]
    assert round_one.name == "Round 1"
    match_one, match_two = sorted(round_one.matches, key=lambda item: item.sequence)
    round_one_pairs = sorted(
        sorted(slot.participant.display_name for slot in match.participants)
        for match in (match_one, match_two)
    )
    assert round_one_pairs == [["A", "D"], ["B", "C"]]

    round_one_lookup = {
        match.id: {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        for match in (match_one, match_two)
    }
    upsert_match_results(
        db_session,
        match_one,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_one_lookup[match_one.id]["A"], rank=1, score=12
                ),
                MatchResultInput(
                    participant_id=round_one_lookup[match_one.id]["D"], rank=2, score=8
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_two,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_one_lookup[match_two.id]["B"], rank=1, score=11
                ),
                MatchResultInput(
                    participant_id=round_one_lookup[match_two.id]["C"], rank=2, score=9
                ),
            ]
        ),
    )

    after_round_one = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_round_one is not None
    round_one_standings = calculate_standings(after_round_one)
    assert {entry["current_status"] for entry in round_one_standings} == {"ACTIVE"}

    round_two = generate_next_round(db_session, after_round_one)
    round_two_matches = sorted(round_two.matches, key=lambda item: item.sequence)
    round_two_pairs = sorted(
        sorted(slot.participant.display_name for slot in match.participants)
        for match in round_two_matches
    )
    assert round_two_pairs == [["A", "C"], ["B", "D"]]

    round_two_lookup = {
        match.id: {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        for match in round_two_matches
    }
    upsert_match_results(
        db_session,
        round_two_matches[0],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[0].id]["C"],
                    rank=1,
                    score=13,
                ),
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[0].id]["A"],
                    rank=2,
                    score=10,
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        round_two_matches[1],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[1].id]["D"],
                    rank=1,
                    score=14,
                ),
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[1].id]["B"],
                    rank=2,
                    score=9,
                ),
            ]
        ),
    )

    after_round_two = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_round_two is not None
    round_three = generate_next_round(db_session, after_round_two)
    assert round_three.is_final is True
    round_three_matches = sorted(round_three.matches, key=lambda item: item.sequence)
    round_three_pairs = sorted(
        sorted(slot.participant.display_name for slot in match.participants)
        for match in round_three_matches
    )
    assert round_three_pairs == [["A", "B"], ["C", "D"]]

    round_three_lookup = {
        match.id: {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        for match in round_three_matches
    }
    upsert_match_results(
        db_session,
        round_three_matches[0],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_three_lookup[round_three_matches[0].id]["A"],
                    rank=1,
                    score=15,
                ),
                MatchResultInput(
                    participant_id=round_three_lookup[round_three_matches[0].id]["B"],
                    rank=2,
                    score=11,
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        round_three_matches[1],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_three_lookup[round_three_matches[1].id]["C"],
                    rank=1,
                    score=16,
                ),
                MatchResultInput(
                    participant_id=round_three_lookup[round_three_matches[1].id]["D"],
                    rank=2,
                    score=12,
                ),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert completed is not None
    assert completed.status == "COMPLETED"
    completed_detail = serialize_tournament_detail(completed)
    assert all(
        match["results_locked"]
        for match in completed_detail["stages"][0]["rounds"][-1]["matches"]
    )

    final_standings = calculate_standings(completed)
    assert [entry["display_name"] for entry in final_standings] == ["A", "C", "B", "D"]
    assert [entry["final_placement"] for entry in final_standings] == [1, 2, 3, 4]

    dashboard = serialize_dashboard(completed)
    assert dashboard["current_round_name"] is None
    assert [entry["display_name"] for entry in dashboard["podium"]] == ["A", "C", "B"]


def test_swiss_pairs_by_record_and_finishes_on_points_table(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Swiss Night",
            description="demo",
            format=TournamentFormat.SWISS,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D"],
        ),
        admin_user(db_session),
    )

    round_one = tournament.stages[0].rounds[0]
    round_one_matches = sorted(round_one.matches, key=lambda item: item.sequence)
    round_one_pairs = sorted(
        sorted(slot.participant.display_name for slot in match.participants)
        for match in round_one_matches
    )
    assert round_one_pairs == [["A", "C"], ["B", "D"]]

    round_one_lookup = {
        match.id: {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        for match in round_one_matches
    }
    upsert_match_results(
        db_session,
        round_one_matches[0],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_one_lookup[round_one_matches[0].id]["A"],
                    rank=1,
                    score=12,
                ),
                MatchResultInput(
                    participant_id=round_one_lookup[round_one_matches[0].id]["C"],
                    rank=2,
                    score=8,
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        round_one_matches[1],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_one_lookup[round_one_matches[1].id]["D"],
                    rank=1,
                    score=11,
                ),
                MatchResultInput(
                    participant_id=round_one_lookup[round_one_matches[1].id]["B"],
                    rank=2,
                    score=7,
                ),
            ]
        ),
    )

    after_round_one = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_round_one is not None
    assert {
        entry["current_status"] for entry in calculate_standings(after_round_one)
    } == {"ACTIVE"}

    round_two = generate_next_round(db_session, after_round_one)
    assert round_two.is_final is True
    round_two_matches = sorted(round_two.matches, key=lambda item: item.sequence)
    round_two_pairs = sorted(
        sorted(slot.participant.display_name for slot in match.participants)
        for match in round_two_matches
    )
    assert round_two_pairs == [["A", "D"], ["B", "C"]]

    round_two_lookup = {
        match.id: {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        for match in round_two_matches
    }
    upsert_match_results(
        db_session,
        round_two_matches[0],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[0].id]["A"],
                    rank=1,
                    score=13,
                ),
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[0].id]["D"],
                    rank=2,
                    score=9,
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        round_two_matches[1],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[1].id]["B"],
                    rank=1,
                    score=10,
                ),
                MatchResultInput(
                    participant_id=round_two_lookup[round_two_matches[1].id]["C"],
                    rank=2,
                    score=6,
                ),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert completed is not None
    assert completed.status == "COMPLETED"

    final_standings = calculate_standings(completed)
    assert [entry["display_name"] for entry in final_standings] == ["A", "B", "D", "C"]
    assert [entry["final_placement"] for entry in final_standings] == [1, 2, 3, 4]


def test_swiss_rotates_byes_for_odd_field(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Swiss Bye Test",
            description="demo",
            format=TournamentFormat.SWISS,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D", "E"],
        ),
        admin_user(db_session),
    )

    round_one = tournament.stages[0].rounds[0]
    round_one_matches = sorted(round_one.matches, key=lambda item: item.sequence)
    round_one_byes = [
        match for match in round_one_matches if len(match.participants) == 1
    ]
    assert len(round_one_byes) == 1
    round_one_bye_name = round_one_byes[0].participants[0].participant.display_name
    assert round_one_bye_name == "E"
    assert round_one_byes[0].status == "COMPLETED"

    for match in round_one_matches:
        if len(match.participants) == 1:
            continue
        lookup = {
            slot.participant.display_name: slot.participant_id
            for slot in match.participants
        }
        winner = min(lookup)
        loser = max(lookup)
        upsert_match_results(
            db_session,
            match,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=lookup[winner], rank=1, score=10),
                    MatchResultInput(participant_id=lookup[loser], rank=2, score=5),
                ]
            ),
        )

    after_round_one = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_round_one is not None
    round_two = generate_next_round(db_session, after_round_one)
    round_two_matches = sorted(round_two.matches, key=lambda item: item.sequence)
    round_two_byes = [
        match for match in round_two_matches if len(match.participants) == 1
    ]
    assert len(round_two_byes) == 1
    round_two_bye_name = round_two_byes[0].participants[0].participant.display_name
    assert round_two_bye_name != round_one_bye_name

    round_one_pairs = {
        frozenset(slot.participant.display_name for slot in match.participants)
        for match in round_one_matches
        if len(match.participants) == 2
    }
    round_two_pairs = {
        frozenset(slot.participant.display_name for slot in match.participants)
        for match in round_two_matches
        if len(match.participants) == 2
    }
    assert round_one_pairs.isdisjoint(round_two_pairs)


def test_page_playoff_gives_top_two_a_second_chance_and_locks_places(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Page Playoff Night",
            description="demo",
            format=TournamentFormat.PAGE_PLAYOFF,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D"],
        ),
        admin_user(db_session),
    )

    opening_round = tournament.stages[0].rounds[0]
    assert opening_round.name == "Opening Round"
    qualifier_match = next(
        match for match in opening_round.matches if match.name == "Qualifier"
    )
    eliminator_match = next(
        match for match in opening_round.matches if match.name == "Eliminator"
    )
    assert sorted(
        slot.participant.display_name for slot in qualifier_match.participants
    ) == ["A", "B"]
    assert sorted(
        slot.participant.display_name for slot in eliminator_match.participants
    ) == ["C", "D"]

    qualifier_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in qualifier_match.participants
    }
    eliminator_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in eliminator_match.participants
    }
    upsert_match_results(
        db_session,
        qualifier_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=qualifier_lookup["B"], rank=1, score=11
                ),
                MatchResultInput(participant_id=qualifier_lookup["A"], rank=2, score=8),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        eliminator_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=eliminator_lookup["D"], rank=1, score=10
                ),
                MatchResultInput(
                    participant_id=eliminator_lookup["C"], rank=2, score=7
                ),
            ]
        ),
    )

    after_opening = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_opening is not None
    opening_standings = calculate_standings(after_opening)
    opening_statuses = {
        entry["display_name"]: entry["current_status"] for entry in opening_standings
    }
    assert opening_statuses == {
        "A": "QUALIFIED",
        "B": "QUALIFIED",
        "C": "ELIMINATED",
        "D": "QUALIFIED",
    }

    preliminary_round = generate_next_round(db_session, after_opening)
    assert preliminary_round.name == "Preliminary Final"
    preliminary_match = preliminary_round.matches[0]
    assert sorted(
        slot.participant.display_name for slot in preliminary_match.participants
    ) == ["A", "D"]
    preliminary_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in preliminary_match.participants
    }
    upsert_match_results(
        db_session,
        preliminary_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=preliminary_lookup["A"], rank=1, score=12
                ),
                MatchResultInput(
                    participant_id=preliminary_lookup["D"], rank=2, score=9
                ),
            ]
        ),
    )

    after_preliminary = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert after_preliminary is not None
    grand_final_round = generate_next_round(db_session, after_preliminary)
    assert grand_final_round.name == "Grand Final"
    assert grand_final_round.is_final is True
    grand_final_match = grand_final_round.matches[0]
    assert sorted(
        slot.participant.display_name for slot in grand_final_match.participants
    ) == ["A", "B"]
    grand_final_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in grand_final_match.participants
    }
    upsert_match_results(
        db_session,
        grand_final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=grand_final_lookup["A"], rank=1, score=13
                ),
                MatchResultInput(
                    participant_id=grand_final_lookup["B"], rank=2, score=10
                ),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert completed is not None
    assert completed.status == "COMPLETED"

    final_standings = calculate_standings(completed)
    assert [entry["display_name"] for entry in final_standings] == ["A", "B", "D", "C"]
    assert [entry["final_placement"] for entry in final_standings] == [1, 2, 3, 4]

    dashboard = serialize_dashboard(completed)
    assert [entry["display_name"] for entry in dashboard["podium"]] == ["A", "B", "D"]


def test_tournament_stays_live_between_completed_round_and_next_round_generation(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Between Rounds",
            description="demo",
            format=TournamentFormat.FFA_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F", "G", "H"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
            advance_count=2,
        ),
        admin_user(db_session),
    )
    match_a, match_b = sorted(
        tournament.stages[0].rounds[0].matches, key=lambda item: item.sequence
    )
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }
    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=15),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=13),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=9),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=6),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["E"], rank=1, score=14),
                MatchResultInput(participant_id=b_lookup["F"], rank=2, score=11),
                MatchResultInput(participant_id=b_lookup["G"], rank=3, score=8),
                MatchResultInput(participant_id=b_lookup["H"], rank=4, score=5),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    assert refreshed.status == "LIVE"


def test_completed_dashboard_hides_current_round_and_uses_final_podium(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Completed Dashboard",
            description="demo",
            format=TournamentFormat.STANDALONE_MATCH,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
        ),
        admin_user(db_session),
    )
    match = tournament.stages[0].rounds[0].matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match.participants
    }
    upsert_match_results(
        db_session,
        match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=lookup["B"], rank=1, score=12),
                MatchResultInput(participant_id=lookup["A"], rank=2, score=10),
                MatchResultInput(participant_id=lookup["D"], rank=3, score=9),
                MatchResultInput(participant_id=lookup["C"], rank=4, score=7),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    dashboard = serialize_dashboard(refreshed)
    assert dashboard["current_round_name"] is None
    assert dashboard["upcoming_matches"] == []
    assert [entry["display_name"] for entry in dashboard["podium"]] == [
        "B",
        "A",
        "D",
    ]


def test_generate_next_round_is_idempotent_for_fresh_round(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Idempotent FFA",
            description="demo",
            format=TournamentFormat.FFA_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F", "G", "H"],
            points_scheme=[
                PlacementPointsInput(placement=1, points=10),
                PlacementPointsInput(placement=2, points=7),
                PlacementPointsInput(placement=3, points=5),
                PlacementPointsInput(placement=4, points=3),
            ],
            advance_count=2,
        ),
        admin_user(db_session),
    )

    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }

    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=15),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=12),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=9),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=6),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["E"], rank=1, score=14),
                MatchResultInput(participant_id=b_lookup["F"], rank=2, score=11),
                MatchResultInput(participant_id=b_lookup["G"], rank=3, score=8),
                MatchResultInput(participant_id=b_lookup["H"], rank=4, score=5),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None

    first_generated = generate_next_round(db_session, refreshed)
    refreshed_again = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed_again is not None
    same_generated = generate_next_round(db_session, refreshed_again)

    assert first_generated.id == same_generated.id


def test_bracket_flow_supports_seeded_byes_and_multiple_rounds(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Bracket Demo",
            description="demo",
            format=TournamentFormat.BRACKET,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F"],
            points_scheme=[PlacementPointsInput(placement=1, points=1)],
        ),
        admin_user(db_session),
    )
    round_one = tournament.stages[0].rounds[0]
    assert round_one.name == "Quarterfinals"
    quarterfinals = sorted(round_one.matches, key=lambda item: item.sequence)
    assert [match.status for match in quarterfinals] == [
        "COMPLETED",
        "SCHEDULED",
        "COMPLETED",
        "SCHEDULED",
    ]

    match_two_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in quarterfinals[1].participants
    }
    match_four_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in quarterfinals[3].participants
    }
    upsert_match_results(
        db_session,
        quarterfinals[1],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=match_two_lookup["D"], rank=1, score=12
                ),
                MatchResultInput(participant_id=match_two_lookup["E"], rank=2, score=8),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        quarterfinals[3],
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=match_four_lookup["C"], rank=1, score=11
                ),
                MatchResultInput(
                    participant_id=match_four_lookup["F"], rank=2, score=7
                ),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    semifinal_round = generate_next_round(db_session, refreshed)
    assert semifinal_round.name == "Semifinals"
    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    assert refreshed.status == "LIVE"
    semifinal_a, semifinal_b = sorted(
        semifinal_round.matches, key=lambda item: item.sequence
    )
    assert [slot.participant.display_name for slot in semifinal_a.participants] == [
        "A",
        "D",
    ]
    assert [slot.participant.display_name for slot in semifinal_b.participants] == [
        "B",
        "C",
    ]

    semifinal_a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in semifinal_a.participants
    }
    semifinal_b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in semifinal_b.participants
    }
    upsert_match_results(
        db_session,
        semifinal_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=semifinal_a_lookup["A"], rank=1, score=15
                ),
                MatchResultInput(
                    participant_id=semifinal_a_lookup["D"], rank=2, score=9
                ),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        semifinal_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=semifinal_b_lookup["C"], rank=1, score=14
                ),
                MatchResultInput(
                    participant_id=semifinal_b_lookup["B"], rank=2, score=10
                ),
            ]
        ),
    )

    semifinals_complete = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    final_round = generate_next_round(db_session, semifinals_complete)
    assert final_round.name == "Final"
    final_match = final_round.matches[0]
    final_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in final_match.participants
    }
    assert sorted(final_lookup) == ["A", "C"]

    upsert_match_results(
        db_session,
        final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=final_lookup["C"], rank=1, score=18),
                MatchResultInput(participant_id=final_lookup["A"], rank=2, score=16),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    final_standings = calculate_standings(completed)
    placements = {
        entry["display_name"]: entry["final_placement"] for entry in final_standings
    }
    assert placements["C"] == 1
    assert placements["A"] == 2


def test_double_elimination_generates_losers_bracket_and_reset_final(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Double Elim Demo",
            description="demo",
            format=TournamentFormat.DOUBLE_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D"],
            points_scheme=[PlacementPointsInput(placement=1, points=3)],
        ),
        admin_user(db_session),
    )

    winners_round_one = tournament.stages[0].rounds[0]
    assert winners_round_one.name == "Winners Semifinals"
    winners_match_a, winners_match_b = sorted(
        winners_round_one.matches, key=lambda item: item.sequence
    )
    winners_a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in winners_match_a.participants
    }
    winners_b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in winners_match_b.participants
    }

    upsert_match_results(
        db_session,
        winners_match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=winners_a_lookup["A"], rank=1, score=13
                ),
                MatchResultInput(participant_id=winners_a_lookup["D"], rank=2, score=9),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        winners_match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=winners_b_lookup["B"], rank=1, score=12
                ),
                MatchResultInput(participant_id=winners_b_lookup["C"], rank=2, score=8),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    losers_round_one = generate_next_round(db_session, refreshed)
    assert losers_round_one.name == "Losers Round 1"
    losers_match = losers_round_one.matches[0]
    losers_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in losers_match.participants
    }
    assert sorted(losers_lookup) == ["C", "D"]

    upsert_match_results(
        db_session,
        losers_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=losers_lookup["D"], rank=1, score=11),
                MatchResultInput(participant_id=losers_lookup["C"], rank=2, score=7),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    winners_final = generate_next_round(db_session, refreshed)
    assert winners_final.name == "Winners Final"
    winners_final_match = winners_final.matches[0]
    winners_final_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in winners_final_match.participants
    }
    assert sorted(winners_final_lookup) == ["A", "B"]

    upsert_match_results(
        db_session,
        winners_final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=winners_final_lookup["A"], rank=1, score=14
                ),
                MatchResultInput(
                    participant_id=winners_final_lookup["B"], rank=2, score=10
                ),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    losers_final = generate_next_round(db_session, refreshed)
    assert losers_final.name == "Losers Final"
    losers_final_match = losers_final.matches[0]
    losers_final_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in losers_final_match.participants
    }
    assert sorted(losers_final_lookup) == ["B", "D"]

    upsert_match_results(
        db_session,
        losers_final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=losers_final_lookup["B"], rank=1, score=15
                ),
                MatchResultInput(
                    participant_id=losers_final_lookup["D"], rank=2, score=9
                ),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    grand_final = generate_next_round(db_session, refreshed)
    assert grand_final.name == "Grand Final"
    grand_final_match = grand_final.matches[0]
    grand_final_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in grand_final_match.participants
    }
    assert sorted(grand_final_lookup) == ["A", "B"]

    upsert_match_results(
        db_session,
        grand_final_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(
                    participant_id=grand_final_lookup["B"], rank=1, score=16
                ),
                MatchResultInput(
                    participant_id=grand_final_lookup["A"], rank=2, score=12
                ),
            ]
        ),
    )

    reset_ready = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert reset_ready is not None
    assert reset_ready.status == "LIVE"
    grand_final_reset = generate_next_round(db_session, reset_ready)
    assert grand_final_reset.name == "Grand Final Reset"
    reset_match = grand_final_reset.matches[0]
    reset_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in reset_match.participants
    }
    assert sorted(reset_lookup) == ["A", "B"]

    upsert_match_results(
        db_session,
        reset_match,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=reset_lookup["A"], rank=1, score=17),
                MatchResultInput(participant_id=reset_lookup["B"], rank=2, score=13),
            ]
        ),
    )

    completed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert completed is not None
    assert completed.status == "COMPLETED"
    final_standings = calculate_standings(completed)
    placements = {
        entry["display_name"]: entry["final_placement"] for entry in final_standings
    }
    assert placements["A"] == 1
    assert placements["B"] == 2
    assert placements["D"] == 3
    assert placements["C"] == 4


def test_tie_on_advancement_boundary_requires_resolution(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Tie Test",
            description="demo",
            format=TournamentFormat.FFA_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=5,
            participants=["A", "B", "C", "D", "E"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
            advance_count=2,
        ),
        admin_user(db_session),
    )
    match = tournament.stages[0].rounds[0].matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match.participants
    }

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            match,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=lookup["A"], rank=1, score=10),
                    MatchResultInput(participant_id=lookup["B"], rank=2),
                    MatchResultInput(participant_id=lookup["C"], rank=2),
                    MatchResultInput(participant_id=lookup["D"], rank=4, score=7),
                    MatchResultInput(participant_id=lookup["E"], rank=5, score=6),
                ]
            ),
        )

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            match,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=lookup["A"], rank=1, tie_group=1),
                    MatchResultInput(participant_id=lookup["B"], rank=2),
                    MatchResultInput(participant_id=lookup["C"], rank=3),
                    MatchResultInput(participant_id=lookup["D"], rank=4),
                ]
            ),
        )


def test_head_to_head_brackets_require_a_decisive_winner(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Decisive Bracket Test",
            description="demo",
            format=TournamentFormat.DOUBLE_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D"],
            points_scheme=[PlacementPointsInput(placement=1, points=3)],
        ),
        admin_user(db_session),
    )
    match = tournament.stages[0].rounds[0].matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match.participants
    }

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            match,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=lookup["A"], rank=1, tie_group=1),
                    MatchResultInput(participant_id=lookup["D"], rank=1, tie_group=1),
                ]
            ),
        )


def test_auto_bye_match_rejects_manual_result_entry(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Bracket Bye Lock",
            description="demo",
            format=TournamentFormat.BRACKET,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=2,
            participants=["A", "B", "C", "D", "E", "F"],
            points_scheme=[PlacementPointsInput(placement=1, points=1)],
        ),
        admin_user(db_session),
    )
    bye_match = sorted(
        tournament.stages[0].rounds[0].matches, key=lambda item: item.sequence
    )[0]
    participant_id = bye_match.participants[0].participant_id

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            bye_match,
            MatchResultsUpsertRequest(
                results=[MatchResultInput(participant_id=participant_id, rank=1)]
            ),
        )


def test_non_contiguous_places_require_tie_consistency(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Rank Shape Test",
            description="demo",
            format=TournamentFormat.STANDALONE_MATCH,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
        ),
        admin_user(db_session),
    )
    match = tournament.stages[0].rounds[0].matches[0]
    lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match.participants
    }

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            match,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=lookup["A"], rank=1),
                    MatchResultInput(participant_id=lookup["B"], rank=2),
                    MatchResultInput(participant_id=lookup["C"], rank=4),
                    MatchResultInput(participant_id=lookup["D"], rank=5),
                ]
            ),
        )


def test_duplicate_participant_names_are_rejected(db_session: Session) -> None:
    with pytest.raises(HTTPException):
        create_tournament(
            db_session,
            TournamentCreateRequest(
                name="Duplicate Names",
                description="demo",
                format=TournamentFormat.STANDALONE_MATCH,
                participant_type=TournamentParticipantType.PLAYER,
                match_size=4,
                participants=["A", "B", "a", "C"],
                points_scheme=[PlacementPointsInput(placement=1, points=10)],
            ),
            admin_user(db_session),
        )


def test_add_participant_rejects_duplicate_name(db_session: Session) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Participant Validation",
            description="demo",
            format=TournamentFormat.STANDALONE_MATCH,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D"],
            points_scheme=[PlacementPointsInput(placement=1, points=10)],
        ),
        admin_user(db_session),
    )

    with pytest.raises(HTTPException):
        add_participant(
            db_session,
            tournament,
            ParticipantCreateRequest(display_name="a"),
        )


def test_completed_round_cannot_be_edited_after_next_round_exists(
    db_session: Session,
) -> None:
    tournament = create_tournament(
        db_session,
        TournamentCreateRequest(
            name="Lock Previous Round",
            description="demo",
            format=TournamentFormat.FFA_ELIMINATION,
            participant_type=TournamentParticipantType.PLAYER,
            match_size=4,
            participants=["A", "B", "C", "D", "E", "F", "G", "H"],
            points_scheme=[
                PlacementPointsInput(placement=1, points=10),
                PlacementPointsInput(placement=2, points=7),
                PlacementPointsInput(placement=3, points=5),
                PlacementPointsInput(placement=4, points=3),
            ],
            advance_count=2,
        ),
        admin_user(db_session),
    )
    round_one = tournament.stages[0].rounds[0]
    match_a, match_b = sorted(round_one.matches, key=lambda item: item.sequence)
    a_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_a.participants
    }
    b_lookup = {
        slot.participant.display_name: slot.participant_id
        for slot in match_b.participants
    }

    upsert_match_results(
        db_session,
        match_a,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=a_lookup["A"], rank=1, score=10),
                MatchResultInput(participant_id=a_lookup["B"], rank=2, score=9),
                MatchResultInput(participant_id=a_lookup["C"], rank=3, score=8),
                MatchResultInput(participant_id=a_lookup["D"], rank=4, score=7),
            ]
        ),
    )
    upsert_match_results(
        db_session,
        match_b,
        MatchResultsUpsertRequest(
            results=[
                MatchResultInput(participant_id=b_lookup["E"], rank=1, score=10),
                MatchResultInput(participant_id=b_lookup["F"], rank=2, score=9),
                MatchResultInput(participant_id=b_lookup["G"], rank=3, score=8),
                MatchResultInput(participant_id=b_lookup["H"], rank=4, score=7),
            ]
        ),
    )

    refreshed = get_tournament_by_identifier(
        db_session, tournament.id, public_only=False
    )
    assert refreshed is not None
    generate_next_round(db_session, refreshed)

    with pytest.raises(HTTPException):
        upsert_match_results(
            db_session,
            match_a,
            MatchResultsUpsertRequest(
                results=[
                    MatchResultInput(participant_id=a_lookup["A"], rank=1, score=12),
                    MatchResultInput(participant_id=a_lookup["B"], rank=2, score=11),
                    MatchResultInput(participant_id=a_lookup["C"], rank=3, score=10),
                    MatchResultInput(participant_id=a_lookup["D"], rank=4, score=9),
                ]
            ),
        )
