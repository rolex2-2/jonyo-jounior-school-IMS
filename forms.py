import logging
from datetime import datetime
from flask import g
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField,
                     TextAreaField, HiddenField, SubmitField, DateField, SelectMultipleField)
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, Optional, Regexp, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from database import get_db, User, ParentStudent, LearningAreas
from database import db
from flask_login import current_user
from database import User, Student





logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


GRADES = [('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')]
TERMS = [('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')]

EXAM_TYPES = [
    ('cat1', 'CAT 1'), ('cat2', 'CAT 2'), ('cat3', 'CAT 3'),
    ('rat1', 'RAT 1'), ('rat2', 'RAT 2'), ('rat3', 'RAT 3'),
    ('midterm', 'Mid Term'), ('endterm', 'End Term'),
    ('project1', 'Project 1'), ('project2', 'Project 2'), ('project3', 'Project 3')
]

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('parent', 'Parent')], validators=[DataRequired()])

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('teacher', 'Teacher'), ('student', 'Student'), ('parent', 'Parent'), ('bursar', 'Bursar')], validators=[DataRequired()])

class ResultsFilterForm(FlaskForm):
    admission_no = SelectField(
        'Admission Number',
        choices=[],
        validators=[DataRequired(message='Please select an admission number.')],
        description='Select the student’s admission number.'
    )
    grade = SelectField(
        'Grade',
        choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')],
        validators=[DataRequired(message='Please select a grade.')]
    )
    term = SelectField(
        'Term',
        choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')],
        validators=[DataRequired(message='Please select a term.')]
    )
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            NumberRange(min=2000, max=2100, message='Year must be between 2000 and 2100.')
        ]
    )
    exam_type = SelectField(
        'Exam Type',
        choices=[
            ('cat1', 'CAT 1'), ('cat2', 'CAT 2'), ('cat3', 'CAT 3'),
            ('rat1', 'RAT 1'), ('rat2', 'RAT 2'), ('rat3', 'RAT 3'),
            ('midterm', 'Mid Term'), ('endterm', 'End Term'),
            ('project1', 'Project 1'), ('project2', 'Project 2'), ('project3', 'Project 3')
        ],
        validators=[DataRequired(message='Please select an exam type.')]
    )
    submit = SubmitField('View Results')

    def __init__(self, admission_no=None, grade=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if admission_no:
            self.admission_no.data = admission_no
        if grade:
            self.grade.data = grade
        logger.debug(f"ResultsFilterForm initialized with admission_no={admission_no}, grade={grade}")
        
class TeacherRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    grade = SelectField('Grade', choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')], validators=[DataRequired()])

class StudentRegistrationForm(FlaskForm):
    admission_no = StringField('Admission Number', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    grade = SelectField('Grade', choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')], validators=[DataRequired()])

class BursarRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=50, message='Username must be between 3 and 50 characters.')
    ])

class MarksForm(FlaskForm):
    """Form for editing or adding student marks."""
    grade = SelectField(
        'Grade',
        choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')],
        validators=[DataRequired(message="Please select a grade.")]
    )
    learning_area = SelectField(
        'Learning Area',
        choices=[],
        validators=[DataRequired(message="Please select a learning area.")]
    )
    exam_type = SelectField(
        'Exam Type',
        choices=[
            ('cat1', 'CAT 1'), ('cat2', 'CAT 2'), ('cat3', 'CAT 3'),
            ('rat1', 'RAT 1'), ('rat2', 'RAT 2'), ('rat3', 'RAT 3'),
            ('midterm', 'Mid Term'), ('endterm', 'End Term'),
            ('project1', 'Project 1'), ('project2', 'Project 2'), ('project3', 'Project 3')
        ],
        validators=[DataRequired(message="Please select an exam type.")]
    )
    term = SelectField(
        'Term',
        choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')],
        validators=[DataRequired(message="Please select a term.")]
    )
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message="Please enter a year."),
            NumberRange(min=2000, max=2100, message="Year must be between 2000 and 2100.")
        ]
    )
    marks = FloatField(
        'Marks',
        validators=[
            Optional(),
            NumberRange(min=0, message="Marks cannot be negative.")
        ]
    )
    submit = SubmitField('Save Marks')

    def __init__(self, *args, **kwargs):
        """Initialize the form and populate learning_area choices."""
        super().__init__(*args, **kwargs)
        from app import db  # Import db here to avoid circular imports
        grade = self.grade.data or 'Grade 7'
        try:
            learning_areas = db.session.query(LearningAreas.name).filter(LearningAreas.grade == grade).all()
            if not learning_areas:
                logger.warning(f"No learning areas found for grade {grade}, using defaults")
                self.learning_area.choices = [
                    ('Mathematics', 'Mathematics'),
                    ('English', 'English'),
                    ('Science', 'Science'),
                    ('Social Studies', 'Social Studies'),
                    ('Kiswahili', 'Kiswahili')
                ]
            else:
                self.learning_area.choices = [(row[0], row[0]) for row in learning_areas]
                logger.debug(f"Loaded {len(self.learning_area.choices)} learning areas for grade {grade}")
        except SQLAlchemyError as e:
            logger.error(f"Error fetching learning areas for grade {grade}: {str(e)}")
            self.learning_area.choices = [
                ('Mathematics', 'Mathematics'),
                ('English', 'English'),
                ('Science', 'Science'),
                ('Social Studies', 'Social Studies'),
                ('Kiswahili', 'Kiswahili')
            ]

