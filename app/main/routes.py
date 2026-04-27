from flask import render_template, redirect, url_for, request, flash, Response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import csv
from io import StringIO
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
    category_filter = request.args.get('category', '').strip()

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

    if category_filter:
        query = query.filter(Ticket.category == category_filter)

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

@main.route("/reports", methods=["GET"])
@login_required
def reports():
    if current_user.role not in ["admin", "gestor"]:
        flash("Acesso negado. Apenas gestores e administradores podem acessar os relatórios.", "danger")
        return redirect(url_for("main.dashboard"))

    export = request.args.get("export")
    if export == "csv":
        data_inicial = request.args.get("data_inicial")
        data_final = request.args.get("data_final")
        area = request.args.get("area")

        query = Ticket.query

        if data_inicial:
            try:
                date_obj = datetime.strptime(data_inicial, "%Y-%m-%d")
                query = query.filter(Ticket.created_at >= date_obj)
            except ValueError:
                pass

        if data_final:
            try:
                date_obj = datetime.strptime(data_final, "%Y-%m-%d")
                query = query.filter(Ticket.created_at < date_obj + timedelta(days=1))
            except ValueError:
                pass

        if area:
            query = query.filter(Ticket.category == area)

        tickets = query.order_by(Ticket.created_at.desc()).all()

        # Pré-carregar o histórico de fechamento por ticket para "Fechado Por"
        closing_history = {}
        for h in TicketHistory.query.filter_by(new_status="Fechado").all():
            if h.ticket_id not in closing_history:
                closer = db.session.get(User, h.user_id)
                closing_history[h.ticket_id] = closer.full_name if closer else ""

        # Construir CSV inteiramente em memória para evitar perda de contexto SQLAlchemy
        output = StringIO()
        writer = csv.writer(output, delimiter=';')

        writer.writerow([
            "ID", "Titulo", "Area", "Linha", "Defeito",
            "Prioridade", "Status",
            "Criado Em", "Fechado Em",
            "Tempo de Atendimento (HH:MM:SS)", "Tempo de Atendimento (horas decimais)",
            "Solucao Categoria", "Solucao Descricao",
            "Criado Por", "Fechado Por"
        ])

        for t in tickets:
            defect_desc = ""
            if t.defect_category:
                defect_desc = f"{t.defect_category.code} - {t.defect_category.description}"

            creator = db.session.get(User, t.created_by)
            creator_name = creator.full_name if creator else ""

            fechado_por = closing_history.get(t.id, "")

            # Tempo de atendimento: HH:MM:SS e decimal em horas
            tempo_hhmmss = ""
            tempo_decimal = ""
            if t.closed_at and t.created_at:
                diff = t.closed_at - t.created_at
                total_seconds = int(diff.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                tempo_hhmmss = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                # Decimal com 2 casas, usando vírgula para Excel brasileiro
                tempo_decimal = f"{total_seconds / 3600:.2f}".replace(".", ",")

            # Separar solução em categoria e descrição
            # Formato salvo: "CATEGORIA - descrição texto" ou "CATEGORIA" (sem descrição)
            solucao_categoria = ""
            solucao_descricao = ""
            if t.solution:
                partes = t.solution.split(" - ", 1)
                solucao_categoria = partes[0].strip()
                solucao_descricao = partes[1].strip() if len(partes) > 1 else ""

            writer.writerow([
                t.id,
                t.title,
                t.category,
                t.station or "",
                defect_desc,
                t.priority,
                t.status,
                t.created_at.strftime("%d/%m/%Y %H:%M:%S") if t.created_at else "",
                t.closed_at.strftime("%d/%m/%Y %H:%M:%S") if t.closed_at else "",
                tempo_hhmmss,
                tempo_decimal,
                solucao_categoria,
                solucao_descricao,
                creator_name,
                fechado_por
            ])

        csv_content = "\ufeff" + output.getvalue()  # BOM para Excel reconhecer UTF-8
        filename = f"relatorio_kpi_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

        return Response(
            csv_content,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )

    return render_template("reports.html")
