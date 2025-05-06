from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
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

    # Get all locations and buildings
    locations = []
    buildings = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT name, bldg FROM locations ORDER BY name')
            location_data = c.fetchall()
            locations = [row[0] for row in location_data]
            buildings = sorted(list(set(row[1] for row in location_data)))
    except Exception as e:
        logger.error(f"Error fetching locations/buildings for user {current_user.username}: {str(e)}")
        flash("Error loading locations/buildings.", "danger")

    # Get all housing units from residents table
    housing_units = []
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute('SELECT DISTINCT housing_unit FROM residents WHERE housing_unit IS NOT NULL ORDER BY housing_unit')
            housing_units = [row[0] for row in c.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching housing units for user {current_user.username}: {str(e)}")
        flash("Error loading housing units.", "danger")

    # Get user's current details
    user_data = {
        'username': current_user.username,
        'role': current_user.role,
        'theme': current_user.theme,
        'default_view': 'All Locations',
        'default_unit': 'All Units'
    }
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT default_view, default_unit FROM users WHERE username = ?",
                (current_user.username,)
            )
            result = c.fetchone()
            if result:
                user_data['default_view'] = result[0] or 'All Locations'
                user_data['default_unit'] = result[1] or 'All Units'
    except Exception as e:
        logger.error(f"Error fetching user data for {current_user.username}: {str(e)}")
        flash("Error loading user data.", "danger")

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        theme = request.form.get('theme')
        default_view = request.form.get('default_view')
        default_unit = request.form.get('default_unit')
        
        logger.info(f"User {current_user.username} attempting to update account (theme={theme}, default_view={default_view}, default_unit={default_unit}, password={'set' if new_password else 'not set'})")
        
        if new_password and len(new_password) < MIN_PASSWORD_LENGTH:
            logger.warning(f"User {current_user.username} failed to update password: Password too short")
            log_audit_action(
                username=username,
                action='update_password_failed',
                target='account',
                details=f'Password less than {MIN_PASSWORD_LENGTH} characters'
            )
            flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", "warning")
            return render_template('common/account.html', user=user_data, locations=locations, buildings=buildings, housing_units=housing_units)

        try:
            with get_db() as conn:
                c = conn.cursor()

                # Update password, theme, default_view, and default_unit
                if new_password:
                    hashed_password = generate_password_hash(new_password)
                    c.execute(
                        "UPDATE users SET password = ?, theme = ?, default_view = ?, default_unit = ? WHERE id = ?",
                        (hashed_password, theme, default_view, default_unit, current_user.id)
                    )
                    logger.debug(f"Updated password, theme, default_view, and default_unit for user {current_user.username}")
                    log_audit_action(
                        username=current_user.username,
                        action='update_password',
                        target='account',
                        details='Changed account password, theme, default view, and default unit'
                    )
                else:
                    c.execute(
                        "UPDATE users SET theme = ?, default_view = ?, default_unit = ? WHERE id = ?",
                        (theme, default_view, default_unit, current_user.id)
                    )
                    logger.debug(f"Updated theme, default_view, and default_unit for user {current_user.username}")
                    log_audit_action(
                        username=current_user.username,
                        action='update_account',
                        target='account',
                        details=f'Changed theme to {theme}, default view to {default_view}, and default unit to {default_unit}'
                    )

                conn.commit()
                # Update current_user attributes to reflect changes
                current_user.theme = theme
                current_user.default_view = default_view
                current_user.default_unit = default_unit

            logger.info(f"Successfully updated account for user {current_user.username}")
            flash('Account updated successfully.', 'success')
            # Pass theme in redirect to trigger frontend update
            return redirect(url_for('account.account', _theme=theme))

        except Exception as e:
            logger.error(f"Error updating account for user {current_user.username}: {str(e)}", exc_info=True)
            flash('Error updating account.', 'danger')
            log_audit_action(
                username=current_user.username,
                action='update_account_failed',
                target='account',
                details=f'Failed to update account: {str(e)}'
            )

    return render_template('common/account.html', user=user_data, locations=locations, buildings=buildings, housing_units=housing_units)

@account_bp.route('/update_theme', methods=['POST'])
@login_required
@limiter.limit("50/hour", key_func=user_key_func)
def update_theme():
    try:
        data = request.get_json()
        new_theme = data.get('theme')
        if new_theme not in ['light', 'dark']:
            return jsonify({'success': False, 'message': 'Invalid theme'}), 400

        with get_db() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE users SET theme = ? WHERE id = ?",
                (new_theme, current_user.id)
            )
            conn.commit()

        # Update current_user.theme to reflect the new theme
        current_user.theme = new_theme

        logger.info(f"User {current_user.username} updated theme to {new_theme}")
        log_audit_action(
            username=current_user.username,
            action='update_theme',
            target='account',
            details=f'Changed theme to {new_theme}'
        )
        return jsonify({'success': True, 'message': 'Theme updated successfully'}), 200

    except Exception as e:
        logger.error(f"Error updating theme for user {current_user.username}: {str(e)}")
        return jsonify({'success': False, 'message': 'Error updating theme'}), 500