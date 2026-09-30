# Accounting Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new zero-start accounting layer for the honey management system while preserving old sales, purchase, inventory, supplier, and customer data as archive.

**Architecture:** Add a central ledger with financial accounts, then route every new money-moving workflow through ledger entries. Existing domain records stay in place, while new accounting-aware records point to financial accounts for balances, reports, and audit trails.

**Tech Stack:** Django models/forms/views/templates, SQLite on PythonAnywhere, Django migrations, Django test runner.

**Spec:** `docs/superpowers/specs/2026-10-01-accounting-redesign-design.md`

## Global Constraints

- The new accounting system starts from zero; old data remains archived and does not seed new bank/wallet/cash balances.
- Every new financial movement must be linked to a financial account.
- Financial account types are cashbox, bank, wallet, and worker.
- Workers act like financial accounts for cash held by workers.
- Operating expenses reduce profit; personal expenses reduce cash balances only.
- Do not delete old tables or old data.
- Do not use `flush` during deployment.
- Every deployment to PythonAnywhere must first back up `db.sqlite3` and export a JSON data backup.
- Each new editable financial operation must support edit and delete by reversing old effects before applying new effects.

## Review Focus

- Editing an operation after money has moved must reverse the old ledger entries exactly once, then apply the new entries.
- Deleting an operation must not leave orphaned ledger entries or wrong balances.
- Deferred customer sales must not increase bank/wallet/cash balances until a payment is recorded.
- Transfer fees must reduce the source account and count as operating expenses.
- Hidden or archived old entities must remain readable in old history without appearing in new daily workflows.

---

## File Structure

- Create `accounting/models.py`: financial accounts, ledger entries, transfers, manual money adjustments, expense categories, customer payments.
- Create `accounting/forms.py`: forms for financial accounts, transfers, adjustments, customer payments, and expense entries.
- Create `accounting/services.py`: shared ledger functions for posting, reversing, and recalculating operation effects.
- Create `accounting/views.py`: manager-only pages for accounts, account statements, transfers, adjustments, dashboard reports, deferred customers.
- Create `accounting/urls.py`: routes under `/accounting/`.
- Create `accounting/tests.py`: unit tests for balances, posting/reversing ledger entries, transfers, and reporting summaries.
- Modify `config/settings.py`: add `accounting`.
- Modify `config/urls.py`: include accounting routes.
- Modify `templates/accounts/manager_dashboard.html`: replace old daily workflow links with accounting-first links.
- Modify `sales/models.py`, `sales/forms.py`, `sales/views.py`, `templates/sales/*.html`: route new manager sales through accounting.
- Modify `suppliers/models.py`, `suppliers/forms.py`, `suppliers/views.py`, `templates/suppliers/*.html`: route supplier purchase/payment money through accounting.
- Modify `finance/models.py`, `finance/forms.py`, `finance/views.py`, `templates/finance/*.html`: separate operating and personal expenses through accounting accounts.
- Modify `accounts/views.py`, `accounts/urls.py`, related templates: hide old users/warehouses from main workflow and expose archive/report links only where useful.

## Task 1: Accounting App Foundation

**Files:**
- Create: `accounting/__init__.py`
- Create: `accounting/apps.py`
- Create: `accounting/models.py`
- Create: `accounting/services.py`
- Create: `accounting/tests.py`
- Modify: `config/settings.py`

**Interfaces:**
- Produces: `FinancialAccount`, `LedgerEntry`, `post_entry(account, amount, direction, category, description, source_type, source_id, occurred_at=None) -> LedgerEntry`
- Produces: `reverse_entries(source_type: str, source_id: int) -> int`
- Produces: `FinancialAccount.current_balance() -> Decimal`

- [ ] **Step 1: Write failing ledger balance tests**

Add tests in `accounting/tests.py`:

```python
def test_financial_account_balance_includes_opening_and_ledger_entries(self):
    account = FinancialAccount.objects.create(name="Cash", account_type="cashbox", opening_balance=100)
    post_entry(account, 50, "in", "manual_deposit", "deposit", "test", 1)
    post_entry(account, 20, "out", "manual_withdrawal", "withdrawal", "test", 2)
    self.assertEqual(account.current_balance(), Decimal("130.00"))
```