class MarksFilterForm(FlaskForm):
    """Form for filtering student marks by grade, term, year, and exam type."""
    grade = SelectField(
        'Grade',
        choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9')],
        validators=[DataRequired(message="Please select a grade.")]
    )
    term = SelectField(
        'Term',
        choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')],
        validators=[DataRequired(message="Please select a term.")]
    )
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message="Please enter a year."),
            NumberRange(min=2000, max=2100, message="Year must be between 2000 and 2100.")
        ]
    )
    exam_type = SelectField(
        'Exam Type',
        choices=[
            ('cat1', 'CAT 1'), ('cat2', 'CAT 2'), ('cat3', 'CAT 3'),
            ('rat1', 'RAT 1'), ('rat2', 'RAT 2'), ('rat3', 'RAT 3'),
            ('midterm', 'Mid Term'), ('endterm', 'End Term'),
            ('project1', 'Project 1'), ('project2', 'Project 2'), ('project3', 'Project 3')
        ],
        validators=[DataRequired(message="Please select an exam type.")]
    )
    submit = SubmitField('Filter Marks')

    def __init__(self, *args, **kwargs):
        """Initialize the form and set default choices."""
        super().__init__(*args, **kwargs)
        logger.debug("MarksFilterForm initialized with fields: grade, term, year, exam_type")
class AnnouncementsForm(FlaskForm):
    content = TextAreaField('Announcements Content', validators=[DataRequired()])
    submit = SubmitField('Add Announcements')


class LinkParentStudentForm(FlaskForm):
    parent_id = StringField(
        'Parent Username',
        validators=[DataRequired(message='Please enter a parent username.'), Length(min=1, max=80)],
        description='Enter the parent\'s username.'
    )
    admission_no = StringField(
        'Student Admission Number',
        validators=[DataRequired(message='Please enter a student admission number.'), Length(min=1, max=50)],
        description='Enter the student\'s admission number.'
    )
    submit = SubmitField('Link Student')

    def validate_parent_id(self, parent_id):
        db_session = next(get_db())
        try:
            parent = db_session.query(User).filter_by(username=parent_id.data, role='parent').first()
            if not parent:
                raise ValidationError('Parent username not found.')
        finally:
            db_session.close()

    def validate_admission_no(self, admission_no):
        db_session = next(get_db())
        try:
            student = db_session.query(Student).filter_by(admission_no=admission_no.data).first()
            if not student:
                raise ValidationError('Student admission number not found.')
        finally:
            db_session.close()
class ParentRegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    phone_number1 = StringField('Phone Number 1', validators=[DataRequired(), Regexp(r'^\+?\d{10,15}$', message='Invalid phone number format')])
    phone_number2 = StringField('Phone Number 2', validators=[Optional(), Regexp(r'^\+?\d{10,15}$', message='Invalid phone number format')])
    phone_number3 = StringField('Phone Number 3', validators=[Optional(), Regexp(r'^\+?\d{10,15}$', message='Invalid phone number format')])
    submit = SubmitField('Register')

class ReportCardForm(FlaskForm):
    grade = SelectField(
        'Grade',
        choices=GRADES[1:],  # Exclude 'all' for report card
        validators=[DataRequired(message='Please select a grade.')]
    )
    term = SelectField(
        'Term',
        choices=TERMS,
        validators=[DataRequired(message='Please select a term.')]
    )
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            NumberRange(min=2000, max=2100, message='Please enter a valid year (2000-2100).')
        ]
    )
    exam_type = SelectField(
        'Exam Type',
        choices=EXAM_TYPES,
        validators=[DataRequired(message='Please select an exam type.')]
    )
    admission_no = SelectField(
        'Admission Number',
        choices=[],  # Choices set dynamically in routes
        validators=[Optional()]
    )
    submit = SubmitField('Download')
