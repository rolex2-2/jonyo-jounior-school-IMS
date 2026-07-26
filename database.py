from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask-SQLAlchemy
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    grade = db.Column(db.String)
    admission_no = db.Column(db.String)
    phone_number = db.Column(db.String)

class Student(db.Model):
    __tablename__ = "students"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    admission_no = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    grade = db.Column(db.String, nullable=False)

class Fee(db.Model):
    __tablename__ = "fees"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    admission_no = db.Column(db.String, db.ForeignKey("students.admission_no"), nullable=False)
    total_fee = db.Column(db.Integer)
    amount_paid = db.Column(db.Integer)
    balance = db.Column(db.Integer)
    grade = db.Column(db.String)
    term = db.Column(db.String, nullable=False, default="Term 1")
    year = db.Column(db.Integer, nullable=False, default=2025)

class PaymentHistory(db.Model):
    __tablename__ = "payment_history"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    admission_no = db.Column(db.String, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String, nullable=False)
    term = db.Column(db.String, nullable=False)
    year = db.Column(db.String, nullable=False)

class Marks(db.Model):
    __tablename__ = "marks"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    admission_no = db.Column(db.String, db.ForeignKey("students.admission_no"), nullable=False)
    learning_area = db.Column(db.String, nullable=False)
    marks = db.Column(db.Integer, nullable=False)
    exam_type = db.Column(db.String, nullable=False)
    total_marks = db.Column(db.Integer)
    term = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('admission_no', 'learning_area', 'exam_type', 'term', 'year', 'grade', name='unique_marks'),
    )

class TeacherAssignments(db.Model):
    __tablename__ = "teacher_assignments"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    learning_area = db.Column(db.String, nullable=False)
    grade = db.Column(db.String, nullable=False)

class ClassTeachers(db.Model):
    __tablename__ = "class_teachers"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    grade = db.Column(db.String, nullable=False)

class LearningAreas(db.Model):
    __tablename__ = "learning_areas"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String, nullable=False)
    grade = db.Column(db.String, nullable=False)

class PerformanceLevels(db.Model):
    __tablename__ = "performance_levels"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    min_marks = db.Column(db.Integer, nullable=False)
    max_marks = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String, nullable=False)
    points = db.Column(db.Float, nullable=False)
    comment = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    __table_args__ = (
        db.CheckConstraint("type IN ('learning_area', 'class_teacher', 'principal')", name='check_type'),
    )

class TermInfo(db.Model):
    __tablename__ = "term_info"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    term = db.Column(db.String, nullable=False)
    year = db.Column(db.String, nullable=False)
    principal = db.Column(db.String, nullable=False)
    start_date = db.Column(db.String, nullable=False)
    end_date = db.Column(db.String, nullable=False)

class ParentStudent(db.Model):
    __tablename__ = "parent_student"
    
    parent_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    admission_no = db.Column(db.String, db.ForeignKey("students.admission_no"), primary_key=True)

class Mission(db.Model):
    __tablename__ = "mission"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)

class Vision(db.Model):
    __tablename__ = "vision"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)

class Messages(db.Model):
    __tablename__ = "messages"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    recipient_role = db.Column(db.String, nullable=False)

class Announcements(db.Model):
    __tablename__ = "announcements"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)

class AdminNotes(db.Model):
    __tablename__ = "admin_notes"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)
    created_by = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class About(db.Model):
    __tablename__ = "about"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)

class Contact(db.Model):
    __tablename__ = "contact"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    content = db.Column(db.String, nullable=False)

