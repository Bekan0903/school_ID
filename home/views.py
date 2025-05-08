from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import studentForm
from .models import Student, Worker, BookCheckout
import json
from django.utils import timezone 
from datetime import datetime
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from .models import AttendanceLog
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    return render(request, 'home.html')

def scannerw(request):
    if 'admin_id' not in request.session or request.session.get('admin_department', '').lower() != 'security':
        return redirect('admin')
    return render(request, 'scannerw.html')

def index(request):
    return render(request, 'index.html')
def scanner(request):
    if 'admin_id' not in request.session or request.session.get('admin_department', '').lower() != 'librarian':
        return redirect('admin')
    return render(request, 'scanner.html')

def about(request):
    return render(request, 'about.html')

def verify_user(request, user_id, user_type):
    if user_type == 'student':
        user = get_object_or_404(Student, id=user_id)
    elif user_type == 'worker':
        user = get_object_or_404(Worker, id=user_id)
    else:
        return redirect('index')
    
    # Store verification in session
    request.session['verified_user_id'] = user.id
    request.session['verified_user_type'] = user_type
    
    # Redirect to myaccount page which will show the verified user
    return redirect('myaccount')
def custom_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def myaccount(request):
    # Check if we're viewing a verified user (from QR scan)
    if 'verified_user_id' in request.session:
        user_id = request.session['verified_user_id']
        user_type = request.session.get('verified_user_type')
        
        try:
            if user_type == 'student':
                user = Student.objects.get(id=user_id)
                user_data = {
                    'name': user.student_name,
                    'email': user.email,
                    'age': user.student_age,
                    'class': user.student_class,
                    'section': user.student_section,
                    'phone': user.student_phone,
                    'photo': user.student_photo.url if user.student_photo else None,
                    'address': user.student_address,
                    'parent_name': user.parent_name,
                    'parent_relation': user.parent_relation,
                    'qr_code': user.qr_code.url if user.qr_code else None,
                    'is_verified_view': True
                }
            elif user_type == 'worker':
                user = Worker.objects.get(id=user_id)
                user_data = {
                    'name': user.worker_name,
                    'email': user.email,
                    'age': user.worker_age,
                    'photo': user.worker_photo.url if user.worker_photo else None,
                    'address': user.worker_address,
                    'qr_code': user.qr_code.url if user.qr_code else None,
                    'phone': user.worker_phone,
                    'department': user.worker_department,
                    'is_verified_view': True
                }
            return render(request, 'my account.html', {
                'user_data': user_data, 
                'user_type': user_type,
                'recent_activities': []  # No activities shown for verified views
            })
        except:
            return redirect('index')

    # Check normal session-based login
    if 'user_id' not in request.session:
        return redirect('login')

    try:
        # Check if user is a student
        student = Student.objects.get(id=request.session['user_id'])
        user_data = {
            'name': student.student_name,
            'email': student.email,
            'age': student.student_age,
            'class': student.student_class,
            'section': student.student_section,
            'phone': student.student_phone,
            'photo': student.student_photo.url if student.student_photo else None,
            'address': student.student_address,
            'parent_name': student.parent_name, 
            'parent_relation': student.parent_relation,
            'qr_code': student.qr_code.url if student.qr_code else None,
            'is_verified_view': False
        }
        user_type = 'student'
    except Student.DoesNotExist:
        try:
            # Check if user is a worker
            worker = Worker.objects.get(id=request.session['user_id'])
            user_data = {
                'name': worker.worker_name,
                'email': worker.email,
                'age': worker.worker_age,
                'photo': worker.worker_photo.url if worker.worker_photo else None,
                'address': worker.worker_address,
                'qr_code': worker.qr_code.url if worker.qr_code else None,
                'phone': worker.worker_phone,
                'department': worker.worker_department,
                'is_verified_view': False
            }
            user_type = 'worker'
        except Worker.DoesNotExist:
            return redirect('login')

    # Get recent activities
    recent_activities = []
    
    # 1. Add current login activity
    recent_activities.append({
        'type': 'login',
        'timestamp': timezone.now(),
        'description': 'Logged in to Digital ID system'
    })
    
    # 2. Add door access activities (last 5)
    try:
        door_activities = AttendanceLog.objects.filter(
            user_id=request.session['user_id'],
            user_type=user_type
        ).order_by('-timestamp')[:5]
        
        for activity in door_activities:
            recent_activities.append({
                'type': activity.action,
                'timestamp': activity.timestamp,
                'location': getattr(activity, 'location', 'Main Gate'),
                'late': activity.late_entry if activity.action == 'entry' else False
            })
    except Exception as e:
        print(f"Error fetching door activities: {e}")

    # 3. Add library activities (last 3)
    try:
        library_activities = BookCheckout.objects.filter(
            user_id=request.session['user_id'],
            user_type=user_type
        ).order_by('-checkout_date')[:3]
        
        for activity in library_activities:
            recent_activities.append({
                'type': 'library',
                'timestamp': activity.checkout_date,
                'book_title': activity.book_title,
                'due_date': activity.due_date,
                'returned': activity.returned
            })
    except Exception as e:
        print(f"Error fetching library activities: {e}")

    # Sort all activities by timestamp (newest first) and limit to 10
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:10]

    return render(request, 'my account.html', {
        'user_data': user_data,
        'user_type': user_type,
        'recent_activities': recent_activities,
        'is_verified': False
    })
