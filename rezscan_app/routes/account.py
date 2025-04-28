from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from rezscan_app.models.database import get_db
import logging

account_bp = Blueprint('account', __name__, url_prefix='/account')
logger = logging.getLogger(__name__)

@account_bp.route('/', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        theme = request.form.get('theme')

        try:
            with get_db() as conn:
                c = conn.cursor()

                # Update theme
                c.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, current_user.id))

                # Update password if entered
                if new_password:
                    hashed_password = generate_password_hash(new_password)
                    c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, current_user.id))

                conn.commit()

            flash('Account updated successfully.', 'success')
            return redirect(url_for('account.account'))

        except Exception as e:
            logger.error(f"Error updating account: {str(e)}")
            flash('Error updating account.', 'danger')

    return render_template('account.html', user=current_user)
