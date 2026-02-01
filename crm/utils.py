from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib import messages
from .models import *
import json

def generate_analytics(period='month', date_from=None, date_to=None):
    """Генерация аналитики для заданного периода"""
    
    now = timezone.now()
    
    if not date_from:
        if period == 'day':
            date_from = now - timedelta(days=1)
        elif period == 'week':
            date_from = now - timedelta(days=7)
        elif period == 'month':
            date_from = now - timedelta(days=30)
        elif period == 'quarter':
            date_from = now - timedelta(days=90)
        elif period == 'year':
            date_from = now - timedelta(days=365)
        else:
            date_from = now - timedelta(days=30)
    
    if not date_to:
        date_to = now
    
    # Общая выручка
    payments_qs = Payment.objects.filter(
        is_paid=True,
        payment_date__gte=date_from,
        payment_date__lte=date_to
    )
    total_revenue = payments_qs.aggregate(total=Sum('amount'))['total'] or 0
    
    # Расходы (рассчитываем как сумма зарплат юристов за отработанные часы)
    time_entries_qs = TimeEntry.objects.filter(
        start_time__gte=date_from,
        start_time__lte=date_to,
        billable=True
    ).select_related('lawyer')
    
    total_expenses = 0
    for entry in time_entries_qs:
        if entry.lawyer.hourly_rate:
            total_expenses += entry.duration * entry.lawyer.hourly_rate
    
    # Активные дела
    active_cases = Case.objects.filter(
        is_active=True,
        created_at__gte=date_from
    ).count()
    
    # Новые клиенты
    new_clients = Client.objects.filter(
        created_at__gte=date_from,
        created_at__lte=date_to
    ).count()
    
    # Средняя длительность дела (в днях)
    closed_cases = Case.objects.filter(
        end_date__isnull=False,
        created_at__gte=date_from
    )
    
    avg_duration = 0
    if closed_cases.exists():
        total_days = sum([
            (case.end_date - case.start_date).days 
            for case in closed_cases 
            if case.end_date
        ])
        avg_duration = total_days / closed_cases.count()
    
    analytics = {
        'period': period,
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'total_profit': total_revenue - total_expenses,
        'active_cases': active_cases,
        'new_clients': new_clients,
        'avg_case_duration': round(avg_duration, 1),
        'profit_margin': round(((total_revenue - total_expenses) / total_revenue * 100) if total_revenue > 0 else 0, 1),
        'lawyer_productivity': [],
        'case_type_distribution': {},
        'stage_distribution': {},
        'revenue_by_month': [],
        'top_clients': [],
        'case_success_rate': 0,
    }
    
    # Статистика по юристам
    lawyers = CustomUser.objects.filter(role='lawyer', is_active=True)
    for lawyer in lawyers:
        # Количество дел юриста
        cases = Case.objects.filter(lawyer=lawyer, is_active=True)
        
        # Выручка по делам юриста
        lawyer_revenue = Payment.objects.filter(
            case__lawyer=lawyer,
            is_paid=True,
            payment_date__gte=date_from
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Отработанные часы
        worked_hours = TimeEntry.objects.filter(
            lawyer=lawyer,
            start_time__gte=date_from
        ).aggregate(total=Sum('duration'))['total'] or 0
        
        # Эффективность (выручка на час работы)
        efficiency = 0
        if worked_hours > 0:
            efficiency = lawyer_revenue / worked_hours
        
        # Процент успешных дел
        successful_cases = Case.objects.filter(
            lawyer=lawyer,
            stage='closed',
            created_at__gte=date_from
        ).count()
        
        success_rate = 0
        if cases.count() > 0:
            success_rate = (successful_cases / cases.count()) * 100
        
        analytics['lawyer_productivity'].append({
            'id': lawyer.id,
            'name': lawyer.get_full_name() or lawyer.username,
            'cases_count': cases.count(),
            'revenue': round(lawyer_revenue, 2),
            'worked_hours': round(worked_hours, 2),
            'hourly_rate': lawyer.hourly_rate,
            'efficiency': round(efficiency, 2),
            'success_rate': round(success_rate, 1),
        })
    
    # Сортировка юристов по эффективности
    analytics['lawyer_productivity'].sort(key=lambda x: x['efficiency'], reverse=True)
    
    # Распределение по типам дел
    case_types = dict(Case.TYPE_CHOICES)
    for case_type, label in case_types.items():
        count = Case.objects.filter(
            case_type=case_type,
            created_at__gte=date_from
        ).count()
        if count > 0:
            analytics['case_type_distribution'][label] = {
                'count': count,
                'percentage': round((count / active_cases * 100) if active_cases > 0 else 0, 1)
            }
    
    # Распределение по стадиям
    stages = dict(Case.STAGE_CHOICES)
    for stage, label in stages.items():
        count = Case.objects.filter(
            stage=stage,
            is_active=True,
            created_at__gte=date_from
        ).count()
        if count > 0:
            analytics['stage_distribution'][label] = {
                'count': count,
                'percentage': round((count / active_cases * 100) if active_cases > 0 else 0, 1)
            }
    
    # Выручка по месяцам
    revenue_by_month = []
    current_date = date_from
    while current_date <= date_to:
        month_start = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period in ['year', 'quarter', 'month']:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        else:
            month_end = min(current_date + timedelta(days=30), date_to)
        
        month_revenue = Payment.objects.filter(
            is_paid=True,
            payment_date__gte=month_start,
            payment_date__lte=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_by_month.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': round(month_revenue, 2),
            'start_date': month_start,
            'end_date': month_end
        })
        
        if period in ['year', 'quarter', 'month']:
            current_date = month_end + timedelta(days=1)
        else:
            current_date = month_end
    
    analytics['revenue_by_month'] = revenue_by_month
    
    # Топ клиентов по выручке
    top_clients = []
    clients = Client.objects.filter(
        cases__payments__is_paid=True,
        cases__payments__payment_date__gte=date_from
    ).distinct()
    
    for client in clients:
        client_revenue = Payment.objects.filter(
            case__client=client,
            is_paid=True,
            payment_date__gte=date_from
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if client_revenue > 0:
            top_clients.append({
                'client': client,
                'revenue': round(client_revenue, 2),
                'cases_count': client.cases.count()
            })
    
    top_clients.sort(key=lambda x: x['revenue'], reverse=True)
    analytics['top_clients'] = top_clients[:10]
    
    # Процент успешных дел
    total_closed_cases = Case.objects.filter(
        stage='closed',
        created_at__gte=date_from
    ).count()
    
    total_cases_in_period = Case.objects.filter(
        created_at__gte=date_from,
        created_at__lte=date_to
    ).count()
    
    if total_cases_in_period > 0:
        analytics['case_success_rate'] = round((total_closed_cases / total_cases_in_period) * 100, 1)
    
    return analytics

def create_calendar_event_from_communication(communication):
    """Создание события календаря из коммуникации"""
    if communication.scheduled_for and communication.communication_type in ['meeting', 'phone']:
        end_time = communication.scheduled_for
        if communication.duration:
            end_time = communication.scheduled_for + timedelta(minutes=communication.duration)
        else:
            end_time = communication.scheduled_for + timedelta(minutes=30)
        
        event = CalendarEvent.objects.create(
            title=f"{communication.get_communication_type_display()}: {communication.subject}",
            description=communication.content,
            event_type='meeting' if communication.communication_type == 'meeting' else 'reminder',
            start_time=communication.scheduled_for,
            end_time=end_time,
            case=communication.case,
            created_by=communication.created_by
        )
        event.participants.set(communication.participants.all())
        
        # Уведомление участников
        for participant in communication.participants.all():
            if participant != communication.created_by:
                create_notification(
                    user=participant,
                    title='Новое событие в календаре',
                    message=f'Вас пригласили на {communication.get_communication_type_display()}: {communication.subject}',
                    notification_type='calendar',
                    related_object_id=event.id,
                    related_object_type='calendar_event'
                )
        
        return event
    return None

def create_notification(user, title, message, notification_type='info', 
                       related_object_id=None, related_object_type=None):
    """
    Создание уведомления для пользователя
    """
    try:
        from .models import Notification
        
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_object_id=related_object_id,
            related_object_type=related_object_type
        )
        
        # Здесь можно добавить WebSocket уведомление
        # send_websocket_notification(user.id, {
        #     'id': notification.id,
        #     'title': title,
        #     'message': message,
        #     'type': notification_type,
        #     'created_at': notification.created_at.isoformat(),
        #     'is_read': False
        # })
        
        return notification
    
    except Exception as e:
        # Логирование ошибки
        print(f"Ошибка создания уведомления: {e}")
        return None

