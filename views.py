# Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from .models import Teacher, Student, Mark

# Utilities
def student_to_dict(student, mark):
    percentage = (mark.marks_obtained / mark.max_marks) * 100 if mark.max_marks else 0
    status = 'Pass' if percentage >= 40 else 'Fail'
    return {
        'id': student.id,
        'name': student.name,
        'roll_number': student.roll_number,
        'subject': mark.subject,
        'marks_obtained': mark.marks_obtained,
        'max_marks': mark.max_marks,
        'status': status
    }

# ─── Teacher Auth Views ────────────────────────────────────────────────

def teacher_register(request):
    response_data = {'status': 'error', 'message': '', 'error_field': {}}

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        error_field = {}

        if not name:
            error_field['name'] = 'Name is required.'
        if not email:
            error_field['email'] = 'Email is required.'
        elif Teacher.objects.filter(email=email).exists():
            error_field['email'] = 'Email already registered.'
        if not password:
            error_field['password'] = 'Password is required.'
        if password != confirm_password:
            error_field['confirm_password'] = 'Passwords do not match.'

        if error_field:
            response_data['error_field'] = error_field
            return JsonResponse(response_data)

        Teacher.objects.create(name=name, email=email, password=make_password(password))
        response_data.update({'status': 'success', 'message': 'Registered successfully.'})
        return JsonResponse(response_data)

    return render(request, 'register.html')


def teacher_login(request):
    response_data = {'status': 'error', 'message': '', 'error_field': {}}

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        if not email or not password:
            if not email:
                response_data['error_field']['email'] = 'Email is required.'
            if not password:
                response_data['error_field']['password'] = 'Password is required.'
            return JsonResponse(response_data)

        try:
            teacher = Teacher.objects.get(email=email)
            if check_password(password, teacher.password):
                request.session['teacher_email'] = teacher.email
                response_data['status'] = 'success'
            else:
                response_data['message'] = 'Invalid password.'
        except Teacher.DoesNotExist:
            response_data['message'] = 'Email not registered.'

        return JsonResponse(response_data)

    return render(request, 'login.html')


def logout(request):
    if 'teacher_email' in request.session:
        del request.session['teacher_email']
    return redirect('teacher_login')


# ─── Student & Mark Management Views ───────────────────────────────────

def handle_student_list(request):
    if 'teacher_email' not in request.session:
        return redirect('teacher_login')

    teacher = get_object_or_404(Teacher, email=request.session['teacher_email'])

    search_query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('sort_order', 'desc')
    sort_by = request.GET.get('sort_by', 'id')
    rows_per_page = int(request.GET.get('rows_per_page', 10))
    page_number = request.GET.get('page', 1)

    marks = Mark.objects.filter(entered_by=teacher).select_related('student')

    if search_query:
        marks = marks.filter(
            Q(student__name__icontains=search_query) |
            Q(student__roll_number__icontains=search_query)
        )

    order = '' if sort_order == 'asc' else '-'
    if sort_by == 'name':
        marks = marks.order_by(f'{order}student__name')
    elif sort_by == 'roll_number':
        marks = marks.order_by(f'{order}student__roll_number')
    else:
        marks = marks.order_by(f'{order}id')

    paginator = Paginator(marks, rows_per_page)
    page_obj = paginator.get_page(page_number)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'items': [student_to_dict(m.student, m) for m in page_obj.object_list],
            'total': paginator.count,
            'page': page_obj.number,
            'rows_per_page': rows_per_page,
        })

    return render(request, 'home.html', {
        'students': page_obj,
        'search_query': search_query,
        'sort_order': sort_order,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page_obj': page_obj,
    })


