import io
import sqlite3
import logging
import traceback
from flask import flash, redirect, url_for, send_file, request
from flask_login import current_user, login_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_exam_type(exam_type):
    """Normalize exam_type by removing spaces, converting to lowercase, and stripping whitespace."""
    if not isinstance(exam_type, str):
        return ''
    return exam_type.replace(" ", "").lower().strip()


# ============================================================
# PERFORMANCE LEVEL HELPERS (DB-DRIVEN)
# ============================================================

def _get_matching_performance_level(marks, type_='learning_area'):
    """Return the matching row from performance_levels table."""
    try:
        if not isinstance(marks, (int, float)):
            return None
        marks = float(marks)
        if marks < 0:
            return None

        with sqlite3.connect('school.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT level, points, comment
                FROM performance_levels
                WHERE type = ?
                  AND min_marks <= ?
                  AND max_marks >= ?
                ORDER BY min_marks DESC
                LIMIT 1
            """, (type_, marks, marks))
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error looking up performance level: marks={marks}, type={type_}, error={str(e)}")
        return None


def get_performance_level(marks, type_='learning_area'):
    """Determine performance level based on marks and type (DB-driven)."""
    try:
        if not isinstance(marks, (int, float)) or marks < 0:
            return 'N/A'

        row = _get_matching_performance_level(marks, type_)
        if row and row['level']:
            return row['level'].strip()
        return 'N/A'
    except Exception as e:
        logger.error(f"Error in get_performance_level: {str(e)}")
        return 'N/A'


def get_points(marks, type_='learning_area'):
    """Calculate points based on marks (DB-driven)."""
    try:
        if not isinstance(marks, (int, float)) or marks < 0:
            return 0.0

        row = _get_matching_performance_level(marks, type_)
        if row and row['points'] is not None:
            return float(row['points'])
        return 0.0
    except Exception as e:
        logger.error(f"Error in get_points: {str(e)}")
        return 0.0


def get_teacher_comment(level):
    """Return comment for a given performance level name."""
    try:
        if not level or level == 'N/A':
            return 'No performance data available.'

        with sqlite3.connect('school.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT comment
                FROM performance_levels
                WHERE LOWER(level) = LOWER(?)
                LIMIT 1
            """, (level.strip(),))
            row = cursor.fetchone()
            if row and row['comment']:
                return row['comment'].strip()
        return 'No performance data available.'
    except Exception as e:
        logger.error(f"Error fetching teacher comment for level {level}: {str(e)}")
        return 'No performance data available.'


def get_class_teacher_comment(average_marks, grade):
    """Generate class teacher comment based on average marks."""
    try:
        if not isinstance(average_marks, (int, float)) or average_marks <= 0:
            return 'No performance data available.'
        level = get_performance_level(average_marks, 'class_teacher')
        return get_teacher_comment(level)
    except Exception as e:
        logger.error(f"Error in get_class_teacher_comment: {str(e)}")
        return 'No performance data available.'


def get_principal_comment(average_marks):
    """Generate principal comment based on average marks."""
    try:
        if not isinstance(average_marks, (int, float)) or average_marks <= 0:
            return 'No performance data available.'
        level = get_performance_level(average_marks, 'principal')
        return get_teacher_comment(level)
    except Exception as e:
        logger.error(f"Error in get_principal_comment: {str(e)}")
        return 'No performance data available.'


def get_teacher_name(learning_area, grade):
    """Fetch teacher name for a learning area and grade."""
    try:
        with sqlite3.connect('school.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.username
                FROM users u
                JOIN teacher_assignments ta ON u.id = ta.teacher_id
                WHERE LOWER(ta.learning_area) = LOWER(?)
                  AND LOWER(ta.grade) = LOWER(?)
                LIMIT 1
            """, (learning_area, grade))
            row = cursor.fetchone()
            return row[0].strip() if row and row[0] else 'Unknown Teacher'
    except Exception as e:
        logger.error(f"Error fetching teacher name: {str(e)}")
        return 'Unknown Teacher'


def get_class_teacher_name(grade):
    """Fetch class teacher name for a grade."""
    try:
        with sqlite3.connect('school.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.username
                FROM users u
                JOIN class_teachers ct ON u.id = ct.teacher_id
                WHERE LOWER(ct.grade) = LOWER(?)
                LIMIT 1
            """, (grade,))
            row = cursor.fetchone()
            return row[0].strip() if row and row[0] else 'Unknown Class Teacher'
    except Exception as e:
        logger.error(f"Error fetching class teacher name: {str(e)}")
        return 'Unknown Class Teacher'


