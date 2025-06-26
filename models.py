from django.db import models
from django.core.validators import MinLengthValidator

class Teacher(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(
        max_length=128,
        validators=[MinLengthValidator(6)],
        help_text="Password must be at least 6 characters"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.roll_number})"


class Mark(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    exam_name = models.CharField(max_length=50) 
    marks_obtained = models.FloatField()
    max_marks = models.PositiveIntegerField()
    min_marks = models.PositiveIntegerField()
    entered_by = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Mark Entry"
        verbose_name_plural = "Marks"

    def __str__(self):
        return f"{self.student.name} - {self.subject} - {self.exam_name}"
