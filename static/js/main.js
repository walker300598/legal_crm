$(document).ready(function() {
    // Initialize Select2
    $('.select2').select2({
        theme: 'bootstrap-5',
        placeholder: 'Выберите значение',
        allowClear: true
    });
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        $('.alert').fadeTo(500, 0).slideUp(500, function() {
            $(this).remove();
        });
    }, 5000);
    
    // File upload preview
    $('input[type="file"]').on('change', function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).siblings('.custom-file-label').addClass("selected").html(fileName);
    });
    
    // Task status update
    $('.task-status-select').on('change', function() {
        var taskId = $(this).data('task-id');
        var newStatus = $(this).val();
        
        $.ajax({
            url: `/api/tasks/${taskId}/update-status/`,
            method: 'POST',
            data: {
                'status': newStatus,
                'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function(response) {
                if (response.success) {
                    showToast('Статус задачи обновлен', 'success');
                    
                    // Update badge
                    var badge = $(`#task-badge-${taskId}`);
                    badge.removeClass().addClass('badge');
                    
                    switch(newStatus) {
                        case 'todo':
                            badge.addClass('badge-new').text('К выполнению');
                            break;
                        case 'in_progress':
                            badge.addClass('badge-in-progress').text('В работе');
                            break;
                        case 'done':
                            badge.addClass('badge-completed').text('Выполнено');
                            break;
                    }
                }
            },
            error: function() {
                showToast('Ошибка при обновлении статуса', 'error');
            }
        });
    });
    
    // Time tracking
    var timeTrackingInterval;
    var startTime;
    
    $('.start-tracking').on('click', function() {
        var caseId = $(this).data('case-id');
        startTime = new Date();
        
        $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> В процессе...');
        $('.stop-tracking').prop('disabled', false);
        
        timeTrackingInterval = setInterval(function() {
            var currentTime = new Date();
            var diff = Math.floor((currentTime - startTime) / 1000);
            var hours = Math.floor(diff / 3600);
            var minutes = Math.floor((diff % 3600) / 60);
            var seconds = diff % 60;
            
            $('.tracking-time').text(
                String(hours).padStart(2, '0') + ':' +
                String(minutes).padStart(2, '0') + ':' +
                String(seconds).padStart(2, '0')
            );
        }, 1000);
    });
    
    $('.stop-tracking').on('click', function() {
        clearInterval(timeTrackingInterval);
        var endTime = new Date();
        var duration = (endTime - startTime) / (1000 * 60 * 60); // in hours
        
        // Save time entry
        $.ajax({
            url: '/api/time-entries/create/',
            method: 'POST',
            data: {
                'case_id': $(this).data('case-id'),
                'duration': duration.toFixed(2),
                'description': $('.tracking-description').val(),
                'csrfmiddlewaretoken': $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function(response) {
                showToast('Время успешно сохранено', 'success');
                $('.start-tracking').prop('disabled', false).html('<i class="fas fa-play"></i> Начать отсчет');
                $('.stop-tracking').prop('disabled', true);
                $('.tracking-time').text('00:00:00');
                
                // Reload time entries list
                loadTimeEntries();
            }
        });
    });
    
    // Search functionality
    var searchTimeout;
    $('.search-input').on('keyup', function() {
        clearTimeout(searchTimeout);
        var searchTerm = $(this).val();
        
        searchTimeout = setTimeout(function() {
            if (searchTerm.length >= 2 || searchTerm.length === 0) {
                performSearch(searchTerm);
            }
        }, 500);
    });
    
    // Analytics date range picker
    $('.date-range-picker').on('apply.daterangepicker', function(ev, picker) {
        $(this).val(
            picker.startDate.format('DD.MM.YYYY') + ' - ' + 
            picker.endDate.format('DD.MM.YYYY')
        );
        
        // Reload analytics with new date range
        loadAnalytics(picker.startDate, picker.endDate);
    });
});

// Toast notifications
function showToast(message, type = 'info') {
    var toastHtml = `
        <div class="toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    $('.toast-container').append(toastHtml);
    $('.toast').toast('show');
}

// Load time entries
function loadTimeEntries() {
    $.get('/api/time-entries/', function(data) {
        var html = '';
        data.forEach(function(entry) {
            html += `
                <div class="timeline-item">
                    <h6 class="mb-1">${entry.description}</h6>
                    <small class="text-muted">
                        ${entry.duration} ч. • ${entry.lawyer_name}
                    </small>
                </div>
            `;
        });
        $('#time-entries-list').html(html);
    });
}

// Load analytics
function loadAnalytics(startDate, endDate) {
    $.get('/api/analytics/', {
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD')
    }, function(data) {
        updateAnalyticsCharts(data);
    });
}

// Update analytics charts
function updateAnalyticsCharts(data) {
    // Update revenue chart
    if (window.revenueChart) {
        window.revenueChart.data.labels = data.months;
        window.revenueChart.data.datasets[0].data = data.revenue;
        window.revenueChart.update();
    }
    
    // Update case distribution chart
    if (window.caseChart) {
        window.caseChart.data.datasets[0].data = data.case_distribution.values;
        window.caseChart.update();
    }
}

// Initialize charts
function initializeCharts() {
    // Revenue chart
    var revenueCtx = document.getElementById('revenueChart');
    if (revenueCtx) {
        window.revenueChart = new Chart(revenueCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Доход',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('ru-RU') + ' ₽';
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                }
            }
        });
    }
    
    // Case distribution chart
    var caseCtx = document.getElementById('caseDistributionChart');
    if (caseCtx) {
        window.caseChart = new Chart(caseCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#3b82f6',
                        '#1d4ed8',
                        '#60a5fa',
                        '#93c5fd',
                        '#bfdbfe'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right'
                    }
                }
            }
        });
    }
}

// Initialize when page loads
$(window).on('load', function() {
    initializeCharts();
    loadTimeEntries();
});