def get_principal_name():
    """Fetch principal name from term_info."""
    try:
        with sqlite3.connect('school.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT principal FROM term_info WHERE id = 1")
            row = cursor.fetchone()
            return row[0].strip() if row and row[0] else 'School Principal'
    except Exception as e:
        logger.error(f"Error fetching principal name: {str(e)}")
        return 'School Principal'


def generate_report_card(students, marks, fees, term, year, exam_type, rank=None, total_students=None, grade=None):
    """Generate a PDF report card."""
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        processed_students = set()
        has_valid_content = False

        exam_type = normalize_exam_type(exam_type)
        term = str(term).strip() if term else ''
        year = str(year).strip() if year else ''
        grade = str(grade).strip() if grade else None

        logger.debug(
            f"generate_report_card called with: term={term}, year={year}, exam_type={exam_type}, "
            f"grade={grade}, rank={rank}, total_students={total_students}"
        )

        # Basic validation
        if not all([term, year, exam_type]):
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: Invalid term, year, or exam type.")
            c.drawString(50, 680, "Please contact the administrator.")
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        if not isinstance(students, (list, tuple)) or not students:
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: No student data provided.")
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        for student in students:
            try:
                # Extract student data
                if isinstance(student, (list, tuple)) and len(student) >= 6:
                    admission_no = str(student[5]).strip()
                    name = str(student[1]).strip()
                    student_grade = str(student[4]).strip()
                elif isinstance(student, dict):
                    admission_no = str(student.get('admission_no', '')).strip()
                    name = str(student.get('username', student.get('name', ''))).strip()
                    student_grade = str(student.get('grade', '')).strip()
                else:
                    logger.warning(f"Invalid student data format: {student}")
                    continue

                if not all([admission_no, name, student_grade]):
                    logger.warning(f"Incomplete student data: {admission_no}, {name}, {student_grade}")
                    continue

                if grade and student_grade.lower() != grade.lower():
                    logger.debug(f"Skipping grade mismatch: {admission_no}")
                    continue

                if admission_no in processed_students:
                    continue
                processed_students.add(admission_no)
                has_valid_content = True

                # Filter marks for this student + exam_type
                student_marks = []
                for m in marks:
                    try:
                        if isinstance(m, dict):
                            m_adm = str(m.get('admission_no', '')).strip()
                            m_exam = normalize_exam_type(m.get('exam_type', ''))
                            if m_adm == admission_no and m_exam == exam_type:
                                student_marks.append(m)
                        elif isinstance(m, (list, tuple)) and len(m) >= 7:
                            m_adm = str(m[0]).strip()
                            m_exam = normalize_exam_type(m[6] if len(m) > 6 else '')
                            if m_adm == admission_no and m_exam == exam_type:
                                student_marks.append(m)
                    except Exception:
                        continue

                # Header
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                c.setFont("Helvetica", 14)
                display_exam = (
                    exam_type.replace('cat1', 'CAT 1').replace('cat2', 'CAT 2').replace('cat3', 'CAT 3')
                    .replace('rat1', 'RAT 1').replace('rat2', 'RAT 2').replace('rat3', 'RAT 3')
                    .replace('midterm', 'Mid Term').replace('endterm', 'End Term')
                    .replace('project1', 'Project 1').replace('project2', 'Project 2').replace('project3', 'Project 3')
                )
                c.drawCentredString(300, 730, f"REPORT CARD - {term} {year} ({display_exam})")
                c.setFont("Helvetica", 12)
                c.drawString(50, 700, f"Name: {name}")
                c.drawString(50, 680, f"Admission No: {admission_no}")
                c.drawString(50, 660, f"Grade: {student_grade}")

                # Build table
                table_data = [['Learning Area', 'Marks', 'Perf. Level', 'Points', 'Teacher Comment', 'Teacher']]
                total_marks = 0.0
                total_points = 0.0
                valid_subjects = 0

                if not student_marks:
                    table_data.append(['N/A', 'N/A', 'N/A', 'N/A', 'No marks available', 'N/A'])
                else:
                    for mark in student_marks:
                        try:
                            if isinstance(mark, dict):
                                learning_area = str(mark.get('learning_area', '')).strip()[:20]
                                marks_value = float(mark.get('total_marks', 0) or 0)
                                exam_out_of = float(mark.get('exam_out_of', 100) or 100)
                            else:
                                learning_area = str(mark[1]).strip()[:20]
                                marks_value = float(mark[2] or 0)
                                exam_out_of = float(mark[3] or 100) if len(mark) > 3 else 100.0

                            if marks_value < 0:
                                continue

                            level = get_performance_level(marks_value, 'learning_area')
                            points = get_points(marks_value, 'learning_area')
                            comment = get_teacher_comment(level)[:25]
                            teacher = get_teacher_name(learning_area, student_grade)[:18]

                            marks_str = f"{marks_value:.0f}/{exam_out_of:.0f}"
                            table_data.append([learning_area, marks_str, level, f"{points:.2f}", comment, teacher])

                            total_marks += marks_value
                            total_points += points
                            valid_subjects += 1
                        except Exception as e:
                            logger.error(f"Error processing mark for {admission_no}: {str(e)}")
                            continue

                average_marks = total_marks / valid_subjects if valid_subjects > 0 else 0.0

                # Draw table
                col_widths = [1.6*inch, 0.8*inch, 0.9*inch, 0.7*inch, 1.5*inch, 1.3*inch]
                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                table.wrapOn(c, 500, 400)
                table_height = table._height
                table_x = 25
                table_y = 620 - table_height

                if table_y < 120:
                    # Simple multi-page handling
                    rows_per_page = 12
                    for i in range(0, len(table_data), rows_per_page):
                        sub_data = table_data[:1] + table_data[i+1:i+rows_per_page+1]
                        sub_table = Table(sub_data, colWidths=col_widths)
                        sub_table.setStyle(table._argW)  # reuse style if possible
                        sub_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                            ('FONTSIZE', (0, 1), (-1, -1), 8),
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        sub_table.wrapOn(c, 500, 400)
                        sub_table.drawOn(c, table_x, 620 - sub_table._height)
                        c.showPage()
                        # Redraw header on new page
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 14)
                        c.drawCentredString(300, 730, f"REPORT CARD - {term} {year} ({display_exam})")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Name: {name}")
                        c.drawString(50, 680, f"Admission No: {admission_no}")
                        c.drawString(50, 660, f"Grade: {student_grade}")
                    table = None
                else:
                    table.drawOn(c, table_x, table_y)

                # Footer
                y = max(table_y - 25, 120) if table else 580

                # Fees
                total_fee = 0.0
                balance = 0.0
                for f in fees:
                    try:
                        if isinstance(f, dict):
                            if str(f.get('admission_no', '')).strip() == admission_no:
                                total_fee = float(f.get('total_fee', 0) or 0)
                                balance = float(f.get('balance', 0) or 0)
                                break
                        elif isinstance(f, (list, tuple)) and len(f) >= 4:
                            if str(f[0]).strip() == admission_no:
                                total_fee = float(f[1] or 0)
                                balance = float(f[3] or 0)
                                break
                    except Exception:
                        continue

                performance_level = get_performance_level(average_marks, 'class_teacher') if valid_subjects > 0 else 'N/A'
                class_teacher_comment = get_class_teacher_comment(average_marks, student_grade) if valid_subjects > 0 else 'No performance data available'
                principal_comment = get_principal_comment(average_marks) if valid_subjects > 0 else 'No performance data available'

                c.setFont("Helvetica", 10)
                c.drawString(30, y - 15, f"Rank: {rank if rank else 'N/A'} out of {total_students if total_students else 'N/A'}")
                c.drawString(30, y - 35, f"Total Marks: {total_marks:.0f}" if total_marks > 0 else "Total Marks: N/A")
                c.drawString(30, y - 55, f"Total Points: {total_points:.2f}" if total_points > 0 else "Total Points: N/A")
                c.drawString(30, y - 75, f"Average Marks: {average_marks:.1f}" if valid_subjects > 0 else "Average Marks: N/A")
                c.drawString(30, y - 95, f"Performance Level: {performance_level}")
                c.drawString(30, y - 115, f"Total Fee: {total_fee:,.2f}")
                c.drawString(30, y - 135, f"Balance: {balance:,.2f}")
                c.drawString(30, y - 155, f"Class Teacher Comment: {class_teacher_comment[:55]}")
                c.drawString(30, y - 175, f"Principal Comment: {principal_comment[:55]}")
                c.drawString(30, y - 195, f"Class Teacher: {get_class_teacher_name(student_grade)[:25]}")
                c.drawString(30, y - 215, f"Principal: {get_principal_name()[:25]}")
                c.drawString(30, y - 235, "School Stamp: ____________________")

                # Watermark
                c.setFont("Helvetica", 50)
                c.setFillColor(colors.grey, alpha=0.15)
                c.saveState()
                c.translate(300, 400)
                c.rotate(45)
                c.drawCentredString(0, 0, "JONYO JSS")
                c.restoreState()
                c.setFillColor(colors.black)

                c.showPage()

            except Exception as e:
                logger.error(f"Error processing student {admission_no}: {str(e)}\n{traceback.format_exc()}")
                continue

        if not has_valid_content:
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "No valid student data or marks available.")
            c.drawString(50, 680, "Please contact your teacher or administrator.")
            c.showPage()

        c.save()
        buffer.seek(0)

        if not buffer.getvalue().startswith(b'%PDF-'):
            logger.error("Generated invalid PDF")
            return None

        logger.info(f"PDF report card generated successfully, size={len(buffer.getvalue())} bytes")
        return buffer

    except Exception as e:
        logger.error(f"Critical error in generate_report_card: {str(e)}\n{traceback.format_exc()}")
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
        c.setFont("Helvetica", 12)
        c.drawString(50, 700, "An unexpected error occurred while generating the report card.")
        c.drawString(50, 680, "Please contact the administrator.")
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer


