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
    logger.debug(f"User {current_user.username} accessed account page")
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        theme = request.form.get('theme')
        
        logger.info(f"User {current_user.username} attempting to update account (theme={theme}, password={'set' if new_password else 'not set'})")
        
        try:
            with get_db() as conn:
                c = conn.cursor()

                # Update theme
                #c.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, current_user.id))
                #logger.debug(f"Updated theme to {theme} for user {current_user.username}")
                
                # Log theme change to audit log
                # c.execute("""
                #     INSERT INTO audit_log (username, action, target, details)
                #     VALUES (?, ?, ?, ?)
                # """, (
                #     current_user.username,
                #     'update_theme',
                #     'account',
                #     f'Changed theme to {theme}'
                # ))

                # Update password if entered
                if new_password:
                    hashed_password = generate_password_hash(new_password)
                    c.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, current_user.id))
                    logger.debug(f"Updated password for user {current_user.username}")
                    
                    # Log password change to audit log
                    c.execute("""
                        INSERT INTO audit_log (username, action, target, details)
                        VALUES (?, ?, ?, ?)
                    """, (
                        current_user.username,
                        'update_password',
                        'account',
                        'Changed account password'
                    ))

                conn.commit()

            logger.info(f"Successfully updated account for user {current_user.username}")
            flash('Account updated successfully.', 'success')
            return redirect(url_for('account.account'))

        except Exception as e:
            logger.error(f"Error updating account for user {current_user.username}: {str(e)}", exc_info=True)
            flash('Error updating account.', 'danger')
            
            # Log error to audit log
            try:
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO audit_log (username, action, target, details)
                        VALUES (?, ?, ?, ?)
                    """, (
                        current_user.username,
                        'update_account_failed',
                        'account',
                        f'Failed to update account: {str(e)}'
                    ))
                    conn.commit()
            except Exception as audit_error:
                logger.error(f"Failed to write audit log for account update error: {str(audit_error)}")

    return render_template('account.html', user=current_user)