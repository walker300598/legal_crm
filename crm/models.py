from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('lawyer', 'Юрист'),
        ('client', 'Клиент'),
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Client(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('active', 'Активный'),
        ('closed', 'Закрыт'),
        ('lost', 'Утерян'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='client_profile')
    company_name = models.CharField(max_length=200, blank=True)
    inn = models.CharField(max_length=12, blank=True)
    address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    source = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='clients_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Case(models.Model):
    STAGE_CHOICES = (
        ('consultation', 'Консультация'),
        ('analysis', 'Анализ документов'),
        ('negotiation', 'Переговоры'),
        ('lawsuit', 'Подача иска'),
        ('court', 'Судебное заседание'),
        ('decision', 'Решение суда'),
        ('execution', 'Исполнительное производство'),
        ('closed', 'Закрыто'),
    )
    
    TYPE_CHOICES = (
        ('civil', 'Гражданское дело'),
        ('criminal', 'Уголовное дело'),
        ('administrative', 'Административное дело'),
        ('arbitration', 'Арбитражное дело'),
        ('consultation', 'Консультация'),
    )
    
    case_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='cases')
    lawyer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='cases')
    case_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default='consultation')
    description = models.TextField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    success_probability = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=50
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Task(models.Model):
    PRIORITY_CHOICES = (
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    )
    
    STATUS_CHOICES = (
        ('todo', 'К выполнению'),
        ('in_progress', 'В работе'),
        ('review', 'На проверке'),
        ('done', 'Выполнено'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tasks')
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    due_date = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class Communication(models.Model):
    TYPE_CHOICES = (
        ('email', 'Email'),
        ('phone', 'Телефонный звонок'),
        ('meeting', 'Встреча'),
        ('message', 'Сообщение'),
        ('document', 'Документ'),
    )
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='communications')
    communication_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=200)
    content = models.TextField()
    participants = models.ManyToManyField(CustomUser, related_name='communications')
    scheduled_for = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(help_text="Длительность в минутах", null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_communications')
    created_at = models.DateTimeField(auto_now_add=True)

class Document(models.Model):
    CATEGORY_CHOICES = (
        ('contract', 'Договор'),
        ('lawsuit', 'Исковое заявление'),
        ('protocol', 'Протокол'),
        ('expertise', 'Экспертиза'),
        ('decision', 'Решение суда'),
        ('other', 'Другое'),
    )
    
    document_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(default=1)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)

class CalendarEvent(models.Model):
    EVENT_TYPE_CHOICES = (
        ('meeting', 'Встреча'),
        ('court_hearing', 'Судебное заседание'),
        ('deadline', 'Дедлайн'),
        ('reminder', 'Напоминание'),
        ('task', 'Задача'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='calendar_events', null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='calendar_event')
    participants = models.ManyToManyField(CustomUser, related_name='calendar_events')
    location = models.CharField(max_length=200, blank=True)
    is_all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=7, default='#3788d8')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class TimeEntry(models.Model):
    lawyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='time_entries')
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='time_entries')
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True, related_name='time_entries')
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    billable = models.BooleanField(default=True)
    billed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = (
        ('advance', 'Аванс'),
        ('installment', 'Рассрочка'),
        ('final', 'Финальный платеж'),
        ('additional', 'Дополнительный'),
    )
    
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    invoice_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Analytics(models.Model):
    period = models.CharField(max_length=20)  # 'daily', 'weekly', 'monthly', 'yearly'
    period_date = models.DateField()
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    active_cases = models.IntegerField(default=0)
    new_clients = models.IntegerField(default=0)
    lawyer_performance = models.JSONField(default=dict)  # Статистика по юристам
    case_type_distribution = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['period', 'period_date']

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('info', 'Информация'),
        ('warning', 'Предупреждение'),
        ('success', 'Успех'),
        ('error', 'Ошибка'),
        ('reminder', 'Напоминание'),
        ('calendar', 'Календарь'),
        ('task', 'Задача'),
        ('case', 'Дело'),
        ('payment', 'Платеж'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    related_object_id = models.IntegerField(null=True, blank=True)
    related_object_type = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
        ]
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"