```python
def test_reverse_entries_voids_source_entries(self):
    account = FinancialAccount.objects.create(name="Cash", account_type="cashbox", opening_balance=0)
    post_entry(account, 50, "in", "manual_deposit", "deposit", "test", 1)
    self.assertEqual(reverse_entries("test", 1), 1)
    self.assertEqual(account.current_balance(), Decimal("0.00"))
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: FAIL because `accounting` app and models do not exist.

- [ ] **Step 3: Implement accounting app models**

Create `FinancialAccount` with fields:

- `name: CharField(max_length=150)`
- `account_type: CharField(choices=[cashbox, bank, wallet, worker])`
- `opening_balance: DecimalField(max_digits=14, decimal_places=2, default=0)`
- `is_active: BooleanField(default=True)`
- `notes: TextField(blank=True, null=True)`
- `created_at: DateTimeField(auto_now_add=True)`

Create `LedgerEntry` with fields:

- `account: ForeignKey(FinancialAccount, on_delete=PROTECT, related_name="ledger_entries")`
- `direction: CharField(choices=[in, out])`
- `amount: DecimalField(max_digits=14, decimal_places=2)`
- `category: CharField(max_length=50)`
- `description: CharField(max_length=250)`
- `source_type: CharField(max_length=80)`
- `source_id: PositiveIntegerField()`
- `is_reversed: BooleanField(default=False)`
- `occurred_at: DateTimeField(default=timezone.now)`
- `created_at: DateTimeField(auto_now_add=True)`

Implement `FinancialAccount.current_balance() -> Decimal` by summing non-reversed ledger entries.

- [ ] **Step 4: Implement ledger services**

In `accounting/services.py`, implement:

- `post_entry(account: FinancialAccount, amount: Decimal, direction: str, category: str, description: str, source_type: str, source_id: int, occurred_at=None) -> LedgerEntry`
- `reverse_entries(source_type: str, source_id: int) -> int`

Validate positive amounts. Mark existing non-reversed source entries as reversed in `reverse_entries`.

- [ ] **Step 5: Add app to settings and create migrations**

Run:

```bash
venv\Scripts\python.exe manage.py makemigrations accounting
venv\Scripts\python.exe manage.py migrate
```

- [ ] **Step 6: Run tests**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add accounting config/settings.py
git commit -m "Add accounting ledger foundation"
```

## Task 2: Financial Accounts UI and Manual Money Movements

**Files:**
- Create: `accounting/forms.py`
- Create: `accounting/views.py`
- Create: `accounting/urls.py`
- Create: `templates/accounting/account_list.html`
- Create: `templates/accounting/account_form.html`
- Create: `templates/accounting/account_detail.html`
- Create: `templates/accounting/manual_adjustment_form.html`
- Modify: `config/urls.py`
- Modify: `templates/accounts/manager_dashboard.html`
- Test: `accounting/tests.py`

**Interfaces:**
- Consumes: `FinancialAccount.current_balance()`
- Consumes: `post_entry(...)`
- Produces routes: `accounting-account-list`, `accounting-account-create`, `accounting-account-update`, `accounting-account-detail`, `accounting-manual-adjustment`

- [ ] **Step 1: Write view tests for account creation and manual deposit**

Add tests that create a manager user/profile, post a new bank account, and post a manual deposit. Assert account exists and balance increased.

- [ ] **Step 2: Run tests and verify failure**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: FAIL because forms/views/routes do not exist.

- [ ] **Step 3: Implement forms**

Create:

- `FinancialAccountForm(ModelForm)` for `name`, `account_type`, `opening_balance`, `is_active`, `notes`.
- `ManualAdjustmentForm(forms.Form)` with `account`, `direction`, `amount`, `category`, `description`, `occurred_at`.

Categories for manual adjustment:

- `manual_deposit`
- `manual_withdrawal`
- `personal_expense`
- `operating_expense`

- [ ] **Step 4: Implement manager-only views**

Add helper `get_manager_profile(request)` in `accounting/views.py`.

Implement:

- account list with balances.
- create/edit account.
- account detail with ledger entries.
- manual adjustment that posts one ledger entry.

- [ ] **Step 5: Add URLs and dashboard links**

Include `path('accounting/', include('accounting.urls'))` in `config/urls.py`.

Add dashboard links for:

- الحسابات المالية
- إضافة حركة مالية
- التقارير المحاسبية