def send_task_reminders():
    """Отправка напоминаний о задачах с приближающимся дедлайном"""
    now = timezone.now()
    tomorrow = now + timedelta(days=1)
    
    # Задачи с дедлайном в течение 24 часов
    upcoming_tasks = Task.objects.filter(
        status__in=['todo', 'in_progress'],
        due_date__gte=now,
        due_date__lte=tomorrow
    ).select_related('assigned_to', 'case')
    
    notifications_sent = 0
    
    for task in upcoming_tasks:
        # Создаем уведомление для назначенного пользователя
        notification = create_notification(
            user=task.assigned_to,
            title='Напоминание о задаче',
            message=f'Задача "{task.title}" должна быть выполнена до {task.due_date.strftime("%d.%m.%Y %H:%M")}',
            notification_type='reminder',
            related_object_id=task.id,
            related_object_type='task'
        )
        
        # Также уведомляем того, кто назначил задачу
        if task.assigned_by and task.assigned_by != task.assigned_to:
            create_notification(
                user=task.assigned_by,
                title='Напоминание о назначенной задаче',
                message=f'Назначенная вами задача "{task.title}" должна быть выполнена до {task.due_date.strftime("%d.%m.%Y %H:%M")}',
                notification_type='reminder',
                related_object_id=task.id,
                related_object_type='task'
            )
        
        notifications_sent += 1
    
    return f"Отправлено {notifications_sent} напоминаний о задачах"

