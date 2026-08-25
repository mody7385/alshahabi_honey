from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from customers.models import Customer
from finance.models import WorkerAccountTransaction
from decimal import Decimal
from inventory.forms import ManagerInventoryAdjustForm
from inventory.models import Inventory
from products.models import Product
from sales.models import Sale
from warehouses.models import Warehouse
from .models import WorkerProfile
from products.forms import ManagerProductForm
from .forms import ManagerUserForm
from warehouses.forms import ManagerWarehouseForm


@login_required
def dashboard(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return render(request, 'accounts/dashboard.html', {'profile': None})

    if profile.role == 'manager':
        return redirect('manager-dashboard')

    return render(request, 'accounts/dashboard.html', {'profile': profile})


@login_required
def worker_account_summary(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile:
        return redirect('dashboard')

    return render(request, 'accounts/worker_account_summary.html', {'profile': profile})


@login_required
def manager_dashboard(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    total_workers = WorkerProfile.objects.filter(role='worker', is_active=True).count()
    total_warehouses = Warehouse.objects.filter(is_active=True).count()
    total_products = Product.objects.filter(is_active=True).count()
    total_profit = Sale.objects.aggregate(total=Sum('profit_amount')).get('total') or 0
    total_sales_amount = Sale.objects.aggregate(total=Sum('total_amount')).get('total') or 0
    total_cash_sales = Sale.objects.filter(payment_type='cash').aggregate(total=Sum('total_amount')).get('total') or 0
    total_transfer_sales = Sale.objects.filter(payment_type='transfer').aggregate(total=Sum('total_amount')).get('total') or 0
    total_deferred_sales = Sale.objects.filter(payment_type='deferred').aggregate(total=Sum('total_amount')).get('total') or 0

    total_worker_cash = WorkerAccountTransaction.objects.filter(
        transaction_type='sale_cash'
    ).aggregate(total=Sum('amount')).get('total') or 0

    context = {
        'profile': profile,
        'total_workers': total_workers,
        'total_warehouses': total_warehouses,
        'total_profit': total_profit,
        'total_products': total_products,
        'total_sales_amount': total_sales_amount,
        'total_cash_sales': total_cash_sales,
        'total_transfer_sales': total_transfer_sales,
        'total_deferred_sales': total_deferred_sales,
        'total_worker_cash': total_worker_cash,
    }
    return render(request, 'accounts/manager_dashboard.html', context)


@login_required
def manager_customers_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    customers = Customer.objects.all().order_by('-created_at')

    return render(request, 'accounts/manager_customers_list.html', {
        'profile': profile,
        'customers': customers,
    })


@login_required
def manager_sales_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    today = timezone.localdate()
    month_value = request.GET.get('month') or today.strftime('%Y-%m')
    payment_type = request.GET.get('payment_type', '')

    try:
        year, month = [int(part) for part in month_value.split('-')]
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
    except (TypeError, ValueError):
        month_value = today.strftime('%Y-%m')
        start_date = today.replace(day=1)
        end_date = date(today.year + 1, 1, 1) if today.month == 12 else date(today.year, today.month + 1, 1)

    sales = Sale.objects.filter(
        sale_date__date__gte=start_date,
        sale_date__date__lt=end_date,
    ).select_related(
        'worker',
        'customer',
        'product',
        'warehouse',
    ).order_by('-sale_date')

    if payment_type:
        sales = sales.filter(payment_type=payment_type)

    return render(request, 'accounts/manager_sales_list.html', {
        'profile': profile,
        'sales': sales,
        'month_value': month_value,
        'payment_type': payment_type,
        'total_sales_amount': sales.aggregate(total=Sum('total_amount')).get('total') or 0,
        'total_profit_amount': sales.aggregate(total=Sum('profit_amount')).get('total') or 0,
    })


@login_required
def manager_worker_accounts_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    workers = WorkerProfile.objects.filter(
        role='worker',
        is_active=True
    ).select_related('warehouse', 'user').order_by('full_name')

    return render(request, 'accounts/manager_worker_accounts_list.html', {
        'profile': profile,
        'workers': workers,
    })


@login_required
def manager_worker_account_detail(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    worker = WorkerProfile.objects.select_related('warehouse', 'user').filter(
        pk=pk,
        role='worker'
    ).first()

    if not worker:
        return redirect('manager-worker-accounts-list')

    transactions = worker.workeraccounttransaction_set.select_related('sale').order_by('-created_at')

    return render(request, 'accounts/manager_worker_account_detail.html', {
        'profile': profile,
        'worker': worker,
        'transactions': transactions,
    })


@login_required
def manager_warehouses_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    warehouses = Warehouse.objects.all().order_by('name')

    return render(request, 'accounts/manager_warehouses_list.html', {
        'profile': profile,
        'warehouses': warehouses,
    })


@login_required
def manager_reports(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    total_sales_amount = Sale.objects.aggregate(total=Sum('total_amount')).get('total') or 0
    total_cash_sales = Sale.objects.filter(payment_type='cash').aggregate(total=Sum('total_amount')).get('total') or 0
    total_transfer_sales = Sale.objects.filter(payment_type='transfer').aggregate(total=Sum('total_amount')).get('total') or 0
    total_deferred_sales = Sale.objects.filter(payment_type='deferred').aggregate(total=Sum('total_amount')).get('total') or 0

    top_workers = (
        Sale.objects
        .values('worker__full_name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id')
        )
        .order_by('-total_sales')[:5]
    )

    top_products = (
        Sale.objects
        .values('product__name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id'),
            total_dabba=Sum('quantity_dabba'),
            total_kg=Sum('quantity_kg')
        )
        .order_by('-total_sales')[:5]
    )

    return render(request, 'accounts/manager_reports.html', {
        'profile': profile,
        'total_sales_amount': total_sales_amount,
        'total_cash_sales': total_cash_sales,
        'total_transfer_sales': total_transfer_sales,
        'total_deferred_sales': total_deferred_sales,
        'top_workers': top_workers,
        'top_products': top_products,
    })
@login_required
def manager_products_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    show_inactive = request.GET.get('show_inactive') == '1'
    products = Product.objects.select_related('warehouse').order_by('warehouse__name', 'name')
    if not show_inactive:
        products = products.filter(is_active=True)

    return render(request, 'accounts/manager_products_list.html', {
        'profile': profile,
        'products': products,
        'show_inactive': show_inactive,
    })


@login_required
def manager_inventory_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    for product in Product.objects.filter(is_active=True):
        Inventory.objects.get_or_create(product=product)

    inventory_items = Inventory.objects.select_related(
        'product',
        'product__warehouse',
    ).filter(
        product__is_active=True,
    ).order_by('product__warehouse__name', 'product__name')
    total_inventory_capital = sum((item.capital_value() for item in inventory_items), Decimal('0'))

    return render(request, 'accounts/manager_inventory_list.html', {
        'profile': profile,
        'inventory_items': inventory_items,
        'total_inventory_capital': total_inventory_capital,
    })
@login_required
def manager_reports(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    total_sales_amount = Sale.objects.aggregate(total=Sum('total_amount')).get('total') or 0
    total_cash_sales = Sale.objects.filter(payment_type='cash').aggregate(total=Sum('total_amount')).get('total') or 0
    total_transfer_sales = Sale.objects.filter(payment_type='transfer').aggregate(total=Sum('total_amount')).get('total') or 0
    total_deferred_sales = Sale.objects.filter(payment_type='deferred').aggregate(total=Sum('total_amount')).get('total') or 0

    top_workers = (
        Sale.objects
        .values('worker__full_name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id')
        )
        .order_by('-total_sales')[:5]
    )

    top_products = (
        Sale.objects
        .values('product__name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id'),
            total_dabba=Sum('quantity_dabba'),
            total_kg=Sum('quantity_kg')
        )
        .order_by('-total_sales')[:5]
    )

    return render(request, 'accounts/manager_reports.html', {
        'profile': profile,
        'total_sales_amount': total_sales_amount,
        'total_cash_sales': total_cash_sales,
        'total_transfer_sales': total_transfer_sales,
        'total_deferred_sales': total_deferred_sales,
        'top_workers': top_workers,
        'top_products': top_products,
    })
@login_required
def manager_reports(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    total_sales_amount = Sale.objects.aggregate(total=Sum('total_amount')).get('total') or 0
    total_cash_sales = Sale.objects.filter(payment_type='cash').aggregate(total=Sum('total_amount')).get('total') or 0
    total_transfer_sales = Sale.objects.filter(payment_type='transfer').aggregate(total=Sum('total_amount')).get('total') or 0
    total_deferred_sales = Sale.objects.filter(payment_type='deferred').aggregate(total=Sum('total_amount')).get('total') or 0

    top_workers = (
        Sale.objects
        .values('worker__full_name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id')
        )
        .order_by('-total_sales')[:5]
    )

    top_products = (
        Sale.objects
        .values('product__name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id'),
            total_dabba=Sum('quantity_dabba'),
            total_kg=Sum('quantity_kg')
        )
        .order_by('-total_sales')[:5]
    )

    return render(request, 'accounts/manager_reports.html', {
        'profile': profile,
        'total_sales_amount': total_sales_amount,
        'total_cash_sales': total_cash_sales,
        'total_transfer_sales': total_transfer_sales,
        'total_deferred_sales': total_deferred_sales,
        'top_workers': top_workers,
        'top_products': top_products,
    })
@login_required
def manager_reports(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    total_sales_amount = Sale.objects.aggregate(total=Sum('total_amount')).get('total') or 0
    total_cash_sales = Sale.objects.filter(payment_type='cash').aggregate(total=Sum('total_amount')).get('total') or 0
    total_transfer_sales = Sale.objects.filter(payment_type='transfer').aggregate(total=Sum('total_amount')).get('total') or 0
    total_deferred_sales = Sale.objects.filter(payment_type='deferred').aggregate(total=Sum('total_amount')).get('total') or 0

    top_workers = (
        Sale.objects
        .values('worker__full_name')
        .annotate(
            total_sales=Sum('total_amount'),
            sales_count=Count('id')
        )
        .order_by('-total_sales')[:5]
    )

    product_sales_report = []
    for product in Product.objects.filter(is_active=True).select_related('warehouse').order_by('warehouse__name', 'name'):
        product_sales = Sale.objects.filter(product=product).aggregate(
            sales_count=Count('id'),
            total_dabba=Sum('quantity_dabba'),
            total_kg=Sum('quantity_kg'),
            total_sales=Sum('total_amount'),
        )
        product_sales_report.append({
            'product': product,
            'sales_count': product_sales.get('sales_count') or 0,
            'total_dabba': product_sales.get('total_dabba') or 0,
            'total_kg': product_sales.get('total_kg') or 0,
            'total_sales': product_sales.get('total_sales') or 0,
        })

    return render(request, 'accounts/manager_reports.html', {
        'profile': profile,
        'total_sales_amount': total_sales_amount,
        'total_cash_sales': total_cash_sales,
        'total_transfer_sales': total_transfer_sales,
        'total_deferred_sales': total_deferred_sales,
        'top_workers': top_workers,
        'product_sales_report': product_sales_report,
    })


@login_required
def manager_product_create(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ManagerProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manager-products-list')
    else:
        form = ManagerProductForm()

    return render(request, 'accounts/manager_product_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة منتج',
        'submit_label': 'حفظ المنتج',
    })


@login_required
def manager_product_update(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    product = Product.objects.select_related('warehouse').filter(pk=pk).first()

    if not product:
        return redirect('manager-products-list')

    if request.method == 'POST':
        form = ManagerProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('manager-products-list')
    else:
        form = ManagerProductForm(instance=product)

    return render(request, 'accounts/manager_product_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل منتج',
        'submit_label': 'حفظ التعديلات',
    })
@login_required
def manager_warehouse_create(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ManagerWarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manager-warehouses-list')
    else:
        form = ManagerWarehouseForm()

    return render(request, 'accounts/manager_warehouse_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة مخزن',
        'submit_label': 'حفظ المخزن',
    })


@login_required
def manager_warehouse_update(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    warehouse = Warehouse.objects.filter(pk=pk).first()

    if not warehouse:
        return redirect('manager-warehouses-list')

    if request.method == 'POST':
        form = ManagerWarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            form.save()
            return redirect('manager-warehouses-list')
    else:
        form = ManagerWarehouseForm(instance=warehouse)

    return render(request, 'accounts/manager_warehouse_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل مخزن',
        'submit_label': 'حفظ التعديلات',
    })
@login_required
def manager_users_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    users_list = WorkerProfile.objects.select_related('user', 'warehouse').order_by('full_name')

    return render(request, 'accounts/manager_users_list.html', {
        'profile': profile,
        'users_list': users_list,
    })


@login_required
def manager_user_create(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ManagerUserForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manager-users-list')
    else:
        form = ManagerUserForm()

    return render(request, 'accounts/manager_user_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'إضافة مستخدم',
        'submit_label': 'حفظ المستخدم',
    })


@login_required
def manager_user_update(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    user_profile = WorkerProfile.objects.select_related('user', 'warehouse').filter(pk=pk).first()

    if not user_profile:
        return redirect('manager-users-list')

    if request.method == 'POST':
        form = ManagerUserForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('manager-users-list')
    else:
        form = ManagerUserForm(instance=user_profile)

    return render(request, 'accounts/manager_user_form.html', {
        'profile': profile,
        'form': form,
        'page_title': 'تعديل مستخدم',
        'submit_label': 'حفظ التعديلات',
    })
@login_required
def manager_inventory_adjust(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    inventory = Inventory.objects.select_related(
        'product',
        'product__warehouse',
    ).filter(pk=pk).first()

    if not inventory:
        return redirect('manager-inventory-list')

    if request.method == 'POST':
        form = ManagerInventoryAdjustForm(request.POST)
        if form.is_valid():
            operation_type = form.cleaned_data['operation_type']
            quantity_dabba = form.cleaned_data['quantity_dabba']
            quantity_kg = form.cleaned_data['quantity_kg']

            entered_total = (Decimal(quantity_dabba) * Decimal('6.5')) + Decimal(quantity_kg)
            current_total = inventory.total_kg()

            if operation_type == 'add':
                new_total = current_total + entered_total
            elif operation_type == 'subtract':
                if entered_total > current_total:
                    form.add_error(None, 'الكمية المطلوب خصمها أكبر من المخزون الحالي.')
                    return render(request, 'accounts/manager_inventory_adjust.html', {
                        'profile': profile,
                        'inventory': inventory,
                        'form': form,
                    })
                new_total = current_total - entered_total
            else:
                new_total = entered_total

            inventory.set_from_total_kg(new_total)
            inventory.save()

            return redirect('manager-inventory-list')
    else:
        form = ManagerInventoryAdjustForm()

    return render(request, 'accounts/manager_inventory_adjust.html', {
        'profile': profile,
        'inventory': inventory,
        'form': form,
    })


@login_required
def manager_product_deactivate(request, pk):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or profile.role != 'manager':
        return redirect('dashboard')

    product = Product.objects.filter(pk=pk).first()
    if product and request.method == 'POST':
        product.is_active = False
        product.save(update_fields=['is_active'])

    return redirect('manager-products-list')
