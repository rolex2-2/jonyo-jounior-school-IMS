import io
import sqlite3
import logging
from flask import flash, redirect, url_for, send_file, request, Blueprint
from flask_login import current_user, login_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import inch
import traceback
from flask import Flask
# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define blueprint
app = Flask(__name__)

# Placeholder functions (replace with actual implementations)
def get_performance_level(marks, context): return "N/A"
def get_points(marks, context): return 0
def get_teacher_comment(level): return "N/A"
def get_teacher_name(learning_area, grade): return "N/A"
def get_class_teacher_comment(marks, grade): return "N/A"
def get_class_teacher_name(grade): return "N/A"
def get_principal_comment(marks): return "N/A"
def get_principal_name(): return "N/A"

def normalize_exam_type(exam_type):
    """Normalize exam_type by removing spaces, converting to lowercase, and stripping whitespace."""
    if not isinstance(exam_type, str):
        return ''
    return exam_type.replace(" ", "").lower().strip()

def generate_report_card(students, marks, fees, term, year, exam_type, rank=None, total_students=None, grade=None):
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        processed_students = set()
        has_valid_content = False

        # Normalize exam_type
        exam_type = normalize_exam_type(exam_type)

        # Log all input parameters
        logger.debug(f"generate_report_card called with: term={term}, year={year}, exam_type={exam_type}, grade={grade}, "
                     f"rank={rank}, total_students={total_students}, students={students}, "
                     f"marks_count={len(marks) if isinstance(marks, (list, tuple)) else 'N/A'}, "
                     f"fees_count={len(fees) if isinstance(fees, (list, tuple)) else 'N/A'}")

        # Input validation
        if not all(isinstance(x, str) for x in [term, year, exam_type] if x is not None):
            logger.error(f"Invalid string inputs: term={type(term)}, year={type(year)}, exam_type={type(exam_type)}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: Invalid term, year, or exam type.")
            c.drawString(50, 680, "Please contact the administrator.")
            has_valid_content = True
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        if not isinstance(students, (list, tuple)) or not students:
            logger.error(f"Invalid or empty students input: type={type(students)}, len={len(students) if isinstance(students, (list, tuple)) else 'N/A'}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: No student data provided.")
            c.drawString(50, 680, "Please ensure the student ID is valid and try again.")
            has_valid_content = True
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        if not isinstance(marks, (list, tuple)):
            logger.error(f"Invalid marks input: type={type(marks)}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: Invalid marks data format.")
            c.drawString(50, 680, "Please contact the administrator.")
            has_valid_content = True
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        if not isinstance(fees, (list, tuple)):
            logger.error(f"Invalid fees input: type={type(fees)}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: Invalid fees data format.")
            c.drawString(50, 680, "Please contact the administrator.")
            has_valid_content = True
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        with sqlite3.connect('school.db') as conn:
            db_cursor = conn.cursor()
            for student in students:
                try:
                    logger.debug(f"Processing student entry: {student}")
                    # Extract student data
                    if isinstance(student, (list, tuple)) and len(student) >= 6:
                        admission_no = str(student[5]).strip()
                        name = str(student[1]).strip()
                        student_grade = str(student[4]).strip()
                    elif isinstance(student, dict):
                        admission_no = str(student.get('admission_no', '')).strip()
                        name = str(student.get('username', '')).strip()
                        student_grade = str(student.get('grade', '')).strip()
                    else:
                        logger.warning(f"Invalid student data format: {student}")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Error: Invalid student data format.")
                        c.drawString(50, 680, "Please ensure correct student data is provided.")
                        has_valid_content = True
                        c.showPage()
                        continue

                    if not all([admission_no, student_grade, name]):
                        logger.warning(f"Empty or invalid student data: admission_no={admission_no}, name={name}, grade={student_grade}")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Error: Invalid student data for admission number {admission_no or 'unknown'}.")
                        c.drawString(50, 680, "Please verify the student ID, name, and grade.")
                        has_valid_content = True
                        c.showPage()
                        continue

                    # Verify student exists in database
                    try:
                        db_cursor.execute("SELECT username, grade FROM users WHERE admission_no = ? AND role = 'student'",
                                         (admission_no,))
                        db_student = db_cursor.fetchone()
                    except sqlite3.Error as e:
                        logger.error(f"Database error fetching student {admission_no}: {str(e)}")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Error: Database error for student {admission_no}.")
                        c.drawString(50, 680, "Please contact the administrator.")
                        has_valid_content = True
                        c.showPage()
                        continue

                    if not db_student:
                        logger.warning(f"Student {admission_no} not found in users table")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Error: Student {admission_no} not found in database.")
                        c.drawString(50, 680, "Please verify the student ID.")
                        has_valid_content = True
                        c.showPage()
                        continue
                    db_name, db_grade = db_student
                    name = db_name if db_name else name or "Unknown"
                    student_grade = db_grade if db_grade else student_grade

                    # Check grade mismatch
                    if grade and student_grade.lower() != grade.lower():
                        logger.warning(f"Grade mismatch for {admission_no}: expected {grade}, got {student_grade}")
                        c.setFont("Helvetica-Bold", 16)
                        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 700, f"Error: Grade mismatch for {admission_no}.")
                        c.drawString(50, 680, f"Expected {grade}, found {student_grade}.")
                        has_valid_content = True
                        c.showPage()
                        continue

                    if admission_no in processed_students:
                        logger.debug(f"Skipping duplicate admission_no: {admission_no}")
                        continue

                    # Filter marks with normalized exam_type
                    student_marks = [
                        m for m in marks
                        if (isinstance(m, dict) and str(m.get('admission_no', '')).strip() == admission_no and
                            normalize_exam_type(m.get('exam_type', '')) == exam_type) or
                           (isinstance(m, (list, tuple)) and len(m) >= 8 and str(m[0]).strip() == admission_no and
                            normalize_exam_type(m[6]) == exam_type)
                    ]
                    logger.debug(f"Student {admission_no} marks count: {len(student_marks)} | term={term}, year={year}, exam_type={exam_type}")

                    processed_students.add(admission_no)
                    has_valid_content = True

                    # Header
                    c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                    c.setFont("Helvetica", 14)
                    display_exam_type = exam_type.replace('cat1', 'CAT 1').replace('cat2', 'CAT 2').replace('cat3', 'CAT 3') \
                        .replace('rat1', 'RAT 1').replace('rat2', 'RAT 2').replace('rat3', 'RAT 3') \
                        .replace('midterm', 'Mid Term').replace('endterm', 'End Term') \
                        .replace('project1', 'Project 1').replace('project2', 'Project 2').replace('project3', 'Project 3')
                    c.drawCentredString(300, 730, f"REPORT CARD - {term} {year} ({display_exam_type})")
                    c.setFont("Helvetica", 12)
                    c.drawString(50, 700, f"Name: {name}")
                    c.drawString(50, 680, f"Admission No: {admission_no}")
                    c.drawString(50, 660, f"Grade: {student_grade}")

                    # Create table data
                    table_data = [
                        ['Learning Area', 'Marks', 'Perf. Level', 'Points', 'Teacher Comment', 'Teacher']
                    ]
                    total_marks = 0
                    total_points = 0
                    if not student_marks:
                        logger.warning(f"No marks found for {admission_no} in {grade}, {term}, {year}, {exam_type}")
                        c.setFont("Helvetica", 12)
                        c.drawString(50, 600, f"No marks found for {admission_no} in {grade}, {term} {year} ({display_exam_type})")
                        c.drawString(50, 580, "Please contact your teacher or administrator.")
                        table_data.append(['N/A', 'N/A', 'N/A', 'N/A', 'No marks available', 'N/A'])
                        has_valid_content = True
                    else:
                        for mark in student_marks:
                            try:
                                if isinstance(mark, dict):
                                    learning_area = str(mark.get('learning_area', '')).strip()[:15]
                                    marks_value = float(mark.get('total_marks', 0) or 0)
                                    exam_out_of = float(mark.get('exam_out_of', 100) or 100)
                                elif isinstance(mark, (list, tuple)) and len(mark) >= 8:
                                    learning_area = str(mark[1]).strip()[:15]
                                    marks_value = float(mark[2] or 0)
                                    exam_out_of = float(mark[3] or 100)
                                else:
                                    logger.warning(f"Invalid mark data for {admission_no}: {mark}")
                                    continue

                                marks_str = f"{marks_value:.2f}/{exam_out_of:.0f}"
                                level = get_performance_level(marks_value, 'learning_area')
                                points = get_points(marks_value, 'learning_area')
                                comment = get_teacher_comment(level)[:20]
                                teacher = get_teacher_name(learning_area, student_grade)[:15]
                                table_data.append([learning_area, marks_str, level, f"{points:.2f}", comment, teacher])
                                total_marks += marks_value
                                total_points += float(points)
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error processing mark for {admission_no}, mark={mark}: {str(e)}")
                                continue

                    # Create table
                    col_widths = [1.5*inch, 0.8*inch, 0.8*inch, 0.7*inch, 1.5*inch, 1.2*inch]
                    table = Table(table_data, colWidths=col_widths)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('LEFTPADDING', (0, 0), (-1, -1), 4),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ]))
                    table.wrapOn(c, 500, 400)
                    table_height = table._height
                    table_x = 30
                    table_y = 620 - table_height
                    if table_y < 100:
                        logger.warning(f"Table y-position {table_y} too low for {admission_no}, splitting table")
                        rows_per_page = 10
                        for i in range(0, len(table_data), rows_per_page):
                            sub_table = Table(table_data[:1] + table_data[i+1:i+rows_per_page+1], colWidths=col_widths)
                            sub_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 10),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 1), (-1, -1), 9),
                                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ]))
                            sub_table.wrapOn(c, 500, 400)
                            sub_table.drawOn(c, table_x, 620 - sub_table._height)
                            c.showPage()
                            c.setFont("Helvetica-Bold", 16)
                            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                            c.setFont("Helvetica", 14)
                            c.drawCentredString(300, 730, f"REPORT CARD - {term} {year} ({display_exam_type})")
                            c.setFont("Helvetica", 12)
                            c.drawString(50, 700, f"Name: {name}")
                            c.drawString(50, 680, f"Admission No: {admission_no}")
                            c.drawString(50, 660, f"Grade: {student_grade}")
                        table = None
                    else:
                        table.drawOn(c, table_x, table_y)

                    # Footer details
                    y = 580 if not student_marks else max(table_y - 20, 100)
                    student_fees = [
                        f for f in fees
                        if (isinstance(f, dict) and str(f.get('admission_no', '')).strip() == admission_no) or
                           (isinstance(f, (list, tuple)) and len(f) >= 7 and str(f[0]).strip() == admission_no)
                    ]
                    fee_info = student_fees[0] if student_fees else {'admission_no': admission_no, 'total_fee': 0, 'amount_paid': 0, 'balance': 0}

                    if isinstance(fee_info, dict):
                        total_fee = float(fee_info.get('total_fee', 0) or 0)
                        balance = float(fee_info.get('balance', 0) or 0)
                    else:
                        total_fee = float(fee_info[1] or 0)
                        balance = float(fee_info[3] or 0)

                    c.drawString(30, y-20, f"Rank: {rank if rank else 'N/A'} out of {total_students if total_students else 'N/A'}")
                    c.drawString(30, y-40, f"Total Marks: {total_marks:.2f}" if total_marks > 0 else "Total Marks: N/A")
                    c.drawString(30, y-60, f"Total Points: {total_points:.2f}" if total_points > 0 else "Total Points: N/A")
                    c.drawString(30, y-80, f"Performance Level: {get_performance_level(total_marks, 'class_teacher') if total_marks > 0 else 'N/A'}")
                    c.drawString(30, y-100, f"Total Fee: {total_fee:,.2f}")
                    c.drawString(30, y-120, f"Balance: {balance:,.2f}")
                    c.drawString(30, y-140, f"Class Teacher Comment: {get_class_teacher_comment(total_marks, student_grade)[:50] if total_marks > 0 else 'N/A'}")
                    c.drawString(30, y-160, f"Principal Comment: {get_principal_comment(total_marks)[:50] if total_marks > 0 else 'N/A'}")
                    c.drawString(30, y-180, f"Class Teacher: {get_class_teacher_name(student_grade)[:20]}")
                    c.drawString(30, y-200, f"Principal: {get_principal_name()[:20]}")
                    c.drawString(30, y-220, "School Stamp: ____________________")

                    # Watermark
                    c.setFont("Helvetica", 50)
                    c.setFillColor(colors.grey, alpha=0.2)
                    c.rotate(45)
                    c.drawCentredString(400, 200, "JONYO JSS")
                    c.rotate(-45)
                    c.setFillColor(colors.black)
                    c.showPage()

                except Exception as e:
                    logger.error(f"Error processing student {admission_no}: {str(e)}\n{traceback.format_exc()}")
                    c.setFont("Helvetica-Bold", 16)
                    c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
                    c.setFont("Helvetica", 12)
                    c.drawString(50, 700, f"Error processing student {admission_no}: {str(e)}")
                    c.drawString(50, 680, "Please contact the administrator.")
                    has_valid_content = True
                    c.showPage()
                    continue

        if not has_valid_content:
            logger.warning(f"No valid report cards generated for {grade or 'unknown grade'}, {term}, {year}, {exam_type}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, f"No valid student data available for {grade or 'unknown grade'}, {term} {year} ({exam_type}).")
            c.drawString(50, 680, "Please check if the student exists and has marks for the specified term and exam type.")
            c.drawString(50, 660, "Contact the administrator for assistance.")
            has_valid_content = True
            c.showPage()

        c.save()
        buffer.seek(0)
        pdf_content = buffer.getvalue()
        if not pdf_content.startswith(b'%PDF-'):
            logger.error(f"Invalid PDF generated for {grade or 'unknown grade'}, starts with: {pdf_content[:10]}")
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
            c.setFont("Helvetica", 12)
            c.drawString(50, 700, "Error: Invalid PDF generated.")
            c.drawString(50, 680, "Please contact the administrator.")
            has_valid_content = True
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer
        logger.info(f"PDF report generated for {grade or 'unknown grade'}, size={len(pdf_content)} bytes")
        return buffer

    except Exception as e:
        logger.error(f"Error in generate_report_card: {str(e)}\n{traceback.format_exc()}")
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(300, 750, "JONYO JUNIOR SECONDARY SCHOOL")
        c.setFont("Helvetica", 12)
        c.drawString(50, 700, f"Error generating report card: {str(e)}")
        c.drawString(50, 680, "Please contact the administrator.")
        c.showPage()
        c.save()
        buffer.seek(0)
        return buffer

@app.route('/student/download_report_card', methods=['GET', 'POST'])
@login_required
def student_download_report_card():
    try:
        # Ensure user is a student
        if current_user.role != 'student':
            logger.warning(f"Unauthorized access to student report card by user {current_user.id}, role={current_user.role}")
            flash('Access denied: Only students can download their report cards.', 'error')
            return redirect(url_for('main.index'))

        admission_no = current_user.admission_no
        logger.debug(f"Student {admission_no} requesting report card download")

        # Get form data or default to latest term
        if request.method == 'POST':
            term = request.form.get('term', '').strip()
            year = request.form.get('year', '').strip()
            exam_type = normalize_exam_type(request.form.get('exam_type', ''))
        else:
            # Fetch latest term, year, exam_type from marks table for this student
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
                    # Fallback to term_info
                    c.execute("SELECT term, year FROM term_info WHERE id = 1")
                    result = c.fetchone()
                    term = result[0] if result else 'Term 1'
                    year = result[1] if result else '2025'
                    exam_type = 'endterm'

        if not all([term, year, exam_type]):
            logger.error(f"Invalid input: term={term}, year={year}, exam_type={exam_type}")
            flash('Please provide valid term, year, and exam type.', 'error')
            return redirect(url_for('main.index'))

        # Fetch student details
        with sqlite3.connect('school.db') as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT admission_no, username, grade FROM users WHERE admission_no = ? AND role = 'student'", (admission_no,))
            student = c.fetchone()
            if not student:
                logger.error(f"Student not found: {admission_no}")
                flash('Error: Student not found.', 'error')
                return redirect(url_for('main.index'))

            # Fetch marks with normalized exam_type
            c.execute("""
                SELECT admission_no, learning_area, total_marks, exam_out_of, term, year, exam_type, grade
                FROM marks
                WHERE admission_no = ? AND LOWER(term) = LOWER(?) AND year = ? AND LOWER(REPLACE(exam_type, ' ', '')) = ?
            """, (admission_no, term, year, exam_type))
            marks = c.fetchall()
            logger.debug(f"Marks for {admission_no}: {len(marks)} entries")

            if not marks:
                logger.warning(f"No marks found for {admission_no} in {student['grade']}, {term}, {year}, {exam_type}")
                flash(f"No marks found for {term} {year} ({exam_type.replace('endterm', 'End Term').replace('midterm', 'Mid Term')}). "
                      f"Please contact your teacher.", 'error')
                return redirect(url_for('main.index'))

            # Fetch fees
            c.execute("""
                SELECT admission_no, total_fee, amount_paid, balance, grade, term, year
                FROM fees
                WHERE admission_no = ? AND LOWER(term) = LOWER(?) AND year = ?
            """, (admission_no, term, year))
            fees = c.fetchall()

            # Calculate rank
            c.execute("""
                SELECT admission_no, SUM(total_marks) as total
                FROM marks
                WHERE LOWER(grade) = LOWER(?) AND LOWER(term) = LOWER(?) AND year = ? AND LOWER(REPLACE(exam_type, ' ', '')) = ?
                GROUP BY admission_no
                ORDER BY total DESC
            """, (student['grade'], term, year, exam_type))
            ranks = [r['admission_no'] for r in c.fetchall()]
            rank = ranks.index(admission_no) + 1 if admission_no in ranks else 'N/A'
            total_students = len(ranks)

        # Format student data
        student_data = [(None, student['username'], None, None, student['grade'], student['admission_no'])]

        # Generate PDF
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

        if pdf_buffer is None or len(pdf_buffer.getvalue()) == 0:
            logger.error(f"Failed to generate report card for {admission_no}")
            flash('Error generating report card. Please contact the administrator.', 'error')
            return redirect(url_for('main.index'))

        # Send PDF as downloadable file
        pdf_buffer.seek(0)
        filename = f"Report_Card_{admission_no}_{student['grade'].replace(' ', '_')}_{term}_{year}_{exam_type}.pdf"
        logger.info(f"Successfully generated report card for {admission_no}, size={len(pdf_buffer.getvalue())} bytes")
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Error in student_download_report_card for {admission_no}: {str(e)}\n{traceback.format_exc()}")
        flash('An error occurred while generating the report card. Please contact the administrator.', 'error')
        return redirect(url_for('main.index'))