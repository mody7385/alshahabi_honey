from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import WorkerProfile


class ManagerNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='manager', password='pass')
        WorkerProfile.objects.create(
            user=self.user,
            full_name='المدير',
            role=WorkerProfile.ROLE_MANAGER,
        )
        self.client.force_login(self.user)

    def test_manager_dashboard_prioritizes_accounting_workflow_links(self):
        response = self.client.get(reverse('manager-dashboard'))

        self.assertContains(response, reverse('manager-sale-create'))
        self.assertContains(response, reverse('accounting-account-list'))
        self.assertContains(response, reverse('accounting-reports-dashboard'))
        self.assertNotContains(response, reverse('manager-warehouses-list'))
        self.assertNotContains(response, reverse('manager-users-list'))

    def test_archive_dashboard_links_legacy_workflows(self):
        response = self.client.get(reverse('manager-archive-dashboard'))

        self.assertContains(response, reverse('manager-warehouses-list'))
        self.assertContains(response, reverse('manager-users-list'))
        self.assertContains(response, reverse('manager-worker-accounts-list'))
        self.assertContains(response, reverse('manager-sales-list'))
