from django import forms
from .models import Student

class studentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_name','student_class','student_section','student_age','student_photo','student_phone','email','student_address','parent_name','parent_relation','parent_email','parent_address','parent_phone']