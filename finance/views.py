from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import WorkerProfile
from sales.models import Sale
from .forms import ManagerOperatingExpenseForm, ManagerWorkerTransactionForm
from .models import OperatingExpense


@login_required
def manager_add_worker_transaction(request, worker_pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    worker = get_object_or_404(
        WorkerProfile.objects.select_related('warehouse', 'user'),
        pk=worker_pk,
        role='worker'
    )

    if request.method == 'POST':
        form = ManagerWorkerTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.worker = worker
            transaction.sale = None
            transaction.save()
            return redirect('manager-worker-account-detail', pk=worker.pk)
    else:
        form = ManagerWorkerTransactionForm()

    context = {
        'profile': profile,
        'worker': worker,
        'form': form,
    }
    return render(request, 'finance/manager_add_worker_transaction.html', context)


def get_period_range(period):
    today = timezone.localdate()

    if period == 'today':
        return today, today, 'اليوم'

    if period == 'week':
        start = today - timedelta(days=today.weekday())
        return start, today, 'هذا الأسبوع'

    if period == 'year':
        start = today.replace(month=1, day=1)
        return start, today, 'هذه السنة'

    start = today.replace(day=1)
    return start, today, 'هذا الشهر'


@login_required
def manager_profit_center(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    period = request.GET.get('period', 'month')
    start_date, end_date, period_label = get_period_range(period)

    gross_profit = Sale.objects.filter(
        sale_date__date__range=[start_date, end_date]
    ).aggregate(total=Sum('profit_amount')).get('total') or 0

    expenses_qs = OperatingExpense.objects.filter(
        expense_date__range=[start_date, end_date]
    ).order_by('-expense_date', '-created_at')

    total_expenses = expenses_qs.aggregate(total=Sum('amount')).get('total') or 0
    net_profit = gross_profit - total_expenses

    context = {
        'profile': profile,
        'period': period,
        'period_label': period_label,
        'start_date': start_date,
        'end_date': end_date,
        'gross_profit': gross_profit,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'expenses': expenses_qs,
    }
    return render(request, 'finance/manager_profit_center.html', context)


@login_required
def manager_operating_expense_create(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ManagerOperatingExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manager-profit-center')
    else:
        form = ManagerOperatingExpenseForm()

    return render(request, 'finance/operating_expense_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة مصروف تشغيلي',
        'submit_label': 'حفظ المصروف',
    })


@login_required
def manager_operating_expense_update(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    expense = get_object_or_404(OperatingExpense, pk=pk)

    if request.method == 'POST':
        form = ManagerOperatingExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('manager-profit-center')
    else:
        form = ManagerOperatingExpenseForm(instance=expense)

    return render(request, 'finance/operating_expense_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل مصروف تشغيلي',
        'submit_label': 'حفظ التعديلات',
    })


@login_required
def manager_operating_expense_delete(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    expense = get_object_or_404(OperatingExpense, pk=pk)

    if request.method == 'POST':
        expense.delete()
        return redirect('manager-profit-center')

    return render(request, 'finance/operating_expense_delete_confirm.html', {
        'profile': profile,
        'expense': expense,
    })