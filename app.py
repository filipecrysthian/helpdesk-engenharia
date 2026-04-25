from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from datetime import datetime
import os

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs("instance", exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(30), nullable=False, default="solicitante")

    active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_active(self):
        return self.active


class DefectCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    area = db.Column(db.String(80), nullable=False)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(80), nullable=False)
    defect_category_id = db.Column(db.Integer, db.ForeignKey("defect_category.id"), nullable=True)
    defect_category = db.relationship("DefectCategory")
    priority = db.Column(db.String(30), nullable=False, default="Média")
    status = db.Column(db.String(30), nullable=False, default="Aberto")
    station = db.Column(db.String(80))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now)
    closed_at = db.Column(db.DateTime, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_admin_user():
    admin = User.query.filter_by(email="admin@empresa.com").first()

    if not admin:
        admin = User(
            first_name="Administrador",
            last_name="Sistema",
            email="admin@empresa.com",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            active=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin@empresa.com / admin123")


def create_default_defect_categories():
    default_defects = [
        ("TST001", "PLACA PCI MB NÃO LIGA", "Engenharia de Teste"),
        ("TST002", "PLACA SEM VÍDEO NO LCD", "Engenharia de Teste"),
        ("TST002A", "PLACA SEM VÍDEO NO HDMI", "Engenharia de Teste"),

        ("SMT001", "NXT PARADA", "Engenharia SMT"),
        ("SMT002", "FEEDER COM DEFEITO", "Engenharia SMT"),
        ("SMT002A", "FEEDER TRAVADO", "Engenharia SMT"),

        ("PRC001", "FALHA DE IMPRESSÃO", "Engenharia de Processo"),
        ("PRC002", "TIRAR TEMPO DA ESTEIRA", "Engenharia de Processo"),
        ("PRC002A", "AJUSTAR VELOCIDADE DA ESTEIRA", "Engenharia de Processo"),
    ]

    for code, description, area in default_defects:
        exists = DefectCategory.query.filter_by(code=code).first()
        if not exists:
            defect = DefectCategory(
                code=code,
                description=description,
                area=area
            )
            db.session.add(defect)

    db.session.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
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
            return redirect(url_for("dashboard"))

        flash("Email ou senha inválidos.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name").strip()
        last_name = request.form.get("last_name").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        allowed_domains = ["@empresa", "@digiboard"]

        if not any(domain in email for domain in allowed_domains):
            flash("Email inválido. Utilize um email corporativo valido.", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("As senhas não conferem.", "danger")
            return redirect(url_for("register"))

        exists = User.query.filter_by(email=email).first()

        if exists:
            flash("Já existe um usuário cadastrado com este email.", "danger")
            return redirect(url_for("register"))

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
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter_by(status="Aberto").count()
    progress_tickets = Ticket.query.filter_by(status="Em atendimento").count()
    closed_tickets = Ticket.query.filter_by(status="Fechado").count()

    return render_template(
        "dashboard.html",
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        progress_tickets=progress_tickets,
        closed_tickets=closed_tickets
    )


@app.route("/tickets")
@login_required
def tickets():
    all_tickets = Ticket.query.order_by(Ticket.created_at.asc()).all()
    return render_template("tickets.html", tickets=all_tickets)


@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    defect_categories = DefectCategory.query.filter_by(active=True).order_by(DefectCategory.code.asc()).all()

    if request.method == "POST":
        ticket = Ticket(
            title=request.form.get("title"),
            description=request.form.get("description"),
            category=request.form.get("category"),
            defect_category_id=request.form.get("defect_category_id"),
            priority=request.form.get("priority"),
            station=request.form.get("station"),
            created_by=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        flash("Chamado criado com sucesso!", "success")
        return redirect(url_for("tickets"))

    return render_template("ticket_new.html", defect_categories=defect_categories)


@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template("ticket_detail.html", ticket=ticket)


@app.route("/admin/defects", methods=["GET", "POST"])
@login_required
def admin_defects():
    if current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard"))

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

        return redirect(url_for("admin_defects"))

    defects = DefectCategory.query.order_by(
        DefectCategory.area.asc(),
        DefectCategory.code.asc()
    ).all()

    return render_template("admin_defects.html", defects=defects)


@app.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard"))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/new", methods=["GET", "POST"])
@login_required
def admin_user_new():
    if current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard"))

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
            return redirect(url_for("admin_user_new"))

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
        return redirect(url_for("admin_users"))

    return render_template("admin_user_new.html")


@app.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def admin_user_edit(user_id):
    if current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.first_name = request.form.get("first_name").strip()
        user.last_name = request.form.get("last_name").strip()
        user.email = request.form.get("email").strip().lower()
        user.role = request.form.get("role")
        user.active = True if request.form.get("active") == "1" else False

        db.session.commit()

        flash("Usuário atualizado com sucesso!", "success")
        return redirect(url_for("admin_users"))

    return render_template("admin_user_edit.html", user=user)


@app.route("/admin/users/<int:user_id>/reset-password", methods=["POST"])
@login_required
def admin_user_reset_password(user_id):
    if current_user.role != "admin":
        flash("Acesso negado.", "danger")
        return redirect(url_for("dashboard"))

    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password")

    if not new_password:
        flash("Informe uma nova senha.", "danger")
        return redirect(url_for("admin_user_edit", user_id=user.id))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    flash("Senha redefinida com sucesso!", "success")
    return redirect(url_for("admin_users"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_user()
        create_default_defect_categories()

    app.run(debug=True)