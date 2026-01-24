from flask import (
    Blueprint, render_template, request, redirect, url_for, flash
)
from datetime import datetime
from ..services.permissions_service import requires_permission

budgets_bp = Blueprint('budgets', __name__)

@budgets_bp.route('/')
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def budgets():
    budgets = Budget.query.all()
    return render_template('budgets/list.html', budgets=budgets)

@budgets_bp.route('/<int:id>')
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def budget_detail(id):
    budget = Budget.query.get_or_404(id)
    return render_template('budgets/detail.html', budget=budget)

@budgets_bp.route('/new', methods=['GET', 'POST'])
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def new_budget():
    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if (user_role or session.get('role')) != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('business_ops') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('budgets.budgets'))
        budget = Budget(
            name=request.form['name'],
            category=request.form.get('category'),
            amount=float(request.form['amount']),
            currency=request.form.get('currency', 'EUR'), # Use .get() and add default
            period=request.form.get('period', 'One-time'), # Use .get() and add default
            valid_from=datetime.strptime(request.form['valid_from'], '%Y-%m-%d').date(),
            valid_until=datetime.strptime(request.form['valid_until'], '%Y-%m-%d').date()
        )
        db.session.add(budget)
        db.session.commit()
        flash('Budget created successfully!')
        return redirect(url_for('budgets.budgets'))

    return render_template('budgets/form.html')

@budgets_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@requires_permission('business_ops', access_level='READ_ONLY')
def edit_budget(id):
    budget = Budget.query.get_or_404(id)

    if request.method == 'POST':
        # Manual check for WRITE access
        from ..services.permissions_cache import permissions_cache
        from flask import session
        user_id = session.get('user_id')
        user_role = session.get('user_role')
        if (user_role or session.get('role')) != 'admin':
            perms = permissions_cache.get(user_id)
            if perms.get('business_ops') != 'WRITE':
                flash('Write access required for this action.', 'danger')
                return redirect(url_for('budgets.budget_detail', id=id))
        budget.name = request.form['name']
        budget.category = request.form.get('category')
        budget.amount = float(request.form['amount'])
        budget.currency = request.form['currency']
        budget.period = request.form['period']
        budget.valid_from = datetime.strptime(request.form['valid_from'], '%Y-%m-%d').date()
        budget.valid_until = datetime.strptime(request.form['valid_until'], '%Y-%m-%d').date()
        db.session.commit()
        flash('Budget updated successfully!')
        return redirect(url_for('budgets.budgets'))

    return render_template('budgets/form.html', budget=budget)