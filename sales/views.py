from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import formset_factory
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import WorkerProfile
from customers.models import Customer
from .forms import SaleHeaderForm, SaleLineForm, WorkerSaleForm
from .models import Sale, SaleBatch


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

    return Customer.objects.create(name=customer_name or customer_phone, phone=customer_phone or None)


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

    SaleLineFormSet = formset_factory(SaleLineForm, extra=6, min_num=1, validate_min=False)

    if request.method == 'POST':
        header_form = SaleHeaderForm(request.POST)
        formset = SaleLineFormSet(request.POST, form_kwargs={'worker_profile': profile})

        if header_form.is_valid() and formset.is_valid():
            line_forms = [
                form for form in formset
                if form.cleaned_data and not form.cleaned_data.get('DELETE') and not form.is_empty()
            ]

            if not line_forms:
                formset.non_form_errors()
            else:
                customer = get_or_create_customer_from_form(
                    header_form.cleaned_data.get('customer_name'),
                    header_form.cleaned_data.get('customer_phone'),
                )

                with transaction.atomic():
                    batch = SaleBatch.objects.create(
                        worker=profile,
                        warehouse=profile.warehouse,
                        customer=customer,
                        payment_type=header_form.cleaned_data['payment_type'],
                        notes=header_form.cleaned_data.get('notes'),
                    )

                    for line_form in line_forms:
                        sale = line_form.save(commit=False)
                        sale.batch = batch
                        sale.worker = profile
                        sale.warehouse = profile.warehouse
                        sale.customer = customer
                        sale.payment_type = batch.payment_type
                        sale.notes = batch.notes
                        sale.save()

                return redirect('worker-sales-list')
    else:
        header_form = SaleHeaderForm()
        formset = SaleLineFormSet(form_kwargs={'worker_profile': profile})

    return render(request, 'sales/worker_sale_form.html', {
        'header_form': header_form,
        'formset': formset,
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
        'batch',
    ).order_by('-sale_date')

    return render(request, 'sales/worker_sales_list.html', {
        'profile': profile,
        'sales': sales,
    })


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

    return render(request, 'sales/worker_sale_detail.html', {
        'profile': profile,
        'sale': sale,
    })


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
            customer = get_or_create_customer_from_form(
                form.cleaned_data.get('customer_name'),
                form.cleaned_data.get('customer_phone'),
            )
            updated_sale.customer = customer
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