# In views.py
@csrf_exempt
def log_access(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            user_type = data.get('user_type')
            action = data.get('action')
            location = data.get('location', 'main_gate')  # Default to main gate
            
            # Check for late entry
            late_entry = False
            if action == 'entry':
                now = timezone.localtime(timezone.now())
                late_time = now.replace(hour=8, minute=30, second=0, microsecond=0)
                if now > late_time:
                    late_entry = True
            
            # Create the log
            log = AttendanceLog.objects.create(
                user_id=user_id,
                user_type=user_type,
                action=action,
                late_entry=late_entry,
                location=location
            )
            
            # Send email notification via API-style call
            send_access_notification_email(
                user_id=user_id,
                user_type=user_type,
                action=action,
                timestamp=log.timestamp,
                late_entry=late_entry
            )
            
            return JsonResponse({
                'success': True,
                'log_id': log.id,
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M'),
                'late_entry': late_entry
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })
def verify_user_api(request):
    user_type = request.GET.get('user_type')
    user_id = request.GET.get('user_id')
    
    try:
        if user_type == 'student':
            user = Student.objects.get(id=user_id)
            overdue_books = BookCheckout.objects.filter(
                user_id=user_id,
                user_type='student',
                returned=False,
                due_date__lt=timezone.now()
            ).exists()
            
            if overdue_books and user.is_active:
                user.is_active = False
                user.save()
            return JsonResponse({
                'valid': True,
                'user': {
                    'id': user.id,
                    'name': user.student_name,
                    'type': 'student',
                    'class_info': f"{user.student_class}-{user.student_section}",
                    'photo': user.student_photo.url if user.student_photo else None,
                    'status': 'active' if user.is_active else 'inactive'
                }
            })
        elif user_type == 'worker':
            user = Worker.objects.get(id=user_id)
            overdue_books = BookCheckout.objects.filter(
                user_id=user_id,
                user_type='worker',
                returned=False,
                due_date__lt=timezone.now()
            ).exists()
            
            if overdue_books and user.is_active:
                user.is_active = False
                user.save()
            return JsonResponse({
                'valid': True,
                'user': {
                    'id': user.id,
                    'name': user.worker_name,
                    'type': 'worker',
                    'department': user.worker_department,
                    'photo': user.worker_photo.url if user.worker_photo else None,
                    'status': 'active' if user.is_active else 'inactive'
                }
            })
        
        return JsonResponse({'valid': False, 'message': 'Invalid user type'})
    except (Student.DoesNotExist, Worker.DoesNotExist):
        return JsonResponse({'valid': False, 'message': 'User not found'})
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})
def sample(request):
    return render(request, 'sample.html')

def team(request):
    return render(request, 'team.html')

