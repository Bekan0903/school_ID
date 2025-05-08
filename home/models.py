from django.db import models
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.db import models
from django.core.mail import send_mail
from django.conf import settings
from datetime import time, datetime
from random import randint
from django.utils import timezone



class Student(models.Model):
    student_name = models.CharField(max_length=50)
    student_class = models.CharField(max_length=5)
    student_section = models.CharField(max_length=2)
    student_age = models.CharField(max_length=2)
    student_photo = models.ImageField(upload_to='student_photos/', blank=False, null=False)
    student_phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    student_address = models.TextField()
    parent_name = models.CharField(max_length=50)
    parent_relation = models.CharField(max_length=10)
    parent_email = models.EmailField(unique=True)
    parent_address = models.TextField()
    parent_phone = models.CharField(max_length=15)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Generate QR code only if the instance is saved and has an ID
        generate_qr = not self.pk  # True if creating a new record
        if not generate_qr and 'qr_code' not in kwargs.get('update_fields', {}):
             # If updating but not updating qr_code specifically, check if it exists
             if not self.qr_code:
                 generate_qr = True # Generate if QR code is missing on update

        if generate_qr and not self.pk: # Save first if it's a new record to get an ID
             super().save(*args, **kwargs)

        if generate_qr:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(f"STUDENT:{self.id}")
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            filename = f'student_qr_{self.id}.png'

            # Use save=False initially to avoid recursive save
            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            # Explicitly call save again to save just the qr_code field
            kwargs['update_fields'] = ['qr_code']

        super().save(*args, **kwargs) # Final save

    def __str__(self):
        return self.student_name

class Worker(models.Model):
    worker_name = models.CharField(max_length=50)
    worker_age = models.CharField(max_length=2)
    worker_department = models.CharField(max_length=50)
    worker_photo = models.ImageField(upload_to='worker_photos/', blank=False, null=False)
    email = models.EmailField(unique=True)
    worker_phone = models.CharField(max_length=15)
    worker_address = models.TextField()
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Generate QR code only if the instance is saved and has an ID
        generate_qr = not self.pk  # True if creating a new record
        if not generate_qr and 'qr_code' not in kwargs.get('update_fields', {}):
             # If updating but not updating qr_code specifically, check if it exists
             if not self.qr_code:
                 generate_qr = True # Generate if QR code is missing on update

        if generate_qr and not self.pk: # Save first if it's a new record to get an ID
             super().save(*args, **kwargs)

        if generate_qr:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(f"WORKER:{self.id}")
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            filename = f'worker_qr_{self.id}.png'

            # Use save=False initially to avoid recursive save
            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            # Explicitly call save again to save just the qr_code field
            kwargs['update_fields'] = ['qr_code']

        super().save(*args, **kwargs) # Final save

    def __str__(self):
        return self.worker_name

class BookCheckout(models.Model):
    STUDENT = 'student'
    WORKER = 'worker'
    USER_TYPE_CHOICES = [
        (STUDENT, 'Student'),
        (WORKER, 'Worker'),
    ]

    user_id = models.PositiveIntegerField()
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)
    book_title = models.CharField(max_length=200)
    book_author = models.CharField(max_length=100)
    checkout_date = models.DateTimeField(auto_now_add=True)
    checkout_id = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)
    due_date = models.DateTimeField()
    returned = models.BooleanField(default=False)
    return_date = models.DateTimeField(null=True, blank=True)
    overdue = models.BooleanField(default=False)


    class Meta:
        ordering = ['-checkout_date']

    def __str__(self):
        return f"{self.book_title} - {self.get_user_display()}"

    def get_user_display(self):
        if self.user_type == self.STUDENT:
            user = Student.objects.filter(id=self.user_id).first()
            return user.student_name if user else f"Student #{self.user_id}"
        else:
            user = Worker.objects.filter(id=self.user_id).first()
            return user.worker_name if user else f"Worker #{self.user_id}"

    def save(self, *args, **kwargs):
        if not self.checkout_id:
            # Generate a unique checkout ID when first saving
            prefix = 'STU' if self.user_type == 'student' else 'WRK'
            timestamp = datetime.now().strftime('%y%m%d%H%M')
            self.checkout_id = f"{prefix}{self.user_id}-{timestamp}-{randint(100, 999)}"
        
        # Check if book is overdue
        if not self.returned and timezone.now() > self.due_date:
            self.overdue = True
            self.deactivate_user()
        elif self.returned and self.overdue:
            self.reactivate_user_if_eligible()
        
        super().save(*args, **kwargs)
    
    def deactivate_user(self):
        """Deactivate user account if they have overdue books"""
        if self.user_type == 'student':
            user = Student.objects.filter(id=self.user_id).first()
        else:
            user = Worker.objects.filter(id=self.user_id).first()
        
        if user and user.is_active:
            overdue=True
            overdue.save()
            user.is_active = False
            user.save()
    
    def reactivate_user_if_eligible(self):
        """Reactivate user account if no more overdue books"""
        overdue_count = BookCheckout.objects.filter(
            user_id=self.user_id,
            user_type=self.user_type,
            returned=False,
            overdue=True
        ).exclude(id=self.id).count()
        
        if overdue_count == 0:
            if self.user_type == 'student':
                user = Student.objects.filter(id=self.user_id).first()
            else:
                user = Worker.objects.filter(id=self.user_id).first()
            
            if user and not user.is_active:
                user.is_active = True
                user.save()
class AttendanceLog(models.Model):
    ENTRY = 'entry'
    EXIT = 'exit'
    ACTION_CHOICES = [
        (ENTRY, 'Entry'),
        (EXIT, 'Exit'),
    ]
    LOCATION_CHOICES = [
        ('main_gate', 'Main Gate'),
        ('library', 'Library Entrance'),
        ('gym', 'Gym Entrance'),
        ('auditorium', 'Auditorium'),
    ]
    user_id = models.PositiveIntegerField()
    user_type = models.CharField(max_length=10)  # 'student' or 'worker'
    action = models.CharField(max_length=5, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    late_entry = models.BooleanField(default=False)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='main_gate')

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # First save the record
        super().save(*args, **kwargs)
        
        # Then send notifications (only for new records)
        if not kwargs.get('update_fields'):  # Only for new records, not updates
            self.send_notifications()
    
    def send_notifications(self):
        if self.user_type == 'student':
            try:
                student = Student.objects.get(id=self.user_id)
                subject = f"School {'Entry' if self.action == self.ENTRY else 'Exit'} Notification"
                message = (f"Dear {student.student_name},\n\n"
                         f"You have {'entered' if self.action == self.ENTRY else 'exited'} "
                         f"the school at {self.timestamp.strftime('%Y-%m-%d %H:%M')}.\n"
                         f"{'NOTE: This was a late entry.' if self.late_entry else ''}\n\n"
                         "School Administration")

                # Send to both student and parent emails if they exist
                recipient_list = []
                if student.email:
                    recipient_list.append(student.email)
                if student.parent_email:
                    recipient_list.append(student.parent_email)

                if recipient_list:  # Only send if we have recipients
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        recipient_list,
                        fail_silently=False,
                    )
            except Student.DoesNotExist:
                print(f"Failed to send email: Student with id {self.user_id} not found.")
            except Exception as e:
                print(f"Failed to send email for student {self.user_id}: {e}")