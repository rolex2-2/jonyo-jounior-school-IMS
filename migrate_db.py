from app import db
from database import get_db, Marks
import logging

logger = logging.getLogger(__name__)

def migrate_db(app, db):
    with app.app_context():
        try:
            # Check for marks table
            result = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='marks'")
            if not result.fetchone():
                logger.error("No marks table found. Run init_db from database.py to create it.")
                return False

            # Check existing schema
            result = db.engine.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='marks'")
            schema = result.fetchone()[0]
            if 'UNIQUE (admission_no, learning_area, exam_type, term, year, grade)' in schema:
                logger.info("Marks table already has correct UNIQUE constraint. No migration needed.")
                return True

            # Check for duplicates
            db_session = next(get_db(db))
            try:
                duplicates = db_session.query(
                    Marks.admission_no, Marks.learning_area, Marks.exam_type, Marks.term, Marks.year,
                    db.func.count()
                ).group_by(
                    Marks.admission_no, Marks.learning_area, Marks.exam_type, Marks.term, Marks.year
                ).having(db.func.count() > 1).all()
                if duplicates:
                    logger.warning(f"Found {len(duplicates)} duplicate records: {duplicates}")
                    logger.info("Removing duplicates by keeping the latest record...")
                    db.engine.execute("""
                        DELETE FROM marks 
                        WHERE id NOT IN (
                            SELECT MAX(id) 
                            FROM marks 
                            GROUP BY admission_no, learning_area, exam_type, term, year
                        )
                    """)
                    db.session.commit()
                    logger.info("Duplicates removed.")
            finally:
                db_session.close()

            # Rename old table
            db.engine.execute("ALTER TABLE marks RENAME TO marks_old")
            
            # Create new table with correct schema
            db.engine.execute("""
                CREATE TABLE marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admission_no TEXT NOT NULL,
                    learning_area TEXT NOT NULL,
                    marks INTEGER NOT NULL,
                    exam_type TEXT NOT NULL,
                    total_marks INTEGER,
                    exam_out_of INTEGER DEFAULT 100,
                    percentage TEXT DEFAULT 'none',
                    term TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    grade TEXT NOT NULL,
                    FOREIGN KEY (admission_no) REFERENCES students (admission_no),
                    UNIQUE (admission_no, learning_area, exam_type, term, year, grade)
                )
            """)

            # Copy data with type casting
            db.engine.execute("""
                INSERT INTO marks (id, admission_no, learning_area, marks, exam_type, total_marks, 
                                 exam_out_of, percentage, term, year, grade)
                SELECT id, admission_no, learning_area, 
                       CAST(marks AS INTEGER), 
                       exam_type, 
                       CAST(total_marks AS INTEGER), 
                       CAST(exam_out_of AS INTEGER), 
                       CAST(percentage AS TEXT), 
                       term, 
                       CAST(year AS INTEGER), 
                       grade 
                FROM marks_old
            """)

            # Drop old table
            db.engine.execute("DROP TABLE marks_old")
            db.session.commit()
            logger.info("Successfully migrated marks table to correct UNIQUE constraint and INTEGER types")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Migration failed: {str(e)}")
            return False