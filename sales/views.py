from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import WorkerProfile
from customers.models import Customer
from .forms import WorkerSaleForm
from .models import Sale


def get_or_create_customer_from_form(customer_name, customer_phone):
    customer_name = (customer_name or '').strip()
    customer_phone = (customer_phone or '').strip()

    if not customer_name and not customer_phone:
        return None

    customer = None

    if customer_phone:
        customer = Customer.objects.filter(phone=customer_phone).first()

    if customer:
        if customer_name and customer.name != customer_name:
            customer.name = customer_name
            customer.save()
        return customer

    if customer_name:
        customer = Customer.objects.filter(name=customer_name, phone__isnull=True).first()
        if customer:
            if customer_phone and not customer.phone:
                customer.phone = customer_phone
                customer.save()
            return customer

    return Customer.objects.create(
        name=customer_name or customer_phone,
        phone=customer_phone or None,
    )


def get_sales_redirect_name(profile):
    if profile.role == 'manager':
        return 'manager-sales-list'
    return 'worker-sales-list'


def can_access_sale(profile, sale):
    if profile.role == 'manager':
        return True
    return sale.worker_id == profile.id


@login_required
def worker_sale_create(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    if request.method == 'POST':
        form = WorkerSaleForm(request.POST, worker_profile=profile)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.worker = profile

            customer_name = form.cleaned_data.get('customer_name')
            customer_phone = form.cleaned_data.get('customer_phone')
            sale.customer = get_or_create_customer_from_form(customer_name, customer_phone)

            sale.save()
            return redirect('worker-sales-list')
    else:
        form = WorkerSaleForm(worker_profile=profile)

    return render(request, 'sales/worker_sale_form.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def worker_sales_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    sales = Sale.objects.filter(worker=profile).select_related(
        'customer',
        'product',
        'warehouse',
    ).order_by('-sale_date')

    context = {
        'profile': profile,
        'sales': sales,
    }
    return render(request, 'sales/worker_sales_list.html', context)


@login_required
def worker_sale_detail(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'product', 'warehouse', 'worker'),
        pk=pk,
    )

    if not can_access_sale(profile, sale):
        return redirect(get_sales_redirect_name(profile))

    context = {
        'profile': profile,
        'sale': sale,
    }
    return render(request, 'sales/worker_sale_detail.html', context)


@login_required
def sale_update(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'product', 'warehouse', 'worker'),
        pk=pk,
    )

    if not can_access_sale(profile, sale):
        return redirect(get_sales_redirect_name(profile))

    worker_profile_for_form = profile if profile.role == 'worker' else None

    if request.method == 'POST':
        form = WorkerSaleForm(request.POST, instance=sale, worker_profile=worker_profile_for_form)
        if form.is_valid():
            updated_sale = form.save(commit=False)

            customer_name = form.cleaned_data.get('customer_name')
            customer_phone = form.cleaned_data.get('customer_phone')
            updated_sale.customer = get_or_create_customer_from_form(customer_name, customer_phone)

            updated_sale.save()
            return redirect(get_sales_redirect_name(profile))
    else:
        form = WorkerSaleForm(instance=sale, worker_profile=worker_profile_for_form)

    return render(request, 'sales/sale_update_form.html', {
        'form': form,
        'profile': profile,
        'sale': sale,
    })


@login_required
def sale_delete(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'product', 'warehouse', 'worker'),
        pk=pk,
    )

    if not can_access_sale(profile, sale):
        return redirect(get_sales_redirect_name(profile))

    if request.method == 'POST':
        sale.delete()
        return redirect(get_sales_redirect_name(profile))

    return render(request, 'sales/sale_delete_confirm.html', {
        'profile': profile,
        'sale': sale,
    })