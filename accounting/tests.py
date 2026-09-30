from decimal import Decimal

from django.test import TestCase

from accounting.models import FinancialAccount
from accounting.services import post_entry, reverse_entries


class AccountingLedgerTests(TestCase):
    def test_financial_account_balance_includes_opening_and_ledger_entries(self):
        account = FinancialAccount.objects.create(
            name="Cash",
            account_type="cashbox",
            opening_balance=Decimal("100.00"),
        )

        post_entry(account, Decimal("50.00"), "in", "manual_deposit", "deposit", "test", 1)
        post_entry(account, Decimal("20.00"), "out", "manual_withdrawal", "withdrawal", "test", 2)

        self.assertEqual(account.current_balance(), Decimal("130.00"))

    def test_reverse_entries_voids_source_entries(self):
        account = FinancialAccount.objects.create(
            name="Cash",
            account_type="cashbox",
            opening_balance=Decimal("0.00"),
        )
        post_entry(account, Decimal("50.00"), "in", "manual_deposit", "deposit", "test", 1)

        self.assertEqual(reverse_entries("test", 1), 1)
        self.assertEqual(account.current_balance(), Decimal("0.00"))
