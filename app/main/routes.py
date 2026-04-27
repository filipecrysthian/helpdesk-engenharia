from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.main import main
from app.models import User, Ticket, TicketHistory, DefectCategory, SolutionCategory

@main.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.tickets"))
    return redirect(url_for("auth.login"))

@main.route("/dashboard")
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

@main.route("/tickets")
@login_required
def tickets():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()

    query = Ticket.query

    if search:
        query = query.outerjoin(DefectCategory).filter(
            db.or_(
                Ticket.title.ilike(f'%{search}%'),
                Ticket.category.ilike(f'%{search}%'),
                Ticket.station.ilike(f'%{search}%'),
                DefectCategory.description.ilike(f'%{search}%'),
                DefectCategory.code.ilike(f'%{search}%')
            )
        )

    if status_filter:
        query = query.filter(Ticket.status == status_filter)

    if priority_filter:
        query = query.filter(Ticket.priority == priority_filter)

    tickets_pagination = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=15)
    
    total_tickets = Ticket.query.count()
    open_tickets = Ticket.query.filter_by(status="Aberto").count()
    progress_tickets = Ticket.query.filter_by(status="Em atendimento").count()
    closed_tickets = Ticket.query.filter_by(status="Fechado").count()
    
    return render_template(
        "tickets.html", 
        tickets=tickets_pagination.items, 
        pagination=tickets_pagination,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        progress_tickets=progress_tickets,
        closed_tickets=closed_tickets
    )

@main.route("/tickets/new", methods=["GET", "POST"])
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
        return redirect(url_for("main.tickets"))

    return render_template("ticket_new.html", defect_categories=defect_categories)

@main.route("/tickets/<int:ticket_id>", methods=["GET", "POST"])
@login_required
def ticket_detail(ticket_id):
    ticket = db.get_or_404(Ticket, ticket_id)
    creator = db.session.get(User, ticket.created_by)

    if request.method == "POST":
        if current_user.role == "solicitante":
            flash("Você não tem permissão para fechar chamados.", "danger")
            return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))

        solution_category = request.form.get("solution_category")
        solution_text = request.form.get("solution", "").strip()

        if not solution_category:
            flash("Selecione a categoria da solução.", "danger")
            return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))

        old_status = ticket.status

        ticket.status = "Fechado"
        if solution_text:
            ticket.solution = f"{solution_category} - {solution_text}"
        else:
            ticket.solution = solution_category
        ticket.closed_at = datetime.now()

        history = TicketHistory(
            ticket_id=ticket.id,
            user_id=current_user.id,
            old_status=old_status,
            new_status="Fechado",
            action="Chamado fechado"
        )

        db.session.add(history)
        db.session.commit()

        flash("Chamado fechado com sucesso!", "success")
        return redirect(url_for("main.ticket_detail", ticket_id=ticket.id))

    histories = TicketHistory.query.filter_by(ticket_id=ticket.id).order_by(TicketHistory.created_at.desc()).all()
    solution_categories = SolutionCategory.query.filter_by(active=True).order_by(SolutionCategory.description.asc()).all()

    return render_template(
        "ticket_detail.html",
        ticket=ticket,
        creator=creator,
        histories=histories,
        solution_categories=solution_categories
    )
