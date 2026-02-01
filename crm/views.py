from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta
from .models import *
from .forms import *
from .utils import generate_analytics

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Общая статистика
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        if user.role in ['admin', 'manager']:
            # Для администраторов и менеджеров
            context['total_cases'] = Case.objects.filter(is_active=True).count()
            context['active_cases'] = Case.objects.filter(
                is_active=True,
                stage__in=['consultation', 'analysis', 'negotiation', 'lawsuit', 'court']
            ).count()
            context['total_clients'] = Client.objects.count()
            context['monthly_revenue'] = Payment.objects.filter(
                payment_date__month=today.month,
                payment_date__year=today.year,
                is_paid=True
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            # Дела с приближающимися дедлайнами
            context['upcoming_deadlines'] = Task.objects.filter(
                status__in=['todo', 'in_progress'],
                due_date__gte=today,
                due_date__lte=today + timedelta(days=7)
            ).order_by('due_date')[:10]
            
            # Календарь событий на сегодня
            context['today_events'] = CalendarEvent.objects.filter(
                start_time__date=today
            ).order_by('start_time')
            
        elif user.role == 'lawyer':
            # Для юристов
            context['my_cases'] = Case.objects.filter(
                lawyer=user,
                is_active=True
            ).count()
            context['my_tasks'] = Task.objects.filter(
                assigned_to=user,
                status__in=['todo', 'in_progress']
            ).count()
            context['upcoming_meetings'] = CalendarEvent.objects.filter(
                participants=user,
                start_time__gte=today,
                start_time__lte=today + timedelta(days=3)
            ).order_by('start_time')
            
        # Аналитика
        context['analytics'] = generate_analytics(today)
        
        return context

class CaseListView(LoginRequiredMixin, ListView):
    model = Case
    template_name = 'crm/case_list.html'
    context_object_name = 'cases'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Case.objects.filter(is_active=True).select_related('client', 'lawyer')
        
        # Фильтрация
        stage = self.request.GET.get('stage')
        lawyer_id = self.request.GET.get('lawyer')
        search = self.request.GET.get('search')
        
        if stage:
            queryset = queryset.filter(stage=stage)
        if lawyer_id:
            queryset = queryset.filter(lawyer_id=lawyer_id)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(case_number__icontains=search) |
                Q(client__user__first_name__icontains=search) |
                Q(client__user__last_name__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lawyers'] = CustomUser.objects.filter(role='lawyer', is_active=True)
        context['stages'] = dict(Case.STAGE_CHOICES)
        return context

class CaseDetailView(LoginRequiredMixin, DetailView):
    model = Case
    template_name = 'crm/case_detail.html'
    context_object_name = 'case'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        case = self.object
        
        # Коммуникации
        context['communications'] = case.communications.all().order_by('-created_at')
        
        # Документы
        context['documents'] = case.documents.all().order_by('-uploaded_at')
        
        # Задачи
        context['tasks'] = case.tasks.all().order_by('-due_date')
        
        # Платежи
        context['payments'] = case.payments.all().order_by('-payment_date')
        
        # Затраты времени
        context['time_entries'] = case.time_entries.all().order_by('-start_time')
        
        # События календаря
        context['calendar_events'] = case.calendar_events.all().order_by('start_time')
        
        # Формы
        context['communication_form'] = CommunicationForm()
        context['document_form'] = DocumentForm()
        context['task_form'] = TaskForm()
        context['payment_form'] = PaymentForm()
        
        return context

class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'crm/task_form.html'
    success_url = reverse_lazy('task_list')
    
    def form_valid(self, form):
        form.instance.assigned_by = self.request.user
        return super().form_valid(form)

class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/calendar.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Получение событий календаря
        events = CalendarEvent.objects.filter(
            Q(participants=user) | Q(created_by=user)
        ).distinct().order_by('start_time')
        
        # Преобразование в формат для FullCalendar
        context['events_json'] = json.dumps([
            {
                'id': event.id,
                'title': event.title,
                'start': event.start_time.isoformat(),
                'end': event.end_time.isoformat() if event.end_time else None,
                'color': event.color,
                'description': event.description,
                'type': event.event_type,
                'case': event.case.title if event.case else None,
            }
            for event in events
        ])
        
        return context

class AnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'crm/analytics.html'
    
    def test_func(self):
        return self.request.user.role in ['admin', 'manager']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Период для аналитики
        period = self.request.GET.get('period', 'month')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        # Генерация аналитики
        context['analytics_data'] = generate_analytics(
            period=period,
            date_from=date_from,
            date_to=date_to
        )
        
        # Распределение по юристам
        lawyers = CustomUser.objects.filter(role='lawyer', is_active=True)
        lawyer_stats = []
        
        for lawyer in lawyers:
            cases_count = Case.objects.filter(lawyer=lawyer).count()
            total_hours = TimeEntry.objects.filter(
                lawyer=lawyer,
                start_time__date__gte=date_from if date_from else timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('duration'))['total'] or 0
            
            revenue = Payment.objects.filter(
                case__lawyer=lawyer,
                is_paid=True,
                payment_date__gte=date_from if date_from else timezone.now() - timedelta(days=30)
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            lawyer_stats.append({
                'lawyer': lawyer,
                'cases_count': cases_count,
                'total_hours': total_hours,
                'revenue': revenue,
                'efficiency': revenue / (lawyer.hourly_rate * total_hours) if total_hours > 0 else 0
            })
        
        context['lawyer_stats'] = lawyer_stats
        
        return context

# API Views
def get_calendar_events(request):
    """API для получения событий календаря"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    events = CalendarEvent.objects.filter(
        start_time__gte=start,
        end_time__lte=end
    ).values('id', 'title', 'start_time', 'end_time', 'color', 'event_type')
    
    return JsonResponse(list(events), safe=False)

def update_task_status(request, task_id):
    """API для обновления статуса задачи"""
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        status = request.POST.get('status')
        
        if status in dict(Task.STATUS_CHOICES):
            task.status = status
            if status == 'done':
                task.completed_at = timezone.now()
            task.save()
            
            return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=400)