def generate_case_report(case_id):
    """Генерация отчета по делу"""
    try:
        case = Case.objects.get(id=case_id)
        
        report = {
            'case_info': {
                'number': case.case_number,
                'title': case.title,
                'client': case.client.user.get_full_name(),
                'lawyer': case.lawyer.get_full_name() if case.lawyer else 'Не назначен',
                'type': case.get_case_type_display(),
                'stage': case.get_stage_display(),
                'start_date': case.start_date.strftime('%d.%m.%Y'),
                'end_date': case.end_date.strftime('%d.%m.%Y') if case.end_date else 'В процессе',
                'budget': float(case.budget),
                'actual_cost': float(case.actual_cost),
                'success_probability': case.success_probability,
            },
            'communications': [],
            'documents': [],
            'tasks': [],
            'payments': [],
            'time_entries': [],
            'statistics': {}
        }
        
        # Коммуникации
        for comm in case.communications.all().order_by('-created_at'):
            report['communications'].append({
                'type': comm.get_communication_type_display(),
                'subject': comm.subject,
                'date': comm.created_at.strftime('%d.%m.%Y %H:%M'),
                'created_by': comm.created_by.get_full_name()
            })
        
        # Документы
        for doc in case.documents.all().order_by('-uploaded_at'):
            report['documents'].append({
                'title': doc.title,
                'category': doc.get_category_display(),
                'uploaded_at': doc.uploaded_at.strftime('%d.%m.%Y %H:%M'),
                'uploaded_by': doc.uploaded_by.get_full_name(),
                'is_signed': 'Да' if doc.is_signed else 'Нет'
            })
        
        # Задачи
        for task in case.tasks.all().order_by('-due_date'):
            report['tasks'].append({
                'title': task.title,
                'status': task.get_status_display(),
                'priority': task.get_priority_display(),
                'assigned_to': task.assigned_to.get_full_name(),
                'due_date': task.due_date.strftime('%d.%m.%Y %H:%M'),
                'completed_at': task.completed_at.strftime('%d.%m.%Y %H:%M') if task.completed_at else None,
                'estimated_hours': float(task.estimated_hours),
                'actual_hours': float(task.actual_hours),
            })
        
        # Платежи
        for payment in case.payments.all().order_by('-payment_date'):
            report['payments'].append({
                'amount': float(payment.amount),
                'type': payment.get_payment_type_display(),
                'payment_date': payment.payment_date.strftime('%d.%m.%Y'),
                'is_paid': 'Да' if payment.is_paid else 'Нет',
                'paid_date': payment.paid_date.strftime('%d.%m.%Y') if payment.paid_date else None,
            })
        
        # Учет времени
        for time_entry in case.time_entries.all().order_by('-start_time'):
            report['time_entries'].append({
                'lawyer': time_entry.lawyer.get_full_name(),
                'description': time_entry.description,
                'start_time': time_entry.start_time.strftime('%d.%m.%Y %H:%M'),
                'duration': float(time_entry.duration),
                'billable': 'Да' if time_entry.billable else 'Нет',
            })
        
        # Статистика
        total_paid = case.payments.filter(is_paid=True).aggregate(total=Sum('amount'))['total'] or 0
        total_hours = case.time_entries.aggregate(total=Sum('duration'))['total'] or 0
        
        report['statistics'] = {
            'total_paid': float(total_paid),
            'remaining_budget': float(case.budget - total_paid),
            'total_hours_spent': float(total_hours),
            'documents_count': len(report['documents']),
            'tasks_completed': case.tasks.filter(status='done').count(),
            'tasks_pending': case.tasks.filter(status__in=['todo', 'in_progress']).count(),
        }
        
        return report
    
    except Case.DoesNotExist:
        return None

