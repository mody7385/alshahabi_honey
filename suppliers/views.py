from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import WorkerProfile
from .forms import SupplierForm, SupplierPaymentForm, SupplierPurchaseForm
from .models import Supplier, SupplierPayment, SupplierPurchase


def get_manager_profile(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()
    if not profile or profile.role != 'manager':
        return None
    return profile


@login_required
def supplier_list(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    suppliers = Supplier.objects.all()

    supplier_data = []
    for supplier in suppliers:
        total_purchases = supplier.purchases.aggregate(total=Sum('total_amount')).get('total') or 0
        total_payments = supplier.payments.aggregate(total=Sum('amount')).get('total') or 0
        balance = total_purchases - total_payments

        supplier_data.append({
            'supplier': supplier,
            'total_purchases': total_purchases,
            'total_payments': total_payments,
            'balance': balance,
        })

    return render(request, 'suppliers/supplier_list.html', {
        'profile': profile,
        'supplier_data': supplier_data,
    })


@login_required
def supplier_create(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('supplier-list')
    else:
        form = SupplierForm()

    return render(request, 'suppliers/supplier_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة مورد',
        'submit_label': 'حفظ المورد',
    })


@login_required
def supplier_update(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    supplier = get_object_or_404(Supplier, pk=pk)

    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('supplier-list')
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'suppliers/supplier_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل مورد',
        'submit_label': 'حفظ التعديلات',
    })


@login_required
def supplier_detail(request, pk):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    supplier = get_object_or_404(Supplier, pk=pk)

    purchases = supplier.purchases.select_related('product').all()
    payments = supplier.payments.all()

    total_purchases = purchases.aggregate(total=Sum('total_amount')).get('total') or 0
    total_payments = payments.aggregate(total=Sum('amount')).get('total') or 0
    balance = total_purchases - total_payments

    return render(request, 'suppliers/supplier_detail.html', {
        'profile': profile,
        'supplier': supplier,
        'purchases': purchases,
        'payments': payments,
        'total_purchases': total_purchases,
        'total_payments': total_payments,
        'balance': balance,
    })


@login_required
def supplier_purchase_create(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SupplierPurchaseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('supplier-list')
    else:
        form = SupplierPurchaseForm()

    return render(request, 'suppliers/supplier_purchase_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة شراء من مورد',
        'submit_label': 'حفظ عملية الشراء',
    })


@login_required
def supplier_payment_create(request):
    profile = get_manager_profile(request)
    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('supplier-list')
    else:
        form = SupplierPaymentForm()

    return render(request, 'suppliers/supplier_payment_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة سداد لمورد',
        'submit_label': 'حفظ السداد',
    })