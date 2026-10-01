from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import WorkerProfile
from .forms import FinancialAccountForm, ManualAdjustmentForm, MoneyTransferForm
from .models import FinancialAccount, MoneyTransfer
from .services import post_entry


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
