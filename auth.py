from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        
        # Redirect based on role
        if user.role == 'platform_admin':
            return redirect(url_for('admin.platform_dashboard'))
        else:
            return redirect(url_for('admin.business_dashboard'))

    return render_template('auth/login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@auth.route('/create-business-admin', methods=['GET', 'POST'])
@login_required
def create_business_admin():
    if current_user.role != 'platform_admin':
        flash('Access denied. Platform admin only.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        business_id = request.form.get('business_id')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists')
            return redirect(url_for('auth.create_business_admin'))

        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password),
            role='business_admin',
            business_id=business_id
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Business admin created successfully!')
        return redirect(url_for('admin.platform_dashboard'))

    return render_template('auth/create_business_admin.html')
