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
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="solicitante")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(80), nullable=False)
    priority = db.Column(db.String(30), nullable=False, default="Média")
    status = db.Column(db.String(30), nullable=False, default="Aberto")
    model = db.Column(db.String(80))
    station = db.Column(db.String(80))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_admin_user():
    admin = User.query.filter_by(username="admin").first()

    if not admin:
        admin = User(
            name="Administrador",
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Usuário admin criado: admin / admin123")


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Usuário ou senha inválidos.", "danger")

    return render_template("login.html")


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
    all_tickets = Ticket.query.order_by(
    Ticket.status.asc(),
    Ticket.priority.desc(),
    Ticket.created_at.asc()
    ).all()
    return render_template("tickets.html", tickets=all_tickets)


@app.route("/tickets/new", methods=["GET", "POST"])
@login_required
def ticket_new():
    if request.method == "POST":
        ticket = Ticket(
            title=request.form.get("title"),
            description=request.form.get("description"),
            category=request.form.get("category"),
            priority=request.form.get("priority"),
            model=request.form.get("model"),
            station=request.form.get("station"),
            created_by=current_user.id
        )

        db.session.add(ticket)
        db.session.commit()

        flash("Chamado criado com sucesso!", "success")
        return redirect(url_for("tickets"))

    return render_template("ticket_new.html")


@app.route("/tickets/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template("ticket_detail.html", ticket=ticket)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_admin_user()

    app.run(debug=True)