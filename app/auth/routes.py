from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.auth import auth
from app.models import User

@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.tickets"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if not user:
            flash("Email ou senha inválidos.", "danger")
            return render_template("login.html")

        if not user.active:
            flash("Usuário inativo. Contate o administrador.", "danger")
            return render_template("login.html")

        if user.check_password(password):
            login_user(user)
            return redirect(url_for("main.tickets"))

        flash("Email ou senha inválidos.", "danger")

    return render_template("login.html")

@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.tickets"))

    if request.method == "POST":
        first_name = request.form.get("first_name").strip()
        last_name = request.form.get("last_name").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        allowed_domains = ["@empresa", "@digiboard"]

        if not any(domain in email for domain in allowed_domains):
            flash("Email inválido. Utilize um email corporativo valido.", "danger")
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash("As senhas não conferem.", "danger")
            return redirect(url_for("auth.register"))

        exists = User.query.filter_by(email=email).first()

        if exists:
            flash("Já existe um usuário cadastrado com este email.", "danger")
            return redirect(url_for("auth.register"))

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            role="solicitante",
            active=True
        )

        db.session.add(user)
        db.session.commit()

        flash("Usuário criado com sucesso! Faça login para continuar.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")

@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
