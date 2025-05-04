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

    # Get all locations from locations table
    locations = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT name FROM locations ORDER BY name')
            locations = [row[0] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching locations for user {current_user.username}: {str(e)}")
        flash("Error loading locations.", "danger")

    # Get user's current details, including default_view
    user_data = {
        'username': current_user.username,
        'role': current_user.role,
        'theme': getattr(current_user, 'theme', 'dark'),
        'default_view': 'All Locations'  # Default fallback
    }
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT theme, default_view FROM users WHERE username = ?",
                (current_user.username,)
            )
            result = c.fetchone()
            if result:
                user_data['theme'] = result[0] or 'dark'
                user_data['default_view'] = result[1] or 'All Locations'
    except Exception as e:
        logger.error(f"Error fetching user data for {current_user.username}: {str(e)}")
        flash("Error loading user data.", "danger")

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        theme = request.form.get('theme')
        default_view = request.form.get('default_view')
        
        logger.info(f"User {current_user.username} attempting to update account (theme={theme}, default_view={default_view}, password={'set' if new_password else 'not set'})")
        
        if new_password and len(new_password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"User {current_user.username} failed to update password: Password too short")
            log_audit_action(
                username=username,
                action='update_password_failed',
                target='account',
                details=f'Password less than {MIN_PASSWORD_LENGTH} characters'
            )
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
            return render_template('common/account.html', user=user_data, locations=locations)

        try:
            with get_db() as conn:
                c = conn.cursor()

                # Update password, theme, and default_view
                if new_password:
                    hashed_password = generate_password_hash(new_password)
                    c.execute(
                        "UPDATE users SET password = ?, theme = ?, default_view = ? WHERE id = ?",
                        (hashed_password, theme, default_view, current_user.id)
                    )
                    logger.debug(f"Updated password, theme, and default_view for user {current_user.username}")
                    log_audit_action(
                        username=current_user.username,
                        action='update_password',
                        target='account',
                        details='Changed account password, theme, and default view'
                    )
                else:
                    c.execute(
                        "UPDATE users SET theme = ?, default_view = ? WHERE id = ?",
                        (theme, default_view, current_user.id)
                    )
                    logger.debug(f"Updated theme and default_view for user {current_user.username}")
                    log_audit_action(
                        username=current_user.username,
                        action='update_account',
                        target='account',
                        details=f'Changed theme to {theme} and default view to {default_view}'
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

    return render_template('common/account.html', user=user_data, locations=locations)