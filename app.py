from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret123'  # Para sessões simples
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///reservas.db'
db = SQLAlchemy(app)

# Modelos


class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)


class Sala(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)


class Recurso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)


class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey(
        'usuario.id'), nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey('sala.id'), nullable=False)
    recurso_id = db.Column(
        db.Integer, db.ForeignKey('recurso.id'), nullable=True)
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)

    usuario = db.relationship('Usuario')
    sala = db.relationship('Sala')
    recurso = db.relationship('Recurso')


# Criação inicial dos dados (executa ao iniciar o app)
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin', password='admin')
        db.session.add(admin)
    if not Sala.query.first():
        db.session.add_all([
            Sala(nome='Sala de Reunião 1'),
            Sala(nome='Laboratório de Informática'),
            Sala(nome='Sala de Aula 101'),
        ])
    if not Recurso.query.first():
        db.session.add_all([
            Recurso(nome='Projetor'),
            Recurso(nome='Notebook'),
            Recurso(nome='Caixa de Som'),
        ])
    db.session.commit()

# Rotas


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('reservas'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(
            username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('reservas'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado.', 'info')
    return redirect(url_for('login'))


@app.route('/reservas')
def reservas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    reservas = Reserva.query.order_by(Reserva.data_hora_inicio).all()
    return render_template('reservas.html', reservas=reservas)


@app.route('/reservar', methods=['GET', 'POST'])
def reservar():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    salas = Sala.query.all()
    recursos = Recurso.query.all()

    if request.method == 'POST':
        sala_id = int(request.form['sala'])
        recurso_id = request.form.get('recurso')
        recurso_id = int(recurso_id) if recurso_id else None
        inicio_str = request.form['inicio']
        fim_str = request.form['fim']

        try:
            inicio = datetime.strptime(inicio_str, '%Y-%m-%dT%H:%M')
            fim = datetime.strptime(fim_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Formato de data/hora inválido.', 'danger')
            return redirect(url_for('reservar'))

        if fim <= inicio:
            flash('Data e hora fim devem ser após o início.', 'danger')
            return redirect(url_for('reservar'))

        # Verifica conflito para a mesma sala
        conflito = Reserva.query.filter(
            Reserva.sala_id == sala_id,
            Reserva.data_hora_inicio < fim,
            Reserva.data_hora_fim > inicio
        ).first()

        if conflito:
            flash('Já existe uma reserva para essa sala nesse horário.', 'danger')
            return redirect(url_for('reservar'))

        reserva = Reserva(
            usuario_id=session['user_id'],
            sala_id=sala_id,
            recurso_id=recurso_id,
            data_hora_inicio=inicio,
            data_hora_fim=fim
        )
        db.session.add(reserva)
        db.session.commit()
        flash('Reserva cadastrada com sucesso!', 'success')
        return redirect(url_for('reservas'))

    return render_template('reservar.html', salas=salas, recursos=recursos)


@app.route('/salas')
def salas():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    salas = Sala.query.all()
    return render_template('salas.html', salas=salas)


@app.route('/recursos')
def recursos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    recursos = Recurso.query.all()
    return render_template('recursos.html', recursos=recursos)


@app.route('/excluir_reserva/<int:reserva_id>', methods=['POST'])
def excluir_reserva(reserva_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    reserva = Reserva.query.get_or_404(reserva_id)
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva excluída com sucesso!', 'success')
    return redirect(url_for('reservas'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