- [ ] **Step 6: Run tests**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add accounting config/urls.py templates/accounting templates/accounts/manager_dashboard.html
git commit -m "Add financial accounts management"
```

## Task 3: Transfers Between Accounts with Fees

**Files:**
- Modify: `accounting/models.py`
- Modify: `accounting/forms.py`
- Modify: `accounting/services.py`
- Modify: `accounting/views.py`
- Create: `templates/accounting/transfer_form.html`
- Test: `accounting/tests.py`

**Interfaces:**
- Produces: `MoneyTransfer`
- Produces: `post_transfer(transfer: MoneyTransfer) -> None`
- Consumes: `post_entry(...)`, `reverse_entries(...)`

- [ ] **Step 1: Write transfer tests**

Add tests:

```python
def test_transfer_moves_money_between_accounts_and_fee_counts_as_operating_expense(self):
    source = FinancialAccount.objects.create(name="Wallet", account_type="wallet", opening_balance=1000)
    target = FinancialAccount.objects.create(name="Bank", account_type="bank", opening_balance=0)
    transfer = MoneyTransfer.objects.create(source_account=source, target_account=target, amount=500, fee_amount=10, description="transfer")
    self.assertEqual(source.current_balance(), Decimal("490.00"))
    self.assertEqual(target.current_balance(), Decimal("500.00"))
```

- [ ] **Step 2: Run test and verify failure**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: FAIL because `MoneyTransfer` does not exist.

- [ ] **Step 3: Implement `MoneyTransfer`**

Fields:

- `source_account`
- `target_account`
- `amount`
- `fee_amount`
- `description`
- `occurred_at`
- `created_at`

On save, reverse previous entries for source `money_transfer`, then post:

- source account out for amount, category `transfer_out`
- target account in for amount, category `transfer_in`
- source account out for fee amount if greater than zero, category `transfer_fee`

- [ ] **Step 4: Implement transfer form/view/template**

Manager-only create/update/delete.

Delete reverses entries and deletes transfer record.

- [ ] **Step 5: Run tests**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add accounting templates/accounting
git commit -m "Add account transfers with fees"
```

## Task 4: Manager Sales Integrated with Accounting

**Files:**
- Modify: `sales/models.py`
- Modify: `sales/forms.py`
- Modify: `sales/views.py`
- Modify: `sales/urls.py`
- Create/Modify: `templates/sales/manager_sale_form.html`
- Modify: `templates/accounts/manager_dashboard.html`
- Test: `sales/tests.py` or create `sales/tests/test_accounting_sales.py`

**Interfaces:**
- Consumes: `FinancialAccount`
- Consumes: `post_entry(...)`, `reverse_entries(...)`
- Produces: manager sale create/update/delete flow where payment type controls ledger impact.

- [ ] **Step 1: Write sale accounting tests**

Add tests for:

- cash sale requires worker financial account and posts money into worker account.
- transfer sale requires bank/wallet/cashbox account and posts money into that account.
- deferred sale requires customer and posts no ledger entry.
- edit sale reverses old ledger entry and posts new one.
- delete sale reverses ledger entries.

- [ ] **Step 2: Run tests and verify failure**

Run: `venv\Scripts\python.exe manage.py test sales`

Expected: FAIL because sale-accounting fields do not exist.

- [ ] **Step 3: Extend sale model for accounting**

Add optional fields:

- `cash_worker_account: ForeignKey(FinancialAccount, null=True, blank=True, limit to account_type='worker')`
- `payment_account: ForeignKey(FinancialAccount, null=True, blank=True, related_name='sales_payments')`
- `is_new_accounting_sale: BooleanField(default=False)`

Do not migrate old sales into new accounting balances.

- [ ] **Step 4: Implement manager sale form**

Payment rules:

- `cash`: require `cash_worker_account`.
- `transfer`: require `payment_account`.
- `deferred`: require customer name or phone; no account required.

- [ ] **Step 5: Post ledger entries from sale save service**

Use a service function `sync_sale_ledger(sale: Sale) -> None`.

For cash: post `sale_cash` in to worker account.

For transfer: post `sale_transfer` in to selected account.

For deferred: reverse existing entries and post none.

- [ ] **Step 6: Move daily sale creation to manager page**

Add manager dashboard link to sale create page.

Keep old worker routes hidden from main navigation but do not delete them.

- [ ] **Step 7: Run tests**

Run:

```bash
venv\Scripts\python.exe manage.py test accounting sales
venv\Scripts\python.exe manage.py check
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add sales templates/sales templates/accounts/manager_dashboard.html
git commit -m "Connect manager sales to accounting ledger"
```

## Task 5: Deferred Customers and Customer Payments

**Files:**
- Modify: `accounting/models.py`
- Modify: `accounting/forms.py`
- Modify: `accounting/views.py`
- Create: `templates/accounting/deferred_customer_list.html`
- Create: `templates/accounting/customer_statement.html`
- Create: `templates/accounting/customer_payment_form.html`
- Test: `accounting/tests.py`

**Interfaces:**
- Consumes: deferred `Sale` records.
- Produces: `CustomerPayment`
- Produces: deferred customer report totals.

- [ ] **Step 1: Write deferred customer tests**

Tests:

- deferred sale increases customer receivable report.
- customer payment posts money into selected account.
- customer payment decreases remaining customer balance.
- edit/delete customer payment reverses ledger entries.

- [ ] **Step 2: Run tests and verify failure**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: FAIL because customer payment model does not exist.

- [ ] **Step 3: Implement `CustomerPayment`**

Fields:

- `customer`
- `account`
- `amount`
- `payment_date`
- `notes`
- `created_at`

Save posts `customer_payment` in to selected account.

Delete reverses entries.

- [ ] **Step 4: Implement reports/views**

Deferred customer list shows:

- customer name.
- phone.
- total deferred sales.
- total payments.
- remaining balance.

Customer statement shows sales and payments.

- [ ] **Step 5: Run tests**

Run: `venv\Scripts\python.exe manage.py test accounting`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add accounting templates/accounting
git commit -m "Add deferred customer accounting"
```

## Task 6: Supplier Purchases and Payments Through Accounts

**Files:**
- Modify: `suppliers/models.py`
- Modify: `suppliers/forms.py`
- Modify: `suppliers/views.py`
- Modify: `templates/suppliers/*.html`
- Test: `suppliers/tests.py`

**Interfaces:**
- Consumes: `FinancialAccount`
- Consumes: `post_entry(...)`, `reverse_entries(...)`
- Produces: supplier purchases/payments that optionally affect inventory and always track payable/payment state.

- [ ] **Step 1: Write supplier accounting tests**

Tests:

- paid purchase requires payment account and posts purchase out.
- unpaid purchase posts no ledger entry but increases supplier payable report.
- supplier payment posts out from selected account and reduces supplier payable.
- purchase with `add_to_inventory=True` updates inventory.
- edit/delete reverses old ledger and inventory impact.

- [ ] **Step 2: Run tests and verify failure**

Run: `venv\Scripts\python.exe manage.py test suppliers`

Expected: FAIL because supplier accounting fields are missing.

- [ ] **Step 3: Extend supplier purchase/payment models**

Add to `SupplierPurchase`:

- `payment_status: CharField(choices=[paid, unpaid], default='unpaid')`
- `payment_account: ForeignKey(FinancialAccount, null=True, blank=True)`
- `is_new_accounting_purchase: BooleanField(default=False)`

Add to `SupplierPayment`:

- `payment_account: ForeignKey(FinancialAccount, null=True, blank=True)`
- `is_new_accounting_payment: BooleanField(default=False)`

- [ ] **Step 4: Implement ledger sync**

Paid purchase posts `supplier_purchase_payment` out from selected account.

Supplier payment posts `supplier_payment` out from selected account.

Unpaid purchase posts no ledger entry.

- [ ] **Step 5: Update forms/templates**

Purchase form includes:

- payment status.
- payment account if paid.
- add to inventory.

Payment form requires payment account.

- [ ] **Step 6: Run tests**

Run:

```bash
venv\Scripts\python.exe manage.py test accounting suppliers
venv\Scripts\python.exe manage.py check
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add suppliers templates/suppliers
git commit -m "Connect suppliers to accounting ledger"
```

## Task 7: Operating and Personal Expenses

**Files:**
- Modify: `finance/models.py`
- Modify: `finance/forms.py`
- Modify: `finance/views.py`
- Modify: `templates/finance/*.html`
- Test: `finance/tests.py`

**Interfaces:**
- Consumes: `FinancialAccount`
- Consumes: `post_entry(...)`, `reverse_entries(...)`
- Produces expenses that always subtract from an account, with operating vs personal profit behavior.

- [ ] **Step 1: Write expense tests**

Tests:

- operating expense posts out and appears in profit deduction report.
- personal expense posts out but does not reduce profit.
- edit/delete reverses old entries.

- [ ] **Step 2: Extend expense model**

Add:

- `expense_type: CharField(choices=[operating, personal], default='operating')`
- `payment_account: ForeignKey(FinancialAccount, on_delete=PROTECT)`
- `is_new_accounting_expense: BooleanField(default=True)`

- [ ] **Step 3: Update forms/views/templates**

Expense creation requires payment account.

Personal expenses are clearly labeled as not profit-reducing.

- [ ] **Step 4: Run tests**

Run:

```bash
venv\Scripts\python.exe manage.py test accounting finance
venv\Scripts\python.exe manage.py check
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add finance templates/finance
git commit -m "Separate operating and personal expenses"
```

## Task 8: Accounting Reports Dashboard

**Files:**
- Modify: `accounting/views.py`
- Create: `templates/accounting/reports_dashboard.html`
- Create: `templates/accounting/account_balances_report.html`
- Create: `templates/accounting/profit_report.html`
- Create: `templates/accounting/cashflow_report.html`
- Create: `templates/accounting/worker_balances_report.html`
- Create: `templates/accounting/personal_expenses_report.html`
- Test: `accounting/tests.py`

**Interfaces:**
- Consumes all ledger categories.
- Produces clear reports for owner review.

- [ ] **Step 1: Write reporting tests**

Tests:

- account balances report matches ledger balances.
- profit report includes sales minus operating expenses and excludes personal expenses.
- cashflow report groups money in/out by category.
- worker balances report lists worker accounts and balances.

- [ ] **Step 2: Implement report query helpers**

In `accounting/services.py`, add:

- `get_account_balances() -> list[dict]`
- `get_profit_summary(start_date, end_date) -> dict`
- `get_cashflow_summary(start_date, end_date) -> dict`
- `get_worker_balances() -> list[dict]`
- `get_personal_expense_summary(start_date, end_date) -> dict`

- [ ] **Step 3: Implement report dashboard**

Reports page must show:

- إجمالي المال الحالي.
- أرصدة كل صندوق/بنك/محفظة/عامل.
- المبيعات النقدية والحوالات والآجل.
- المصاريف التشغيلية.
- المصاريف الشخصية.
- ربح الفترة.
- المتبقي على العملاء.
- المتبقي للموردين.
- رصيد كل عامل.

Support filters:

- today.
- current week.
- current month.
- custom date range.

- [ ] **Step 4: Run tests**

Run:

```bash
venv\Scripts\python.exe manage.py test accounting
venv\Scripts\python.exe manage.py check
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add accounting templates/accounting
git commit -m "Add accounting reports dashboard"
```

## Task 9: Simplify Navigation and Preserve Archive

**Files:**
- Modify: `templates/accounts/manager_dashboard.html`
- Modify: `accounts/urls.py`
- Modify: `accounts/views.py`
- Create: `templates/accounts/archive_dashboard.html`
- Test: `accounts/tests.py`

**Interfaces:**
- Produces manager-first navigation.
- Keeps old data reachable but out of daily workflow.

- [ ] **Step 1: Write navigation tests**

Tests:

- manager dashboard includes accounting links.
- manager dashboard does not show old users/warehouses as primary workflow.
- archive dashboard links to old sales/purchases/users/warehouses where still needed.

- [ ] **Step 2: Update dashboard template**

Primary links:

- البيع.
- الحسابات المالية.
- التحويلات.
- العملاء الآجل.
- الموردون.
- المصاريف.
- التقارير المحاسبية.
- المخزون.

Move old users/warehouses/worker-account links to archive or hide them.

- [ ] **Step 3: Add archive dashboard**

Archive page shows read-only or legacy links:

- المبيعات القديمة.
- المخازن القديمة.
- المستخدمون القدامى.
- حسابات العمال القديمة.

- [ ] **Step 4: Run tests**

Run:

```bash
venv\Scripts\python.exe manage.py test accounts
venv\Scripts\python.exe manage.py check
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add accounts templates/accounts
git commit -m "Simplify manager navigation for accounting workflow"
```

## Task 10: Deployment Safety and PythonAnywhere Runbook

**Files:**
- Create: `docs/deployment/accounting-redesign-pythonanywhere.md`
- Test: manual commands documented.

**Interfaces:**
- Produces exact safe deployment steps.

- [ ] **Step 1: Write deployment runbook**

Include:

```bash
cd /home/7Mohamed/alshahabi_honey
workon alshahabi_honey_env
cp db.sqlite3 db.sqlite3.backup_before_accounting_redesign
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry -e sessions.Session --indent 2 -o data_backup_before_accounting_redesign.json
git pull origin master
python manage.py migrate
python manage.py collectstatic --no-input
```

Then reload from PythonAnywhere Web tab.

State explicitly:

- Do not run `flush`.
- Do not delete `db.sqlite3`.
- If migration fails, stop and send the error.

- [ ] **Step 2: Commit**

```bash
git add docs/deployment/accounting-redesign-pythonanywhere.md
git commit -m "Document accounting redesign deployment"
```

## Final Verification

- [ ] Run all Django tests:

```bash
venv\Scripts\python.exe manage.py test
```

- [ ] Run Django system check:

```bash
venv\Scripts\python.exe manage.py check
```

- [ ] Confirm no `db.sqlite3`, `__pycache__`, or local-only files are staged:

```bash
git status --short
```

- [ ] Perform final review focused on:

  - ledger reversal correctness.
  - account balances.
  - deferred customers.
  - supplier payables.
  - operating vs personal expenses.
  - hidden old workflow links.

