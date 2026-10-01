from django.contrib.auth.decorators import login_required
from datetime import date, timedelta
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import WorkerProfile
from customers.models import Customer
from sales.models import Sale, SaleBatch
from .forms import CustomerPaymentForm, FinancialAccountForm, ManualAdjustmentForm, MoneyTransferForm
from .models import CustomerPayment, FinancialAccount, LedgerEntry, MoneyTransfer
from .services import (
    get_account_balances,
    get_cashflow_summary,
    get_comprehensive_report,
    get_customer_deferred_balance,
    get_deferred_customer_balances,
    get_personal_expense_summary,
    get_profit_summary,
    get_worker_balances,
    post_entry,
)


def get_manager_profile(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()
    if not profile or profile.role != WorkerProfile.ROLE_MANAGER:
        return None
    return profile


@login_required
def account_list(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    accounts = FinancialAccount.objects.all()
    return render(request, 'accounting/account_list.html', {
        'profile': profile,
        'accounts': accounts,
    })


@login_required
def account_create(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = FinancialAccountForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('accounting-account-list')
    else:
        form = FinancialAccountForm()

    return render(request, 'accounting/account_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة حساب مالي',
        'submit_label': 'حفظ الحساب',
    })


@login_required
def account_update(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    account = get_object_or_404(FinancialAccount, pk=pk)

    if request.method == 'POST':
        form = FinancialAccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            return redirect('accounting-account-detail', pk=account.pk)
    else:
        form = FinancialAccountForm(instance=account)

    return render(request, 'accounting/account_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل حساب مالي',
        'submit_label': 'حفظ التعديل',
    })


@login_required
def account_detail(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    account = get_object_or_404(FinancialAccount, pk=pk)
    entries = account.ledger_entries.filter(is_reversed=False)
    return render(request, 'accounting/account_detail.html', {
        'profile': profile,
        'account': account,
        'entries': entries,
    })


@login_required
def manual_adjustment(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ManualAdjustmentForm(request.POST)
        if form.is_valid():
            account = form.cleaned_data['account']
            entry = post_entry(
                account=account,
                amount=form.cleaned_data['amount'],
                direction=form.cleaned_data['direction'],
                category=form.cleaned_data['category'],
                description=form.cleaned_data['description'],
                source_type='manual_adjustment',
                source_id=0,
            )
            entry.source_id = entry.pk
            entry.save(update_fields=['source_id'])
            return redirect('accounting-account-detail', pk=account.pk)
    else:
        form = ManualAdjustmentForm()

    return render(request, 'accounting/manual_adjustment_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة حركة مالية',
        'submit_label': 'حفظ الحركة',
    })


@login_required
def transfer_create(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = MoneyTransferForm(request.POST)
        if form.is_valid():
            transfer = form.save()
            return redirect('accounting-account-detail', pk=transfer.source_account_id)
    else:
        form = MoneyTransferForm()

    return render(request, 'accounting/transfer_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تحويل بين الحسابات',
        'submit_label': 'حفظ التحويل',
    })


@login_required
def transfer_update(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    transfer = get_object_or_404(MoneyTransfer, pk=pk)

    if request.method == 'POST':
        form = MoneyTransferForm(request.POST, instance=transfer)
        if form.is_valid():
            transfer = form.save()
            return redirect('accounting-account-detail', pk=transfer.source_account_id)
    else:
        form = MoneyTransferForm(instance=transfer)

    return render(request, 'accounting/transfer_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل تحويل',
        'submit_label': 'حفظ التعديل',
    })


@login_required
def transfer_delete(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    transfer = get_object_or_404(MoneyTransfer, pk=pk)
    source_account_id = transfer.source_account_id

    if request.method == 'POST':
        transfer.delete()
        return redirect('accounting-account-detail', pk=source_account_id)

    return render(request, 'accounting/transfer_delete_confirm.html', {
        'profile': profile,
        'transfer': transfer,
    })


@login_required
def manual_adjustment_void(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    entry = get_object_or_404(
        LedgerEntry,
        pk=pk,
        source_type='manual_adjustment',
        is_reversed=False,
    )
    account_id = entry.account_id

    if request.method == 'POST':
        from .services import reverse_entries

        reverse_entries('manual_adjustment', entry.source_id)
        return redirect('accounting-account-detail', pk=account_id)

    return render(request, 'accounting/manual_adjustment_void_confirm.html', {
        'profile': profile,
        'entry': entry,
    })


@login_required
def deferred_customer_list(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    balances = get_deferred_customer_balances()
    return render(request, 'accounting/deferred_customer_list.html', {
        'profile': profile,
        'balances': balances,
    })


@login_required
def customer_statement(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    customer = get_object_or_404(Customer, pk=pk)
    balance = get_customer_deferred_balance(customer)
    sales = Sale.objects.filter(
        customer=customer,
        payment_type='deferred',
        is_new_accounting_sale=True,
    ).filter(
        Q(batch__isnull=True) | Q(batch__uses_batch_accounting=False),
    ).select_related('product').order_by('-sale_date')
    batch_deferred_sales = SaleBatch.objects.filter(
        customer=customer,
        uses_batch_accounting=True,
        deferred_amount__gt=0,
    ).order_by('-created_at')
    payments = CustomerPayment.objects.filter(customer=customer).select_related('account')

    return render(request, 'accounting/customer_statement.html', {
        'profile': profile,
        'customer': customer,
        'balance': balance,
        'sales': sales,
        'batch_deferred_sales': batch_deferred_sales,
        'payments': payments,
    })


@login_required
def customer_payment_create(request, customer_pk=None):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    customer = get_object_or_404(Customer, pk=customer_pk) if customer_pk else None

    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST, customer=customer)
        if form.is_valid():
            payment = form.save(commit=False)
            if customer:
                payment.customer = customer
            payment.save()
            return redirect('accounting-customer-statement', pk=payment.customer_id)
    else:
        form = CustomerPaymentForm(customer=customer)

    return render(request, 'accounting/customer_payment_form.html', {
        'profile': profile,
        'form': form,
        'customer': customer,
        'page_title': 'تسجيل سداد عميل',
        'submit_label': 'حفظ السداد',
    })


@login_required
def customer_payment_update(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    payment = get_object_or_404(CustomerPayment, pk=pk)

    if request.method == 'POST':
        form = CustomerPaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            return redirect('accounting-customer-statement', pk=payment.customer_id)
    else:
        form = CustomerPaymentForm(instance=payment)

    return render(request, 'accounting/customer_payment_form.html', {
        'profile': profile,
        'form': form,
        'customer': payment.customer,
        'page_title': 'تعديل سداد عميل',
        'submit_label': 'حفظ التعديل',
    })


@login_required
def customer_payment_delete(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    payment = get_object_or_404(CustomerPayment, pk=pk)
    customer_id = payment.customer_id
    if request.method == 'POST':
        payment.delete()
        return redirect('accounting-customer-statement', pk=customer_id)

    return render(request, 'accounting/customer_payment_delete_confirm.html', {
        'profile': profile,
        'payment': payment,
    })


def _report_period(request):
    today = timezone.localdate()
    period = request.GET.get('period', 'month')
    start_value = request.GET.get('start_date')
    end_value = request.GET.get('end_date')
    try:
        if start_value:
            start_date = date.fromisoformat(start_value)
        elif period == 'day':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
        else:
            start_date = today.replace(day=1)
        end_date = date.fromisoformat(end_value) if end_value else today
    except ValueError:
        start_date = today.replace(day=1)
        end_date = today
    return start_date, end_date


@login_required
def reports_dashboard(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    start_date, end_date = _report_period(request)
    return render(request, 'accounting/reports_dashboard.html', {
        'profile': profile,
        'start_date': start_date,
        'end_date': end_date,
        'profit_summary': get_profit_summary(start_date, end_date),
        'account_balances': get_account_balances(),
        'worker_balances': get_worker_balances(),
    })


@login_required
def account_balances_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    return render(request, 'accounting/account_balances_report.html', {
        'profile': profile,
        'balances': get_account_balances(),
    })


@login_required
def profit_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    start_date, end_date = _report_period(request)
    return render(request, 'accounting/profit_report.html', {
        'profile': profile,
        'start_date': start_date,
        'end_date': end_date,
        'summary': get_profit_summary(start_date, end_date),
    })


@login_required
def cashflow_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    start_date, end_date = _report_period(request)
    return render(request, 'accounting/cashflow_report.html', {
        'profile': profile,
        'start_date': start_date,
        'end_date': end_date,
        'summary': get_cashflow_summary(start_date, end_date),
    })


@login_required
def comprehensive_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    start_date, end_date = _report_period(request)
    return render(request, 'accounting/comprehensive_report.html', {
        'profile': profile,
        'start_date': start_date,
        'end_date': end_date,
        'period': request.GET.get('period', 'month'),
        'summary': get_comprehensive_report(start_date, end_date),
    })


@login_required
def worker_balances_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    return render(request, 'accounting/worker_balances_report.html', {
        'profile': profile,
        'balances': get_worker_balances(),
    })


@login_required
def personal_expenses_report(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    start_date, end_date = _report_period(request)
    return render(request, 'accounting/personal_expenses_report.html', {
        'profile': profile,
        'start_date': start_date,
        'end_date': end_date,
        'summary': get_personal_expense_summary(start_date, end_date),
    })