def init_db(app):
    # Initialize Flask-SQLAlchemy with the app
    db.init_app(app)
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

        try:
            # Disable autoflush to prevent premature commits
            with db.session.no_autoflush:
                # Verify schema for marks table
                try:
                    db.session.execute(text("SELECT year FROM marks LIMIT 1"))
                    logger.info("Verified marks table schema")
                except Exception as e:
                    logger.warning(f"Marks table schema check failed: {str(e)}. Ensure year is INTEGER.")

                # Insert default learning areas
                default_learning_areas = [
                    ('Mathematics', 'Grade 7'), ('English', 'Grade 7'), ('Kiswahili', 'Grade 7'),
                    ('Integrated Science', 'Grade 7'), ('Pre-technical', 'Grade 7'),
                    ('Agriculture and Nutrition', 'Grade 7'), ('Social Studies', 'Grade 7'),
                    ('Creative Arts', 'Grade 7'), ('CRE', 'Grade 7'),
                    ('Mathematics', 'Grade 8'), ('English', 'Grade 8'), ('Kiswahili', 'Grade 8'),
                    ('Integrated Science', 'Grade 8'), ('Pre-technical', 'Grade 8'),
                    ('Agriculture and Nutrition', 'Grade 8'), ('Social Studies', 'Grade 8'),
                    ('Creative Arts', 'Grade 8'), ('CRE', 'Grade 8'),
                    ('Mathematics', 'Grade 9'), ('English', 'Grade 9'), ('Kiswahili', 'Grade 9'),
                    ('Integrated Science', 'Grade 9'), ('Pre-technical', 'Grade 9'),
                    ('Agriculture and Nutrition', 'Grade 9'), ('Social Studies', 'Grade 9'),
                    ('Creative Arts', 'Grade 9'), ('CRE', 'Grade 9'),
                ]
                
                for name, grade in default_learning_areas:
                    if not db.session.query(LearningAreas).filter_by(name=name, grade=grade).first():
                        db.session.add(LearningAreas(name=name, grade=grade))
                db.session.commit()
                logger.info("Default learning areas inserted successfully")

                # Insert default performance levels
                default_performance_levels = [
                    (90, 100, 'EE1', 4.0, 'Exceeds Expectations', 'learning_area'),
                    (75, 89, 'EE2', 3.5, 'Exceeds Expectations', 'learning_area'),
                    (58, 74, 'ME1', 3.0, 'Meets Expectations', 'learning_area'),
                    (41, 57, 'ME2', 2.5, 'Meets Expectations', 'learning_area'),
                    (31, 40, 'AE1', 2.0, 'Approaches Expectations', 'learning_area'),
                    (21, 30, 'AE2', 1.5, 'Approaches Expectations', 'learning_area'),
                    (11, 20, 'BE1', 1.0, 'Below Expectations', 'learning_area'),
                    (0, 10, 'BE2', 0.5, 'Below Expectations', 'learning_area'),
                    (450, 500, 'EE1', 4.0, 'Outstanding Performance', 'class_teacher'),
                    (400, 449, 'EE2', 3.5, 'Excellent Performance', 'class_teacher'),
                    (350, 399, 'ME1', 3.0, 'Good Performance', 'class_teacher'),
                    (300, 349, 'ME2', 2.5, 'Satisfactory Performance', 'class_teacher'),
                    (250, 299, 'AE1', 2.0, 'Needs Improvement', 'class_teacher'),
                    (200, 249, 'AE2', 1.5, 'Significant Improvement Needed', 'class_teacher'),
                    (150, 199, 'BE1', 1.0, 'Poor Performance', 'class_teacher'),
                    (0, 149, 'BE2', 0.5, 'Very Poor Performance', 'class_teacher'),
                    (450, 500, 'EE1', 4.0, 'Excellent Work', 'principal'),
                    (400, 449, 'EE2', 3.5, 'Very Good Work', 'principal'),
                    (350, 399, 'ME1', 3.0, 'Good Work', 'principal'),
                    (300, 349, 'ME2', 2.5, 'Fair Work', 'principal'),
                    (250, 299, 'AE1', 2.0, 'Needs More Effort', 'principal'),
                    (200, 249, 'AE2', 1.5, 'More Effort Required', 'principal'),
                    (150, 199, 'BE1', 1.0, 'Unsatisfactory', 'principal'),
                    (0, 149, 'BE2', 0.5, 'Very Unsatisfactory', 'principal'),
                ]
                
                for min_marks, max_marks, level, points, comment, type_ in default_performance_levels:
                    if not db.session.query(PerformanceLevels).filter_by(min_marks=min_marks, max_marks=max_marks, type=type_).first():
                        db.session.add(PerformanceLevels(min_marks=min_marks, max_marks=max_marks, level=level, points=points, comment=comment, type=type_))
                db.session.commit()
                logger.info("Default performance levels inserted successfully")

                # Insert default term info
                if not db.session.query(TermInfo).first():
                    db.session.add(TermInfo(id=1, term='Term 1', year='2025', principal='Mr. Principal', start_date='2025-01-01', end_date='2025-04-01'))
                db.session.commit()
                logger.info("Default term info inserted successfully")

                # Insert default content for Mission, Vision, About
                if not db.session.query(Mission).first():
                    db.session.add(Mission(content="To provide quality education for all students"))
                if not db.session.query(Vision).first():
                    db.session.add(Vision(content="To be a leading institution in academic excellence"))
                if not db.session.query(About).first():
                    db.session.add(About(content="Jonyo Junior School is dedicated to fostering holistic education"))
                db.session.commit()
                logger.info("Default Mission, Vision, About inserted successfully")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in init_db: {str(e)}")
            raise

# Dependency to get DB session
def get_db():
    try:
        yield db.session
    finally:
        db.session.close()

# Export all models and functions
__all__ = [
    'User', 'Student', 'Fee', 'PaymentHistory', 'Marks', 'TeacherAssignments',
    'ClassTeachers', 'LearningAreas', 'PerformanceLevels', 'TermInfo',
    'ParentStudent', 'Mission', 'Vision', 'Messages', 'Announcements',
    'AdminNotes', 'About', 'Contact', 'get_db', 'init_db', 'db'
]