class FeeForm(FlaskForm):
    learner_name = StringField(
        'Learner Name',
        validators=[DataRequired(message="Please enter a learner name.")],
        description="Enter the student's name for autocomplete search"
    )
    admission_no = HiddenField('Admission Number')  # Store admission_no as hidden field
    grade = SelectField(
        'Grade',
        choices=GRADES,
        validators=[DataRequired(message='Please select a grade.')],
        default='all'
    )
    term = SelectField(
        'Term',
        choices=TERMS,
        validators=[DataRequired(message='Please select a term.')],
        default='Term 1'
    )
    total_fee = FloatField(
        'Total Fee',
        validators=[
            DataRequired(message="Total fee is required."),
            NumberRange(min=0, message="Total fee cannot be negative.")
        ]
    )
    amount_paid = FloatField(
        'Amount Paid',
        validators=[
            DataRequired(message="Amount paid is required."),
            NumberRange(min=0, message="Amount paid cannot be negative.")
        ]
    )
    year = StringField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            Regexp(r'^\d{4}$', message="Year must be a 4-digit number (e.g., 2025).")
        ],
        default=str(datetime.now().year)
    )
    format = HiddenField('Format', default='pdf')
    submit = SubmitField('Update Fee')

    def __init__(self, role=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role
        if role == 'student':
            self.grade.validators = [Optional()]
            self.learner_name.validators = [Optional()]
            logger.debug("Grade and learner_name fields set to optional for student role")
        elif role == 'parent':
            self.grade.validators = [Optional()]
            self.learner_name.validators = [DataRequired(message="Please enter a learner name.")]
            logger.debug("Learner_name field set to required for parent role")
        elif role == 'bursar' or role == 'admin':
            self.learner_name.validators = [DataRequired(message="Please enter a learner name.")]
            self.total_fee.validators = [DataRequired(message="Total fee is required."), NumberRange(min=0)]
            self.amount_paid.validators = [DataRequired(message="Amount paid is required."), NumberRange(min=0)]
            logger.debug("Learner_name, total_fee, and amount_paid fields set to required for bursar/admin role")

    def validate_learner_name(self, field):
        """Validate that learner_name corresponds to a student and set admission_no."""
        if field.data:
            student = db.session.query(User).filter(
                User.username.ilike(f'%{field.data}%'),
                User.role == 'student'
            ).first()
            if not student:
                logger.error(f"No student found for learner_name: {field.data}")
                raise ValidationError('No student found with this name.')
            if self.role == 'parent':
                parent_student = db.session.query(ParentStudent).filter_by(
                    parent_id=current_app.current_user.id,
                    admission_no=student.admission_no
                ).first()
                if not parent_student:
                    logger.error(f"Student {student.admission_no} not linked to parent {current_app.current_user.id}")
                    raise ValidationError('This student is not linked to your account.')
            logger.debug(f"Validated student: {student.username}, admission_no: {student.admission_no}")
            self.admission_no.data = student.admission_no

    def validate_amount_paid(self, field):
        """Ensure amount_paid does not exceed total_fee."""
        if field.data is not None and self.total_fee.data is not None:
            if field.data > self.total_fee.data:
                logger.error(f"Amount paid {field.data} exceeds total fee {self.total_fee.data}")
                raise ValidationError('Amount paid cannot exceed total fee.')
class FeeFilterForm(FlaskForm):
    grade = SelectField(
        'Grade',
        choices=GRADES[1:],  # Exclude 'all' for filtering
        validators=[DataRequired(message='Please select a grade.')]
    )
    term = SelectField(
        'Term',
        choices=TERMS,
        validators=[DataRequired(message='Please select a term.')]
    )
    year = StringField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            Regexp(r'^\d{4}$', message="Year must be a 4-digit number (e.g., 2025).")
        ],
        default=str(datetime.now().year)
    )
    submit = SubmitField('Filter')

class NoteForm(FlaskForm):
    content = TextAreaField('Note Content', validators=[
        DataRequired(message="Note content is required."),
        Length(min=5, max=1000, message="Note must be between 5 and 1000 characters.")
    ])
    note_id = HiddenField()
    submit = SubmitField('Save Note')