def service(request):
    return render(request, 'service.html')

def login(request):
     return render(request, 'login.html')

def register(request):
    return render(request, "register.html")
def admin(request):
    return render(request, 'admin.html')
# Add to views.py
@csrf_exempt
def admin_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            department = data.get('department')  # Will be 'Librarian' or 'Security'
            password = data.get('password')
            
            # Find a worker with matching department (case-insensitive)
            worker = Worker.objects.filter(
                worker_department__iexact=department,
                is_active=True
            ).first()
            
            if worker and check_password(password, worker.password):
                # Login successful - create session
                request.session['admin_id'] = worker.id
                request.session['admin_department'] = worker.worker_department
                
                return JsonResponse({
                    'success': True,
                    'department': worker.worker_department,
                    'message': 'Login successful'
                })
            
            return JsonResponse({
                'success': False,
                'message': 'Invalid department or password'
            }, status=401)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)

def register_student(request):
    return render(request, "register_student.html")

def register_worker(request):
    return render(request, "register_worker.html")
def through(request):
    return render(request, "through.html")
# Terms & Conditions view (optional)
def terms_condition(request):
    return render(request, "terms&condition.html")

def logout_view(request):
    logout(request)
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect("index")

@csrf_exempt
def verify_qr(request):
    if request.method == 'GET':
        qr_data = request.GET.get('qr_data', '')
        
        try:
            user_type, user_id = qr_data.split(':')
            user_id = int(user_id)
            
            if user_type == 'STUDENT':
                user = get_object_or_404(Student, id=user_id)
                user_data = {
                    'id': user.id,
                    'name': user.student_name,
                    'type': 'student',
                    'class_info': f"{user.student_class}-{user.student_section}",
                    'photo': user.student_photo.url if user.student_photo else None,
                    'status': 'active' if user.is_active else 'inactive'
                }
            elif user_type == 'WORKER':
                user = get_object_or_404(Worker, id=user_id)
                user_data = {
                    'id': user.id,
                    'name': user.worker_name,
                    'type': 'worker',
                    'department': user.worker_department,
                    'photo': user.worker_photo.url if user.worker_photo else None,
                    'status': 'active' if user.is_active else 'inactive'
                }
            else:
                return JsonResponse({'valid': False, 'message': 'Invalid user type'})
            
            return JsonResponse({
                'valid': True,
                'user': user_data
            })
            
        except (ValueError, IndexError, AttributeError):
            return JsonResponse({'valid': False, 'message': 'Invalid QR code format'})
        except Exception as e:
            return JsonResponse({'valid': False, 'message': str(e)})
    
    return JsonResponse({'valid': False, 'message': 'Invalid request method'})