def calculate_lawyer_bonus(lawyer_id, period_start, period_end):
    """Расчет бонуса для юриста на основе эффективности"""
    try:
        lawyer = CustomUser.objects.get(id=lawyer_id, role='lawyer')
        
        # Получаем дела юриста за период
        cases = Case.objects.filter(
            lawyer=lawyer,
            created_at__gte=period_start,
            created_at__lte=period_end
        )
        
        # Выручка от дел юриста
        revenue = Payment.objects.filter(
            case__lawyer=lawyer,
            is_paid=True,
            payment_date__gte=period_start,
            payment_date__lte=period_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Отработанные часы
        hours = TimeEntry.objects.filter(
            lawyer=lawyer,
            start_time__gte=period_start,
            start_time__lte=period_end
        ).aggregate(total=Sum('duration'))['total'] or 0
        
        # Процент успешных дел
        successful_cases = cases.filter(stage='closed').count()
        success_rate = (successful_cases / cases.count() * 100) if cases.count() > 0 else 0
        
        # Расчет бонуса
        base_bonus = 0
        efficiency = revenue / (hours * lawyer.hourly_rate) if hours > 0 and lawyer.hourly_rate > 0 else 0
        
        if efficiency > 1.5:  # Высокая эффективность
            base_bonus = revenue * 0.1  # 10% от выручки
        elif efficiency > 1.2:
            base_bonus = revenue * 0.07  # 7% от выручки
        elif efficiency > 1.0:
            base_bonus = revenue * 0.05  # 5% от выручки
        
        # Дополнительный бонус за высокий процент успешных дел
        success_bonus = 0
        if success_rate > 90:
            success_bonus = base_bonus * 0.5  # +50% к бонусу
        elif success_rate > 80:
            success_bonus = base_bonus * 0.3  # +30% к бонусу
        elif success_rate > 70:
            success_bonus = base_bonus * 0.1  # +10% к бонусу
        
        total_bonus = base_bonus + success_bonus
        
        return {
            'lawyer': lawyer.get_full_name(),
            'period': f'{period_start.strftime("%d.%m.%Y")} - {period_end.strftime("%d.%m.%Y")}',
            'revenue': round(revenue, 2),
            'hours': round(hours, 2),
            'efficiency': round(efficiency, 2),
            'success_rate': round(success_rate, 1),
            'base_bonus': round(base_bonus, 2),
            'success_bonus': round(success_bonus, 2),
            'total_bonus': round(total_bonus, 2),
        }
    
    except CustomUser.DoesNotExist:
        return None

def sync_calendar_with_external(user_id, service='google'):
    """Синхронизация календаря с внешними сервисами"""
    # Заглушка для интеграции с Google Calendar, Outlook и т.д.
    # В реальной реализации здесь будет API вызов
    
    user = CustomUser.objects.get(id=user_id)
    
    # Для примера, просто возвращаем статус
    return {
        'user': user.get_full_name(),
        'service': service,
        'status': 'not_implemented',
        'message': 'Функция синхронизации календаря находится в разработке',
        'last_sync': timezone.now().isoformat()
    }