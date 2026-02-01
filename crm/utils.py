from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *

def generate_analytics(period='month', date_from=None, date_to=None):
    """Генерация аналитики для заданного периода"""
    
    if not date_from:
        date_from = timezone.now() - timedelta(days=30)
    if not date_to:
        date_to = timezone.now()
    
    analytics = {
        'total_revenue': Payment.objects.filter(
            is_paid=True,
            payment_date__gte=date_from,
            payment_date__lte=date_to
        ).aggregate(total=Sum('amount'))['total'] or 0,
        
        'active_cases': Case.objects.filter(
            is_active=True,
            created_at__gte=date_from
        ).count(),
        
        'new_clients': Client.objects.filter(
            created_at__gte=date_from,
            created_at__lte=date_to
        ).count(),
        
        'avg_case_duration': Case.objects.filter(
            end_date__isnull=False,
            created_at__gte=date_from
        ).aggregate(avg=Avg(
            timezone.now() - timezone.timedelta(days=1)  # Placeholder
        ))['avg'],
        
        'lawyer_productivity': [],
        'case_type_distribution': {},
        'revenue_by_month': [],
    }
    
    # Статистика по юристам
    lawyers = CustomUser.objects.filter(role='lawyer', is_active=True)
    for lawyer in lawyers:
        cases = Case.objects.filter(lawyer=lawyer, is_active=True)
        payments = Payment.objects.filter(
            case__lawyer=lawyer,
            is_paid=True,
            payment_date__gte=date_from
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        analytics['lawyer_productivity'].append({
            'name': lawyer.get_full_name(),
            'cases_count': cases.count(),
            'revenue': payments,
            'efficiency': payments / (lawyer.hourly_rate * 160) if lawyer.hourly_rate > 0 else 0  # 160 часов в месяц
        })
    
    # Распределение по типам дел
    for case_type, label in Case.TYPE_CHOICES:
        count = Case.objects.filter(
            case_type=case_type,
            created_at__gte=date_from
        ).count()
        if count > 0:
            analytics['case_type_distribution'][label] = count
    
    return analytics

def create_calendar_event_from_communication(communication):
    """Создание события календаря из коммуникации"""
    if communication.scheduled_for and communication.communication_type in ['meeting', 'phone']:
        event = CalendarEvent.objects.create(
            title=f"{communication.get_communication_type_display()}: {communication.subject}",
            description=communication.content,
            event_type='meeting' if communication.communication_type == 'meeting' else 'reminder',
            start_time=communication.scheduled_for,
            end_time=communication.scheduled_for + timedelta(minutes=communication.duration or 30),
            case=communication.case,
            created_by=communication.created_by
        )
        event.participants.set(communication.participants.all())
        return event
    return None

def send_notification(user, title, message, notification_type='info'):
    """Отправка уведомления пользователю"""
    # Здесь можно интегрировать с WebSocket для real-time уведомлений
    # или использовать Django messages framework
    from django.contrib import messages
    
    # Для примера, сохраняем в сессии
    messages.add_message(
        request,  # Нужен доступ к request
        messages.INFO if notification_type == 'info' else messages.WARNING,
        message
    )