from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from app.admin import admin
from app.models import User, DefectCategory, SolutionCategory

@admin.before_request
def restrict_admin():
    if current_user.is_authenticated and current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("main.dashboard"))

@admin.route("/defects", methods=["GET", "POST"])
@login_required
def defects():
    if request.method == "POST":
        code = request.form.get("code").strip().upper()
        description = request.form.get("description").strip().upper()
        area = request.form.get("area")

        exists = DefectCategory.query.filter_by(code=code).first()

        if exists:
            flash("Já existe uma categoria com esse código.", "danger")
        else:
            defect = DefectCategory(
                code=code,
                description=description,
                area=area
            )
            db.session.add(defect)
            db.session.commit()
            flash("Categoria de defeito cadastrada com sucesso!", "success")

        return redirect(url_for("admin.defects"))

    defects = DefectCategory.query.order_by(
        DefectCategory.area.asc(),
        DefectCategory.code.asc()
    ).all()

    return render_template("admin_defects.html", defects=defects)


@admin.route("/defects/<int:id>/edit", methods=["GET", "POST"])
@login_required
def defect_edit(id):
    defect = db.get_or_404(DefectCategory, id)

    if request.method == "POST":
        defect.code = request.form.get("code").strip().upper()
        defect.description = request.form.get("description").strip().upper()
        defect.area = request.form.get("area")
        defect.active = True if request.form.get("active") == "1" else False

        db.session.commit()
        flash("Categoria de defeito atualizada com sucesso!", "success")
        return redirect(url_for("admin.defects"))

    return render_template("admin_defect_edit.html", defect=defect)


@admin.route("/defects/<int:id>/toggle", methods=["POST"])
@login_required
def defect_toggle(id):
    defect = db.get_or_404(DefectCategory, id)
    defect.active = not defect.active
    db.session.commit()

    flash(f"Status da categoria {defect.code} alterado com sucesso!", "success")
    return redirect(url_for("admin.defects"))


@admin.route("/solutions", methods=["GET", "POST"])
@login_required
def solutions():
    if request.method == "POST":
        description = request.form.get("description").strip().upper()

        exists = SolutionCategory.query.filter_by(description=description).first()

        if exists:
            flash("Já existe uma categoria de solução com essa descrição.", "danger")
        else:
            sol = SolutionCategory(description=description)
            db.session.add(sol)
            db.session.commit()
            flash("Categoria de solução cadastrada com sucesso!", "success")

        return redirect(url_for("admin.solutions"))

    solutions = SolutionCategory.query.order_by(SolutionCategory.id.asc()).all()
    return render_template("admin_solutions.html", solutions=solutions)


@admin.route("/solutions/<int:id>/edit", methods=["GET", "POST"])
@login_required
def solution_edit(id):
    sol = db.get_or_404(SolutionCategory, id)

    if request.method == "POST":
        sol.description = request.form.get("description").strip().upper()
        sol.active = True if request.form.get("active") == "1" else False

        db.session.commit()
        flash("Categoria de solução atualizada com sucesso!", "success")
        return redirect(url_for("admin.solutions"))

    return render_template("admin_solution_edit.html", sol=sol)


@admin.route("/solutions/<int:id>/toggle", methods=["POST"])
@login_required
def solution_toggle(id):
    sol = db.get_or_404(SolutionCategory, id)
    sol.active = not sol.active
    db.session.commit()

    flash(f"Status da solução alterado com sucesso!", "success")
    return redirect(url_for("admin.solutions"))


@admin.route("/users")
@login_required
def users():
    search = request.args.get('search', '').strip()
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.role.ilike(f'%{search}%')
            )
        )
        
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@admin.route("/users/new", methods=["GET", "POST"])
@login_required
def user_new():
    if request.method == "POST":
        first_name = request.form.get("first_name").strip()
        last_name = request.form.get("last_name").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        role = request.form.get("role")
        active = True if request.form.get("active") == "1" else False

        exists = User.query.filter_by(email=email).first()

        if exists:
            flash("Já existe um usuário cadastrado com este email/login.", "danger")
            return redirect(url_for("admin.user_new"))

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            active=active
        )

        db.session.add(user)
        db.session.commit()

        flash("Usuário cadastrado com sucesso!", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin_user_new.html")


@admin.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def user_edit(user_id):
    user = db.get_or_404(User, user_id)

    if request.method == "POST":
        user.first_name = request.form.get("first_name").strip()
        user.last_name = request.form.get("last_name").strip()
        user.email = request.form.get("email").strip().lower()
        user.role = request.form.get("role")
        user.active = True if request.form.get("active") == "1" else False

        db.session.commit()

        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("admin.users"))

    return render_template("admin_user_edit.html", user=user)


@admin.route("/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
def user_reset_password(user_id):
    user = db.get_or_404(User, user_id)
    new_password = request.form.get("new_password")

    if not new_password:
        flash("Informe uma nova senha.", "danger")
        return redirect(url_for("admin.user_edit", user_id=user.id))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    flash("Senha redefinida com sucesso!", "success")
    return redirect(url_for("admin.users"))
