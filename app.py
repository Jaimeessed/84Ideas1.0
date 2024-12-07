from flask import Flask, render_template, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
import openai
from functools import wraps
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

# Laad de .env-variabelen
load_dotenv()

# Haal de databasegegevens op
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# Maak de DATABASE_URL
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"


# Debug: print de DATABASE_URL
print("DEBUG - DATABASE_URL:", DATABASE_URL)

# Flask-app instellen
app = Flask(__name__)

# Configuratie van environment variables
app.secret_key = os.getenv("SECRET_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Maak de engine en sessie
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base voor het definiëren van tabellen
Base = declarative_base()

# Definieer modellen
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    contact = Column(String(50), nullable=False)

# Initialiseer de database (tabellen maken)
Base.metadata.create_all(bind=engine)

# Logincontrole-decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Je moet ingelogd zijn om deze pagina te bekijken.", "danger")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper


@app.route('/')
def root():
    """Stuur uitgelogde gebruikers naar home en ingelogde gebruikers naar dashboard."""
    if 'user_id' in session:
        print("Gebruiker is ingelogd, doorsturen naar dashboard.")
        return redirect(url_for('dashboards'))
    print("Gebruiker is niet ingelogd, doorsturen naar home.")
    return redirect(url_for('home'))

@app.route('/home')
def home():
    """Homepagina voor uitgelogde gebruikers."""
    if 'user_id' in session:
        return redirect(url_for('dashboards'))  # Stuur ingelogde gebruikers naar het dashboard
    return render_template('home.html', title="Welkom bij 84Ideas")

@app.route('/welkom')
@login_required
def welkom():
    """Welkom pagina voor clients."""
    if session.get('role') != 'client':
        flash("Je hebt geen toegang tot deze pagina.", "danger")
        return redirect(url_for('home'))
    return render_template('welkom.html', title="Welkom")

@app.route('/agenda')
@login_required
def agenda():
    print("Agenda route is aangeroepen")
    return render_template('agenda.html', title="Agenda")

@app.route('/videocall')
@login_required
def videocall():
    print("VideoCall route is aangeroepen")
    return render_template('videocall.html', title="VideoCall")


@app.route('/dashboards')
@login_required
def dashboards():
    """Dashboardpagina voor ingelogde gebruikers."""
    return render_template('dashboard.html', title="Dashboard")

@app.route('/ask84', methods=['GET', 'POST'])
def ask84():
    """Vraag- en antwoordpagina."""
    response = None
    if request.method == 'POST':
        question = request.form.get('question')
        try:
            openai_response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=question,
                max_tokens=150
            )
            response = openai_response['choices'][0]['text'].strip()
        except Exception as e:
            response = f"Er is een fout opgetreden: {e}"
    return render_template('ask84.html', title="Ask84", response=response)

@app.route('/clienten')
@login_required
def view_clienten():
    if session.get('role') not in ['admin', 'superadmin', 'therapist']:
        flash("Je hebt geen toegang tot deze pagina.", "danger")
        return redirect(url_for('home'))

    # Open een database sessie
    db_session = SessionLocal()  # Gebruik een andere naam dan 'session'
    try:
        # Haal alle cliënten op
        clients = db_session.query(Client).all()
    except Exception as e:
        flash(f"Er ging iets mis bij het ophalen van cliënten: {e}", "danger")
        clients = []
    finally:
        db_session.close()

    return render_template('clienten.html', title="Cliënten Overzicht", clients=clients)




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Open een database sessie
        db_session = SessionLocal()  # Gebruik een andere naam
        try:
            # Zoek de gebruiker in de database
            user = db_session.query(User).filter(User.email == email).first()

            if user and user.password == password:
                # Stel sessievariabelen in
                session['user_id'] = user.id  # Dit is Flask's session
                session['username'] = user.username
                session['role'] = user.role
                flash(f"Welkom, {user.username}!", "success")
                return redirect(url_for('dashboards'))
            else:
                flash("Onjuist e-mailadres of wachtwoord.", "danger")
        except Exception as e:
            flash(f"Er ging iets mis: {e}", "danger")
        finally:
            db_session.close()

    return render_template('login.html', title="Inloggen")




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = 'client' if email != 'jaime@ohmymood.com' else 'superadmin'

        # Open een database sessie
        session = SessionLocal()
        try:
            # Controleer of de gebruiker al bestaat
            existing_user = session.query(User).filter(User.email == email).first()
            if existing_user:
                flash("E-mailadres is al geregistreerd.", "danger")
                return redirect(url_for('register'))

            # Voeg de gebruiker toe aan de database
            new_user = User(username=email, email=email, password=password, role=role)
            session.add(new_user)
            session.commit()
            flash("Account succesvol aangemaakt! Je kunt nu inloggen.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Er ging iets mis: {e}", "danger")
        finally:
            session.close()

    # Zorg dat deze regels binnen de functie blijven!
    print("Rendering template: register.html with title='Registreren'")
    return render_template('register.html', title="Registreren")





@app.route('/logout')
def logout():
    """Uitloggen en terugkeren naar de homepagina voor uitgelogde gebruikers."""
    session.clear()  # Verwijder alle sessiegegevens
    flash("Je bent uitgelogd!", "info")
    return redirect(url_for('home'))  # Stuur door naar de uitgelogde homepagina


@app.route('/contact')
def contact():
    """Contactpagina, beschikbaar voor ingelogde en niet-ingelogde gebruikers."""
    return render_template('contact.html', title="Contact")

@app.route('/admin')
@login_required
def admin_module():
    """Admin Module."""
    if session.get('role') not in ['admin', 'superadmin']:
        flash("Je hebt geen toegang tot de Admin Module.", "danger")
        return redirect(url_for('dashboards'))
    return render_template('admin.html', title="Admin Module")

@app.route('/role-management', methods=['GET', 'POST'])
@login_required
def role_management():
    if session.get('role') != 'superadmin':
        flash("Je hebt geen toegang tot de Beheersmodule.", "danger")
        return redirect(url_for('dashboards'))

    # Open een database sessie
    db_session = SessionLocal()  # Gebruik een unieke naam
    try:
        if request.method == 'POST':
            user_id = request.form.get('user_id')
            new_role = request.form.get('new_role')

            # Update de rol van de gebruiker
            user = db_session.query(User).filter(User.id == user_id).first()
            if user:
                user.role = new_role
                db_session.commit()
                flash("Rol succesvol bijgewerkt!", "success")
            else:
                flash("Gebruiker niet gevonden.", "danger")

        # Haal alle gebruikers op
        users = db_session.query(User).all()
    except Exception as e:
        flash(f"Fout bij het beheren van rollen: {e}", "danger")
        users = []
    finally:
        db_session.close()

    return render_template('role_management.html', title="Beheersmodule", users=users)




if __name__ == "__main__":
    app.run(debug=True)
