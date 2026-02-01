from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import *

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'role', 'first_name', 'last_name', 'phone')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['company_name', 'inn', 'address', 'status', 'source', 'notes']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ['title', 'client', 'lawyer', 'case_type', 'stage', 'description', 
                 'budget', 'start_date', 'end_date', 'success_probability']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'success_probability': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'case', 'assigned_to', 'priority', 
                 'due_date', 'estimated_hours']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'estimated_hours': forms.NumberInput(attrs={'step': 0.5, 'min': 0.5}),
        }

class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        fields = ['communication_type', 'subject', 'content', 'participants', 
                 'scheduled_for', 'duration']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
            'scheduled_for': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        }

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['title', 'description', 'category', 'file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = ['title', 'description', 'event_type', 'start_time', 
                 'end_time', 'case', 'participants', 'location', 'is_all_day', 'color']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'participants': forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        }

class TimeEntryForm(forms.ModelForm):
    class Meta:
        model = TimeEntry
        fields = ['case', 'task', 'description', 'start_time', 'end_time', 'billable']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'payment_type', 'payment_date', 'due_date', 
                 'is_paid', 'paid_date', 'payment_method', 'invoice_number', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'paid_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }