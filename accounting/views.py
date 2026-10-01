from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import WorkerProfile
from customers.models import Customer
from sales.models import Sale
from .forms import CustomerPaymentForm, FinancialAccountForm, ManualAdjustmentForm, MoneyTransferForm
from .models import CustomerPayment, FinancialAccount, MoneyTransfer
from .services import get_customer_deferred_balance, get_deferred_customer_balances, post_entry


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
    ).select_related('product').order_by('-sale_date')
    payments = CustomerPayment.objects.filter(customer=customer).select_related('account')

    return render(request, 'accounting/customer_statement.html', {
        'profile': profile,
        'customer': customer,
        'balance': balance,
        'sales': sales,
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
