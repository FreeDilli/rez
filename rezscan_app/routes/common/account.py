from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from rezscan_app.models.database import get_db
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from rezscan_app.utils.audit_logging import log_audit_action
from rezscan_app.utils.constants import MIN_PASSWORD_LENGTH

account_bp = Blueprint('account', __name__)
logger = logging.getLogger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def user_key_func():
    if current_user.is_authenticated:
        return current_user.username
    return get_remote_address()

@account_bp.route('/account', methods=['GET', 'POST'], strict_slashes=False)
@login_required
@limiter.limit("50/hour", key_func=user_key_func)
def account():
    logger.debug(f"User {current_user.username} accessed account page")
    
    username = current_user.username if current_user.is_authenticated else 'unknown'
    log_audit_action(
        username=username,
        action='view',
        target='account',
        details='Viewed account page'
    )

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        theme = request.form.get('theme')
        
        logger.info(f"User {current_user.username} attempting to update account (theme={theme}, password={'set' if new_password else 'not set'})")
        
        if new_password and len(new_password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"User {current_user.username} failed to update password: Password too short")
            log_audit_action(
                username=username,
                action='update_password_failed',
                target='account',
                details=f'Password less than {MIN_PASSWORD_LENGTH} characters'
            )
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
            return render_template('common/account.html', user=current_user)

        try:
            with get_db() as conn:
                c = conn.cursor()

                # Update password if entered
                if new_password:
                    hashed_password = generate_password_hash(new_password)
                    c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, current_user.id))
                    logger.debug(f"Updated password for user {current_user.username}")
                    
                    log_audit_action(
                        username=current_user.username,
                        action='update_password',
                        target='account',
                        details='Changed account password'
                    )

                conn.commit()

            logger.info(f"Successfully updated account for user {current_user.username}")
            flash('Account updated successfully.', 'success')
            return redirect(url_for('account.account'))

        except Exception as e:
            logger.error(f"Error updating account for user {current_user.username}: {str(e)}", exc_info=True)
            flash('Error updating account.', 'danger')
            log_audit_action(
                username=current_user.username,
                action='update_account_failed',
                target='account',
                details=f'Failed to update account: {str(e)}'
            )

    return render_template('common/account.html', user=current_user)