@csrf_exempt
def checkout_book(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            user_type = data.get('user_type')
            book_title = data.get('book_title')
            book_author = data.get('book_author')
            borrow_minutes = int(data.get('borrow_minutes', 10080))  # Default 1 week
            
            # Calculate due date
            due_date = timezone.now() + timedelta(minutes=borrow_minutes)
            
            # Create checkout record
            checkout = BookCheckout.objects.create(
                user_id=user_id,
                user_type=user_type,
                book_title=book_title,
                book_author=book_author,
                due_date=due_date
            )
            
            # Send email notification
            send_checkout_email(user_id, user_type, book_title, due_date)
            
            return JsonResponse({
                'success': True,
                'checkout_id': checkout.id,
                'due_date': due_date.strftime('%Y-%m-%d %H:%M')
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

def send_checkout_email(user_id, user_type, book_title, due_date):
    try:
        if user_type == 'student':
            user = Student.objects.get(id=user_id)
            email = user.email
            name = user.student_name
        else:
            user = Worker.objects.get(id=user_id)
            email = user.email
            name = user.worker_name
            
        subject = f"Library Book Checkout Confirmation"
        message = (f"Dear {name},\n\n"
                 f"You have checked out '{book_title}' from the school library.\n"
                 f"Due Date: {due_date.strftime('%Y-%m-%d')}\n\n"
                 "Please return the book on or before the due date to avoid late fees.\n\n"
                 "School Library System")
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send checkout email: {e}")

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip()
        password = request.POST.get('password')

        try:
            # Check student table
            if Student.objects.filter(email=email).exists():
                student = Student.objects.get(email=email)
                if check_password(password, student.password):
                    request.session['user_id'] = student.id
                    request.session['user_type'] = 'student'
                    messages.success(request, "Login successful!")
                    return redirect('myaccount')
            
            # Check worker table
            elif Worker.objects.filter(email=email).exists():
                worker = Worker.objects.get(email=email)
                if check_password(password, worker.password):
                    request.session['user_id'] = worker.id
                    request.session['user_type'] = 'worker'
                    messages.success(request, "Login successful!")
                    return redirect('myaccount')
            
            messages.error(request, "Invalid credentials!")
            
        except Exception as e:
            messages.error(request, "An error occurred during login")
            print(f"Login error: {str(e)}")

    return render(request, 'login.html')
def insertstudent(request):
    if request.method == 'POST':
        gname = request.POST.get('student_name')
        gclass = request.POST.get('student_class')
        gsection = request.POST.get('student_section')
        gage = request.POST.get('student_age')
        gphoto = request.FILES.get('student_photo')
        gphone = request.POST.get('student_phone')
        gemail = request.POST.get('email')
        gaddress = request.POST.get('student_address')
        pname = request.POST.get('parent_name')
        prelation = request.POST.get('parent_relation')
        pemail = request.POST.get('parent_email')
        paddress = request.POST.get('parent_address')
        pphone = request.POST.get('parent_phone')
        gpassword = request.POST.get('password')

        hashed_password = make_password(gpassword)
        st = Student(student_name=gname , student_class=gclass, student_section=gsection, student_age=gage, student_photo=gphoto, student_phone=gphone, email=gemail, student_address=gaddress, parent_name=pname, parent_relation=prelation, parent_email=pemail, parent_address=paddress, parent_phone=pphone, password=hashed_password)
        st.save()
        return redirect('terms_codition')
    return render(request, 'register_student.html')
def insertworker(request):
    if request.method == 'POST':
        wname = request.POST.get('worker_name')
        wage = request.POST.get('worker_age')
        wdepartment= request.POST.get('worker_department')
        wphoto = request.FILES.get('worker_photo')
        wemail = request.POST.get('email')
        wphone = request.POST.get('worker_phone')
        waddress = request.POST.get('worker_address')
        wpassword = request.POST.get('password')


        hashed_password = make_password(wpassword)
        wk = Worker(worker_name=wname , worker_age=wage,worker_department=wdepartment, worker_photo=wphoto, email=wemail, worker_phone=wphone, worker_address=waddress, password=hashed_password)
        wk.save()  
        return redirect('terms_condition')
    return render(request , 'register_worker.html')

def student_profile(request):
    student = Student.objects.all()
    return render(request, 'student.html', {'studentdata': student})
def worker_profile(request):
    worker = Worker.objects.all()
    return render(request, 'worker.html', {'workerdata': worker})
@csrf_exempt

def return_books(request):
    # Get ALL non-returned books with user info
    active_checkouts = BookCheckout.objects.filter(
        returned=False
    ).order_by('-checkout_date')
    
    # Enhance checkout data with borrower information
    enhanced_checkouts = []
    for checkout in active_checkouts:
        if checkout.user_type == 'student':
            user = Student.objects.filter(id=checkout.user_id).first()
            user_display = f"{user.student_name if user else 'Unknown Student'}"
            user_details = f"Class: {user.student_class}-{user.student_section}" if user else ""
        else:
            user = Worker.objects.filter(id=checkout.user_id).first()
            user_display = f"{user.worker_name if user else 'Unknown Staff'}"
            user_details = f"Dept: {user.worker_department}" if user else ""
        
        enhanced_checkouts.append({
            'checkout': checkout,
            'user_display': user_display,
            'user_details': user_details,
            'is_overdue': checkout.due_date < timezone.now()
        })
    
    if request.method == 'POST':
        checkout_id = request.POST.get('checkout_id')
        try:
            checkout = BookCheckout.objects.get(
                id=checkout_id,
                returned=False
            )
            checkout.returned = True
            checkout.return_date = timezone.now()
            checkout.save()
            
            messages.success(request, f"'{checkout.book_title}' returned successfully!")
            return redirect('return_book')
            
        except BookCheckout.DoesNotExist:
            messages.error(request, "Invalid book return request")
    
    return render(request, 'return_books.html', {
        'checkouts': enhanced_checkouts
    })
@csrf_exempt
def send_access_email(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            user_type = data.get('user_type')
            action = data.get('action')  # 'entry' or 'exit'
            timestamp = data.get('timestamp')  # Optional, will use current time if not provided
            late_entry = data.get('late_entry', False)  # Optional, defaults to False
            
            if not all([user_id, user_type, action]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required parameters'
                }, status=400)
            
            # Convert string timestamp to datetime if provided
            if timestamp and isinstance(timestamp, str):
                try:
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    timestamp = timezone.now()
            else:
                timestamp = timezone.now()
            
            # Send the email
            result = send_access_notification_email(
                user_id=user_id,
                user_type=user_type,
                action=action,
                timestamp=timestamp,
                late_entry=late_entry
            )
            
            if result:
                return JsonResponse({
                    'success': True,
                    'message': 'Email notification sent successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Email notification failed (no valid recipients)'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)

def send_access_notification_email(user_id, user_type, action, timestamp, late_entry=False):
    """Helper function to send access notification emails"""
    try:
        if user_type == 'student':
            student = Student.objects.get(id=user_id)
            subject = f"School {'Entry' if action == 'entry' else 'Exit'} Notification"
            message = (f"Dear {student.student_name},\n\n"
                     f"Your child has {'entered' if action == 'entry' else 'exited'} "
                     f"the school at {timestamp.strftime('%Y-%m-%d %H:%M')}.\n"
                     f"{'NOTE: This was a late entry.' if late_entry else ''}\n\n"
                     "School Administration")

            # Prepare recipients
            recipients = []
            if student.email:
                recipients.append(student.email)
            if student.parent_email:
                recipients.append(student.parent_email)

            if recipients:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    recipients,
                    fail_silently=False,
                )
                return True
        return False
    except Student.DoesNotExist:
        print(f"Student with id {user_id} not found")
        return False
    except Exception as e:
        print(f"Failed to send access email: {str(e)}")
        return False
@csrf_exempt
def change_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            
            if not current_password or not new_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Current password and new password are required'
                }, status=400)
            
            if 'user_id' not in request.session:
                return JsonResponse({
                    'success': False,
                    'message': 'Session expired. Please login again.'
                }, status=401)
            
            user_id = request.session['user_id']
            user_type = request.session.get('user_type')
            
            if user_type == 'student':
                try:
                    student = Student.objects.get(id=user_id)
                    if not check_password(current_password, student.password):
                        return JsonResponse({
                            'success': False,
                            'message': 'Current password is incorrect'
                        }, status=400)
                    
                    student.password = make_password(new_password)
                    student.save()
                    
                    # Update session auth hash if user is changing their own password
                    if hasattr(request, 'user') and request.user.is_authenticated:
                        update_session_auth_hash(request, student)
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Password updated successfully'
                    })
                
                except Student.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Student not found'
                    }, status=404)
            
            elif user_type == 'worker':
                try:
                    worker = Worker.objects.get(id=user_id)
                    if not check_password(current_password, worker.password):
                        return JsonResponse({
                            'success': False,
                            'message': 'Current password is incorrect'
                        }, status=400)
                    
                    worker.password = make_password(new_password)
                    worker.save()
                    
                    # Update session auth hash if user is changing their own password
                    if hasattr(request, 'user') and request.user.is_authenticated:
                        update_session_auth_hash(request, worker)
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Password updated successfully'
                    })
                
                except Worker.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Worker not found'
                    }, status=404)
            
            return JsonResponse({
                'success': False,
                'message': 'Invalid user type'
            }, status=400)
        
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=405)