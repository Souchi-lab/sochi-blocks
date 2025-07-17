import argparse
import json
import os
import uuid
from sqlalchemy import create_engine, Column, String, Text, ForeignKey, TIMESTAMP, Integer, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB, CHAR
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError

# Base for declarative models
Base = declarative_base()

# --- Model Definitions ---
# NOTE: These definitions must be kept in sync with the main models.

class MasterPiece(Base):
    __tablename__ = "master_piece"
    id = Column(String(1), primary_key=True)
    name = Column(String(32), nullable=False)
    shape_json = Column(JSONB, nullable=False)

class MasterBasePuzzle(Base):
    __tablename__ = "master_base_puzzle"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text)
    puzzle_type_id = Column(UUID(as_uuid=True), ForeignKey("master_puzzle_type.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("master_user.id"), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

class MasterBasePuzzleCell(Base):
    __tablename__ = "master_base_puzzle_cell"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_puzzle_id = Column(UUID(as_uuid=True), ForeignKey("master_base_puzzle.id", ondelete="CASCADE"), nullable=False)
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    z = Column(Integer, nullable=False)
    value = Column(CHAR(1), ForeignKey("master_piece.id"), nullable=False)

class MasterDifficulty(Base):
    __tablename__ = "master_difficulty"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)

class MasterPuzzleType(Base):
    __tablename__ = "master_puzzle_type"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255), nullable=True)

class MasterUser(Base):
    __tablename__ = "master_user"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(128), nullable=False, unique=True)
    password_hash = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

# --- Helper Functions ---
def get_or_create(session, model, defaults=None, **kwargs):
    """
    Gets an object or creates it if it does not exist.
    """
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = {**kwargs, **(defaults or {})}
        instance = model(**params)
        session.add(instance)
        try:
            session.flush()
            return instance, True
        except IntegrityError:
            session.rollback()
            instance = session.query(model).filter_by(**kwargs).first()
            return instance, False

# --- Piece Definitions ---
PIECE_DEFINITIONS = {
    'F': {'name': 'F', 'shape_json': [[1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [1, 2, 0]]},
    'I': {'name': 'I', 'shape_json': [[0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 3, 0], [0, 4, 0]]},
    'L': {'name': 'L', 'shape_json': [[0, 0, 0], [0, 1, 0], [0, 2, 0], [0, 3, 0], [1, 3, 0]]},
    'P': {'name': 'P', 'shape_json': [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [0, 2, 0]]},
    'N': {'name': 'N', 'shape_json': [[1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [0, 2, 0]]},
    'T': {'name': 'T', 'shape_json': [[0, 0, 0], [1, 0, 0], [2, 0, 0], [1, 1, 0], [1, 2, 0]]},
    'U': {'name': 'U', 'shape_json': [[0, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0], [2, 1, 0]]},
    'V': {'name': 'V', 'shape_json': [[0, 0, 0], [0, 1, 0], [0, 2, 0], [1, 2, 0], [2, 2, 0]]},
    'W': {'name': 'W', 'shape_json': [[0, 0, 0], [1, 0, 0], [1, 1, 0], [2, 1, 0], [2, 2, 0]]},
    'X': {'name': 'X', 'shape_json': [[1, 0, 0], [0, 1, 0], [1, 1, 0], [2, 1, 0], [1, 2, 0]]},
    'Y': {'name': 'Y', 'shape_json': [[1, 0, 0], [0, 1, 0], [1, 1, 0], [1, 2, 0], [1, 3, 0]]},
    'Z': {'name': 'Z', 'shape_json': [[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 2, 0], [2, 2, 0]]},
}

# --- Main Import Logic ---
def import_solutions(json_dir, size_filter):
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable not set.")

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # --- Prepare Master Data ---
    try:
        print("INFO: Preparing master data...")
        
        # 1. Pieces
        for piece_id, piece_data in PIECE_DEFINITIONS.items():
            get_or_create(session, MasterPiece, id=piece_id, defaults=piece_data)

        # 2. Other Master Data
        dummy_author, _ = get_or_create(session, MasterUser,
            username="dummy_author",
            defaults={'email': 'author@example.com', 'password_hash': '...'})
        
        dummy_puzzle_type, _ = get_or_create(session, MasterPuzzleType,
            name="Pentomino",
            defaults={'description': 'A pentomino puzzle.'})

        dummy_difficulty, _ = get_or_create(session, MasterDifficulty,
            name="Standard",
            defaults={'description': 'Standard difficulty.'})

        session.commit()
        print("INFO: Master data prepared successfully.")
    except Exception as e:
        session.rollback()
        print(f"FATAL: Could not prepare master data. Error: {e}")
        return

    imported_puzzles = 0
    imported_cells = 0

    for filename in os.listdir(json_dir):
        if not (filename.startswith("solutions_") and filename.endswith(".json")):
            continue

        file_size = filename.replace("solutions_", "").replace(".json", "")
        if size_filter != "all" and file_size != size_filter:
            continue

        filepath = os.path.join(json_dir, filename)
        print(f"INFO: Processing file: {filepath}")
        with open(filepath, 'r') as f:
            try:
                solutions_data = json.load(f)
            except json.JSONDecodeError:
                print(f"WARN: Could not decode JSON from {filename}. Skipping.")
                continue

        for index, solution_pieces in enumerate(solutions_data):
            slug = f"{file_size}_{index:04d}"

            try:
                # Create MasterBasePuzzle entry
                master_base_puzzle, created = get_or_create(session, MasterBasePuzzle,
                    name=slug,
                    defaults={
                        'description': f"Base puzzle for {slug}",
                        'puzzle_type_id': dummy_puzzle_type.id,
                        'author_id': dummy_author.id
                    })
                
                if not created:
                    print(f"INFO: Skipping existing master_base_puzzle: {slug}")
                    continue

                # Create MasterBasePuzzleCell entries
                cells_to_add = []
                for piece_data in solution_pieces:
                    piece_id = piece_data["piece"]
                    for cell_coords in piece_data["cells"]:
                        cells_to_add.append(MasterBasePuzzleCell(
                            base_puzzle_id=master_base_puzzle.id,
                            x=cell_coords[0],
                            y=cell_coords[1],
                            z=cell_coords[2] if len(cell_coords) > 2 else 0,
                            value=piece_id  # Use 'value' for piece_id
                        ))
                
                if cells_to_add:
                    session.bulk_save_objects(cells_to_add)

                session.commit()
                print(f"SUCCESS: Imported master_base_puzzle {slug}")
                imported_puzzles += 1
                imported_cells += len(cells_to_add)

            except Exception as e:
                print(f"ERROR: Failed to import master_base_puzzle {slug}. Error: {e}")
                session.rollback()

    session.close()
    print(f"--- Import Summary ---Total puzzles imported: {imported_puzzles}Total cells imported: {imported_cells}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import solution data into the database.")
    parser.add_argument("--json-dir", required=True, help="Directory containing solutions_*.json files.")
    parser.add_argument("--size", default="all", help="Filter by puzzle size (e.g., 6x10) or 'all'.")
    args = parser.parse_args()

    import_solutions(args.json_dir, args.size)