def add_student(request):
    response_data = {'status': 'error', 'message': '', 'error_field': {}, 'student': None}

    if 'teacher_email' not in request.session:
        response_data['message'] = 'Unauthorized. Please log in.'
        return JsonResponse(response_data)

    teacher = get_object_or_404(Teacher, email=request.session['teacher_email'])

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        roll_number = request.POST.get('roll_number', '').strip()
        subject = request.POST.get('subject', '').strip()
        marks_obtained = request.POST.get('marks_obtained', '').strip()
        max_marks = request.POST.get('max_marks', '').strip()

        error_field = {}

        # Field validations
        if not name:
            error_field['name'] = 'Name is required.'
        if not roll_number:
            error_field['roll_number'] = 'Roll number is required.'
        if not subject:
            error_field['subject'] = 'Subject is required.'

        # Type validation
        try:
            marks_obtained = float(marks_obtained)
        except ValueError:
            error_field['marks_obtained'] = 'Enter valid marks.'

        try:
            max_marks = int(max_marks)
        except ValueError:
            error_field['max_marks'] = 'Enter valid max marks.'

        # Logical validation
        if 'marks_obtained' not in error_field and 'max_marks' not in error_field:
            if marks_obtained > max_marks:
                error_field['marks_obtained'] = 'Marks obtained cannot be more than max marks.'

        if error_field:
            response_data['error_field'] = error_field
            return JsonResponse(response_data)

        # Check if student exists
        student = Student.objects.filter(roll_number=roll_number).first()

        if student:
            # If same roll number but different name
            if student.name != name:
                response_data['error_field']['roll_number'] = f"Roll number already exists for another student."
                return JsonResponse(response_data)

            # Check if mark already exists for same subject by same teacher
            existing_mark = Mark.objects.filter(
                student=student,
                subject=subject,
                entered_by=teacher
            ).first()

            if existing_mark:
                existing_mark.marks_obtained += marks_obtained
                existing_mark.max_marks += max_marks
                existing_mark.min_marks = int(existing_mark.max_marks * 0.4)
                existing_mark.save()

                response_data.update({
                    'status': 'success',
                    'message': 'Mark updated with accumulated values.',
                    'student': student_to_dict(student, existing_mark)
                })
                return JsonResponse(response_data)
        else:
            # Create new student if not exists
            student = Student.objects.create(name=name, roll_number=roll_number)

        # Create new mark entry
        try:
            mark = Mark.objects.create(
                student=student,
                subject=subject,
                marks_obtained=marks_obtained,
                max_marks=max_marks,
                min_marks=int(max_marks * 0.4),
                entered_by=teacher
            )
            response_data.update({
                'status': 'success',
                'message': 'Student and mark added successfully.',
                'student': student_to_dict(student, mark)
            })
        except IntegrityError:
            response_data['message'] = 'An error occurred while saving.'

    return JsonResponse(response_data)


def update_student(request, student_id):
    response_data = {'status': 'error', 'message': '', 'error_field': {}, 'student': None}

    if 'teacher_email' not in request.session:
        response_data['message'] = 'Unauthorized. Please log in.'
        return JsonResponse(response_data)

    teacher = get_object_or_404(Teacher, email=request.session['teacher_email'])
    student = get_object_or_404(Student, id=student_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        roll_number = request.POST.get('roll_number', '').strip()
        subject = request.POST.get('subject', '').strip()
        marks_obtained = request.POST.get('marks_obtained', '').strip()
        max_marks = request.POST.get('max_marks', '').strip()

        error_field = {}

        if not name:
            error_field['name'] = 'Name is required.'
        if not roll_number:
            error_field['roll_number'] = 'Roll number is required.'
        elif Student.objects.filter(roll_number=roll_number).exclude(id=student.id).exists():
            error_field['roll_number'] = 'Another student with this roll number exists.'
        if not subject:
            error_field['subject'] = 'Subject is required.'
        try:
            marks_obtained = float(marks_obtained)
        except ValueError:
            error_field['marks_obtained'] = 'Enter valid marks.'
        try:
            max_marks = int(max_marks)
        except ValueError:
            error_field['max_marks'] = 'Enter valid max marks.'

        if not error_field and marks_obtained > max_marks:
            error_field['marks_obtained'] = 'Marks cannot exceed max marks.'

        if error_field:
            response_data['error_field'] = error_field
            return JsonResponse(response_data)

        # ✅ Get mark using all unique identifiers
        try:
            mark = Mark.objects.get(student=student, entered_by=teacher, subject=subject)
        except Mark.DoesNotExist:
            response_data['message'] = 'Mark record not found.'
            return JsonResponse(response_data)
        except Mark.MultipleObjectsReturned:
            response_data['message'] = 'Duplicate mark records found. Please resolve in database.'
            return JsonResponse(response_data)

        try:
            student.name = name
            student.roll_number = roll_number
            student.save()

            mark.marks_obtained = marks_obtained
            mark.max_marks = max_marks
            mark.min_marks = int(max_marks * 0.4)
            mark.save()

            response_data.update({
                'status': 'success',
                'message': 'Student and mark updated successfully.',
                'student': student_to_dict(student, mark)
            })
        except IntegrityError:
            response_data['message'] = 'An error occurred while updating.'

    return JsonResponse(response_data)

def delete_student(request, student_id):
    response_data = {'status': 'error', 'message': ''}

    if 'teacher_email' not in request.session:
        response_data['message'] = 'Unauthorized. Please log in.'
        return JsonResponse(response_data)

    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        if not subject:
            response_data['message'] = 'Subject is required to delete a mark.'
            return JsonResponse(response_data)

        teacher = get_object_or_404(Teacher, email=request.session['teacher_email'])
        student = get_object_or_404(Student, id=student_id)

        try:
            # Delete the specific mark for the subject and teacher
            mark = Mark.objects.get(student=student, subject=subject, entered_by=teacher)
            mark.delete()

            # If no more marks remain for the student, delete the student as well
            remaining_marks = Mark.objects.filter(student=student)
            if not remaining_marks.exists():
                student.delete()

            response_data.update({
                'status': 'success',
                'message': f"Mark for subject '{subject}' deleted. Student deleted if no marks left."
            })

        except Mark.DoesNotExist:
            response_data['message'] = 'Mark not found for the given subject.'
        except Exception as e:
            response_data['message'] = f'Error: {str(e)}'
    else:
        response_data['message'] = 'Invalid request method.'

    return JsonResponse(response_data)