@app.route('/student/download_report_card', methods=['GET', 'POST'])
@login_required
def student_download_report_card():
    try:
        if current_user.role != 'student':
            logger.warning(f"Unauthorized access attempt by user {current_user.id}")
            flash('Access denied: Only students can download their report cards.', 'error')
            return redirect(url_for('main.index'))

        admission_no = current_user.admission_no
        logger.debug(f"Student {admission_no} requesting report card")

        # Get parameters
        if request.method == 'POST':
            term = request.form.get('term', '').strip()
            year = request.form.get('year', '').strip()
            exam_type = normalize_exam_type(request.form.get('exam_type', ''))
        else:
            with sqlite3.connect('school.db') as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT term, year, exam_type
                    FROM marks
                    WHERE admission_no = ?
                    ORDER BY year DESC, term DESC
                    LIMIT 1
                """, (admission_no,))
                result = c.fetchone()
                if result:
                    term, year, exam_type = result
                    exam_type = normalize_exam_type(exam_type)
                else:
                    c.execute("SELECT term, year FROM term_info WHERE id = 1")
                    result = c.fetchone()
                    term = result[0] if result else 'Term 1'
                    year = result[1] if result else '2025'
                    exam_type = 'endterm'

        if not all([term, year, exam_type]):
            flash('Please provide valid term, year, and exam type.', 'error')
            return redirect(url_for('main.index'))

        with sqlite3.connect('school.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Student details
            c.execute("""
                SELECT admission_no, username, grade
                FROM users
                WHERE admission_no = ? AND role = 'student'
            """, (admission_no,))
            student = c.fetchone()
            if not student:
                flash('Student not found.', 'error')
                return redirect(url_for('main.index'))

            # Marks
            c.execute("""
                SELECT admission_no, learning_area, total_marks, exam_out_of,
                       term, year, exam_type, grade
                FROM marks
                WHERE admission_no = ?
                  AND LOWER(term) = LOWER(?)
                  AND year = ?
                  AND LOWER(REPLACE(exam_type, ' ', '')) = ?
            """, (admission_no, term, year, exam_type))
            marks = c.fetchall()

            if not marks:
                flash(
                    f'No marks found for {term} {year} '
                    f'({exam_type.replace("endterm", "End Term").replace("midterm", "Mid Term")}). '
                    f'Please contact your teacher.',
                    'error'
                )
                return redirect(url_for('main.index'))

            # Fees
            c.execute("""
                SELECT admission_no, total_fee, amount_paid, balance, grade, term, year
                FROM fees
                WHERE admission_no = ?
                  AND LOWER(term) = LOWER(?)
                  AND year = ?
            """, (admission_no, term, year))
            fees = c.fetchall()

            # Rank calculation
            c.execute("""
                SELECT admission_no, SUM(total_marks) as total
                FROM marks
                WHERE LOWER(grade) = LOWER(?)
                  AND LOWER(term) = LOWER(?)
                  AND year = ?
                  AND LOWER(REPLACE(exam_type, ' ', '')) = ?
                GROUP BY admission_no
                ORDER BY total DESC
            """, (student['grade'], term, year, exam_type))
            rank_list = [r['admission_no'] for r in c.fetchall()]
            rank = rank_list.index(admission_no) + 1 if admission_no in rank_list else 'N/A'
            total_students = len(rank_list)

        # Prepare data
        student_data = [(None, student['username'], None, None, student['grade'], student['admission_no'])]

        pdf_buffer = generate_report_card(
            students=student_data,
            marks=marks,
            fees=fees or [(admission_no, 0, 0, 0, student['grade'], term, year)],
            term=term,
            year=year,
            exam_type=exam_type,
            rank=rank,
            total_students=total_students,
            grade=student['grade']
        )

        if not pdf_buffer or len(pdf_buffer.getvalue()) == 0:
            flash('Error generating report card. Please contact the administrator.', 'error')
            return redirect(url_for('main.index'))

        pdf_buffer.seek(0)
        filename = f"Report_Card_{admission_no}_{student['grade'].replace(' ', '_')}_{term}_{year}_{exam_type}.pdf"

        logger.info(f"Report card downloaded by {admission_no}, size={len(pdf_buffer.getvalue())} bytes")
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error in student_download_report_card: {str(e)}\n{traceback.format_exc()}")
        flash('An unexpected error occurred. Please contact the administrator.', 'error')
        return redirect(url_for('main.index'))