import enum

from sqlalchemy import Enum as SAEnum


class JobStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    ROOMS_DETECTED = "rooms_detected"
    ROOMS_MANUAL = "rooms_manual"
    ROOMS_CONFIRMED = "rooms_confirmed"
    CONSTRAINTS_SET = "constraints_set"
    CALCULATED = "calculated"
    EXPORTED = "exported"


class RoomType(str, enum.Enum):
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    BATHROOM = "bathroom"
    LIVING_ROOM = "living_room"
    UTILITY = "utility"
    POOJA_ROOM = "pooja_room"
    STORE_ROOM = "store_room"
    BALCONY = "balcony"
    CORRIDOR = "corridor"
    OTHER = "other"


class RoomSource(str, enum.Enum):
    GEMINI_VISION = "gemini_vision"
    MANUAL = "manual"


class MaterialUnit(str, enum.Enum):
    SQFT = "sqft"
    KG = "kg"
    BAG = "bag"
    UNIT = "unit"
    TONNE = "tonne"
    CFT = "cft"


class CorrectionConfidence(str, enum.Enum):
    HIGH = "high"
    LOW = "low"
    FALLBACK = "fallback"


class ModelVersionStatus(str, enum.Enum):
    ACTIVE = "active"
    TRAINING = "training"
    RETIRED = "retired"


# Shared SQLAlchemy Enum type instances — a Postgres ENUM type used by more than one
# table (e.g. MaterialUnit in both `materials` and `rate_table`) must reuse the same
# Enum() instance across columns, otherwise create_all()/Alembic will try to CREATE
# TYPE twice and fail with "type already exists".
#
# values_callable is required: SQLAlchemy's default Enum stores the Python member
# NAME ("SQFT") in the DB, but the API contract and every enum's own .value use
# lowercase ("sqft") — without this, the DB storage and the JSON contract diverge.
def _values(enum_cls):
    return [member.value for member in enum_cls]


job_status_enum = SAEnum(JobStatus, name="job_status", values_callable=_values)
room_type_enum = SAEnum(RoomType, name="room_type", values_callable=_values)
room_source_enum = SAEnum(RoomSource, name="room_source", values_callable=_values)
material_unit_enum = SAEnum(MaterialUnit, name="material_unit", values_callable=_values)
correction_confidence_enum = SAEnum(
    CorrectionConfidence, name="correction_confidence", values_callable=_values
)
model_version_status_enum = SAEnum(
    ModelVersionStatus, name="model_version_status", values_callable=_values
)
