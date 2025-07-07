from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from app import db
from database import get_db, User, TeacherAssignments, ClassTeachers, PerformanceLevels, TermInfo
import logging

logger = logging.getLogger(__name__)

def get_performance_level(marks, type_):
    try:
        db_session = next(get_db(db))
        try:
            result = db_session.query(PerformanceLevels.level).filter(
                PerformanceLevels.min_marks <= marks,
                PerformanceLevels.max_marks >= marks,
                PerformanceLevels.type == type_
            ).first()
            return result[0] if result else 'N/A'
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error in get_performance_level: {str(e)}")
        return 'N/A'

def get_points(marks, type_):
    try:
        db_session = next(get_db(db))
        try:
            result = db_session.query(PerformanceLevels.points).filter(
                PerformanceLevels.min_marks <= marks,
                PerformanceLevels.max_marks >= marks,
                PerformanceLevels.type == type_
            ).first()
            return result[0] if result else 0.0
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error in get_points: {str(e)}")
        return 0.0

def get_teacher_name(learning_area, grade):
    try:
        db_session = next(get_db(db))
        try:
            result = db_session.query(User.username).join(TeacherAssignments).filter(
                TeacherAssignments.learning_area == learning_area,
                TeacherAssignments.grade == grade
            ).first()
            return result[0] if result else 'N/A'
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error in get_teacher_name: {str(e)}")
        return 'N/A'

def get_class_teacher_name(grade):
    try:
        db_session = next(get_db(db))
        try:
            result = db_session.query(User.username).join(ClassTeachers).filter(
                ClassTeachers.grade == grade
            ).first()
            return result[0] if result else 'N/A'
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error in get_class_teacher_name: {str(e)}")
        return 'N/A'

def get_principal_name():
    try:
        db_session = next(get_db(db))
        try:
            result = db_session.query(TermInfo.principal).filter(TermInfo.id == 1).first()
            return result[0] if result else 'N/A'
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error in get_principal_name: {str(e)}")
        return 'N/A'

def get_teacher_comment(level):
    return {'EE1': 'Excellent', 'ME2': 'Good'}.get(level, 'N/A')

def get_class_teacher_comment(total_marks, grade):
    return 'Great effort!' if total_marks > 0 else 'N/A'

def get_principal_comment(total_marks):
    return 'Well done!' if total_marks > 0 else 'N/A'

def generate_report_card(students, marks, fees, term, year, exam_type, rank, total_students, grade):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Report card content
        for student in students:
            admission_no = student.admission_no
            student_name = student.name
            student_grade = student.grade

            # Header
            elements.append(Paragraph(f"Report Card: {student_name} ({admission_no})", styles['Heading1']))
            elements.append(Paragraph(f"Grade: {student_grade}, Term: {term}, Year: {year}, Exam: {exam_type}", styles['Normal']))
            elements.append(Paragraph(f"Rank: {rank} out of {total_students}", styles['Normal']))

            # Marks Table
            marks_data = [['Learning Area', 'Marks', 'Out Of', 'Level', 'Points', 'Teacher']]
            total_marks = 0
            total_out_of = 0
            for mark in marks:
                if mark.admission_no == admission_no:
                    level = get_performance_level(mark.total_marks, 'learning_area')
                    points = get_points(mark.total_marks, 'learning_area')
                    teacher = get_teacher_name(mark.learning_area, grade)
                    marks_data.append([
                        mark.learning_area,
                        mark.total_marks,
                        mark.exam_out_of,
                        level,
                        points,
                        teacher
                    ])
                    total_marks += mark.total_marks
                    total_out_of += mark.exam_out_of
            marks_data.append(['Total', total_marks, total_out_of, '', '', ''])
            marks_table = Table(marks_data)
            marks_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(marks_table)

            # Fees Table
            fees_data = [['Total Fee', 'Amount Paid', 'Balance']]
            for fee in fees:
                if fee.admission_no == admission_no:
                    fees_data.append([fee.total_fee, fee.amount_paid, fee.balance])
            fees_table = Table(fees_data)
            fees_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(fees_table)

            # Comments
            elements.append(Paragraph(f"Class Teacher: {get_class_teacher_name(grade)}", styles['Normal']))
            elements.append(Paragraph(f"Comment: {get_class_teacher_comment(total_marks, grade)}", styles['Normal']))
            elements.append(Paragraph(f"Principal: {get_principal_name()}", styles['Normal']))
            elements.append(Paragraph(f"Comment: {get_principal_comment(total_marks)}", styles['Normal']))

        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error in generate_report_card: {str(e)}")
        return None