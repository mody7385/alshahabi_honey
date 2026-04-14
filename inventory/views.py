from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import WorkerProfile
from .models import Inventory


@login_required
def worker_inventory_list(request):
    profile = WorkerProfile.objects.filter(user=request.user).select_related('warehouse').first()

    if not profile or not profile.warehouse:
        return redirect('dashboard')

    inventory_items = Inventory.objects.filter(
        product__warehouse=profile.warehouse
    ).select_related(
        'product',
        'product__warehouse',
    ).order_by('product__name')

    context = {
        'profile': profile,
        'inventory_items': inventory_items,
    }
    return render(request, 'inventory/worker_inventory_list.html', context)