class MessageForm(FlaskForm):
    content = TextAreaField('Message Content', validators=[DataRequired()])
    recipient_role = SelectField('Recipient Role', choices=[('student', 'Students'), ('teacher', 'Teachers'), ('parent', 'Parents'), ('bursar', 'Bursars')], validators=[DataRequired()])
    submit = SubmitField('Send Message')

class PerformanceLevelForm(FlaskForm):
    min_marks = IntegerField('Minimum Mark', validators=[DataRequired(), NumberRange(min=0, max=100)])
    max_marks = IntegerField('Maximum Mark', validators=[DataRequired(), NumberRange(min=0, max=100)])
    level = StringField('Level', validators=[DataRequired(), Length(min=1, max=50)])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=0, max=100)])
    comment = StringField('Comment', validators=[DataRequired(), Length(min=1, max=200)])
    type = SelectField('Type', choices=[
        ('learning_area', 'Learning Area'),
        ('class_teacher', 'Class Teacher'),
        ('principal', 'Principal')
    ], validators=[DataRequired()])

class TermInfoForm(FlaskForm):
    term = SelectField('Term', choices=[('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')], validators=[DataRequired()])
    year = StringField('Year', validators=[DataRequired()])
    principal = StringField('Principal', validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    submit = SubmitField('Update Term Info')



GRADES = [
    ('Grade 7', 'Grade 7'),
    ('Grade 8', 'Grade 8'),
    ('Grade 9', 'Grade 9')
]

TERMS = [
    ('Term 1', 'Term 1'),
    ('Term 2', 'Term 2'),
    ('Term 3', 'Term 3')
]

EXAM_TYPES = [
    ('cat1', 'CAT 1'),
    ('cat2', 'CAT 2'),
    ('cat3', 'CAT 3'),
    ('rat1', 'RAT 1'),
    ('rat2', 'RAT 2'),
    ('rat3', 'RAT 3'),
    ('midterm', 'Mid Term'),
    ('endterm', 'End Term'),
    ('project1', 'Project 1'),
    ('project2', 'Project 2'),
    ('project3', 'Project 3')
]

class ReportCardForm(FlaskForm):
    grade = SelectField(
        'Grade',
        choices=GRADES,
        validators=[DataRequired(message='Please select a grade.')]
    )
    term = SelectField(
        'Term',
        choices=TERMS,
        validators=[DataRequired(message='Please select a term.')]
    )
    year = IntegerField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            NumberRange(min=2000, max=2100, message='Please enter a valid year (2000-2100).')
        ]
    )
    exam_type = SelectField(
        'Exam Type',
        choices=EXAM_TYPES,
        validators=[DataRequired(message='Please select an exam type.')]
    )
    admission_no = SelectField(
        'Admission Number',
        choices=[],  # Choices will be set dynamically for parents
        validators=[Optional()]  # Optional to support admin/teacher route
    )
    submit = SubmitField('Download')
class BulkStudentUploadForm(FlaskForm):
    file = FileField('Excel File', validators=[
        FileRequired(message='Please upload a file.'),
        FileAllowed(['xlsx'], message='Only .xlsx files are allowed.')
    ])
    grade = SelectField('Grade', choices=[
        ('Grade 7', 'Grade 7'),
        ('Grade 8', 'Grade 8'),
        ('Grade 9', 'Grade 9')
    ], validators=[DataRequired(message='Please select a grade.')])
    
class AdmissionNoForm(FlaskForm):
    admission_no = StringField('Student Admission Number', validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField('View Student Dashboard')
    


class FeeStatementForm(FlaskForm):
    admission_no = SelectField(
        'Student',
        validators=[DataRequired(message='Please select a student.')],
        choices=[]  # Populated dynamically in routes
    )
    grade = SelectField(
        'Grade',
        validators=[DataRequired(message='Please select a grade.')],
        choices=GRADES
    )
    term = SelectField(
        'Term',
        validators=[DataRequired(message='Please select a term.')],
        choices=TERMS
    )
    year = StringField(
        'Year',
        validators=[
            DataRequired(message='Please enter a year.'),
            Regexp(r'^\d{4}$', message='Year must be a 4-digit number (e.g., 2025).')
        ],
        default=str(datetime.now().year)
    )
    submit = SubmitField('Download')

    def __init__(self, admission_no=None, grade=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if admission_no:
            self.admission_no.data = admission_no
        if grade:
            self.grade.data = grade