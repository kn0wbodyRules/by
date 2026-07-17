import pytest

from app.core.exceptions import InvalidStateTransitionError
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.user import User
from app.services.job_state_machine import assert_transition, require_status, transition


@pytest.fixture()
def job(db):
    user = User(email="owner@example.com", hashed_password="x", is_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    job = Job(user_id=user.id, status=JobStatus.UPLOADED, project_name="Test", location="Tamil Nadu")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_valid_transition_succeeds(db, job):
    updated = transition(db, job, JobStatus.ROOMS_MANUAL)
    assert updated.status == JobStatus.ROOMS_MANUAL


def test_invalid_transition_rejected(db, job):
    with pytest.raises(InvalidStateTransitionError):
        transition(db, job, JobStatus.CALCULATED)


def test_full_happy_path_sequence(db, job):
    transition(db, job, JobStatus.ROOMS_MANUAL)
    transition(db, job, JobStatus.ROOMS_CONFIRMED)
    transition(db, job, JobStatus.CONSTRAINTS_SET)
    transition(db, job, JobStatus.CALCULATED)
    transition(db, job, JobStatus.EXPORTED)
    assert job.status == JobStatus.EXPORTED


def test_loopback_from_calculated_to_constraints_set(db, job):
    transition(db, job, JobStatus.ROOMS_MANUAL)
    transition(db, job, JobStatus.ROOMS_CONFIRMED)
    transition(db, job, JobStatus.CONSTRAINTS_SET)
    transition(db, job, JobStatus.CALCULATED)
    # what-if editing after calculation must loop back cleanly
    updated = transition(db, job, JobStatus.CONSTRAINTS_SET)
    assert updated.status == JobStatus.CONSTRAINTS_SET


def test_loopback_from_exported_to_constraints_set(db, job):
    transition(db, job, JobStatus.ROOMS_MANUAL)
    transition(db, job, JobStatus.ROOMS_CONFIRMED)
    transition(db, job, JobStatus.CONSTRAINTS_SET)
    transition(db, job, JobStatus.CALCULATED)
    transition(db, job, JobStatus.EXPORTED)
    updated = transition(db, job, JobStatus.CONSTRAINTS_SET)
    assert updated.status == JobStatus.CONSTRAINTS_SET


def test_cannot_calculate_before_constraints_set(db, job):
    transition(db, job, JobStatus.ROOMS_MANUAL)
    transition(db, job, JobStatus.ROOMS_CONFIRMED)
    with pytest.raises(InvalidStateTransitionError):
        transition(db, job, JobStatus.CALCULATED)


def test_require_status_passes_when_matching(job):
    require_status(job, JobStatus.UPLOADED, JobStatus.ROOMS_MANUAL)  # no raise


def test_require_status_raises_when_not_matching(job):
    with pytest.raises(InvalidStateTransitionError):
        require_status(job, JobStatus.CALCULATED)


def test_assert_transition_does_not_mutate(job):
    original_status = job.status
    with pytest.raises(InvalidStateTransitionError):
        assert_transition(job, JobStatus.EXPORTED)
    assert job.status == original_status
