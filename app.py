from flask import Flask, render_template, request, session, redirect, url_for, flash
import random
from datetime import datetime, timedelta
import openai
import os
import mysql.connector
from functools import wraps

# Flask-app instellen
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Logincontrole-decorator
def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Je moet ingelogd zijn om deze pagina te bekijken.", "danger")
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

# API-sleutel instellen (gebruik dotenv voor veiligheid)
openai.api_key = os.getenv("YOUR_API_KEY")

# MySQL-configuratie
db_config = {
    'user': 'flaskuser',
    'password': '22!Graafsebaan',
    'host': '127.0.0.1',
    'database': 'flask_app'
}

# Maak verbinding met MySQL
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    print("Succesvol verbonden met de database!")
except mysql.connector.Error as err:
    print(f"Fout bij verbinden met de database: {err}")

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
    """Bekijk de lijst van cliënten."""
    if session.get('role') not in ['admin', 'superadmin', 'therapist']:
        flash("Je hebt geen toegang tot deze pagina.", "danger")
        return redirect(url_for('home'))
    
    try:
        # Query om alle cliënten op te halen
        cursor.execute("SELECT * FROM clients")
        clienten = cursor.fetchall()
    except Exception as e:
        flash(f"Er ging iets mis bij het ophalen van cliënten: {e}", "danger")
        clienten = []

    # Verwijs naar het juiste template
    return render_template('clienten.html', title="Cliënten Overzicht", clients=clienten)




@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route om in te loggen met e-mailadres en wachtwoord."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')  # Onthoud: gebruik hashing in productie!

        print(f"Loginpoging: email={email}, wachtwoord={password}")  # Debugging

        try:
            # Controleer of de gebruiker bestaat in de database
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            print(f"Gevonden gebruiker: {user}")  # Debugging

            if user:
                if password == user['password']:  # Controleer wachtwoord
                    # Zet sessie-variabelen
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']
                    flash(f"Welkom, {user['username']}!", "success")
                    return redirect(url_for('dashboards'))
                else:
                    flash("Onjuist wachtwoord. Probeer het opnieuw.", "danger")
            else:
                flash("E-mailadres niet gevonden. Probeer het opnieuw.", "danger")
        except Exception as e:
            flash(f"Er ging iets mis: {e}", "danger")
            print(f"Fout tijdens inloggen: {e}")  # Debugging

    # Render de loginpagina
    return render_template('login.html', title="Login")

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registreren van een nieuwe gebruiker."""
    if request.method == 'POST':
        # Haal gegevens uit het formulier
        email = request.form.get('email')
        password = request.form.get('password')  # Gebruik hashing in productie!
        
        # Standaardrol is 'client', behalve voor Jaime
        role = 'client'
        if email == 'jaime@ohmymood.com':
            role = 'superadmin'

        try:
            # Controleer of het e-mailadres al bestaat
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("E-mailadres is al geregistreerd.", "danger")
                return redirect(url_for('register'))

            # Voeg gebruiker toe aan de database (gebruik email als username)
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (email, email, password, role)
            )
            conn.commit()
            flash("Account succesvol aangemaakt! Je kunt nu inloggen.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Er ging iets mis: {e}", "danger")
            return redirect(url_for('register'))

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
    """Beheersmodule voor gebruikersrollen."""
    if session.get('role') != 'superadmin':
        flash("Je hebt geen toegang tot de Beheersmodule.", "danger")
        return redirect(url_for('dashboards'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        try:
            cursor.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
            conn.commit()
            flash("Rol succesvol bijgewerkt!", "success")
        except Exception as e:
            flash(f"Fout bij het bijwerken van de rol: {e}", "danger")

    cursor.execute("SELECT id, username, role FROM users")
    users = cursor.fetchall()
    return render_template('role_management.html', title="Beheersmodule", users=users)



if __name__ == "__main__":
    app.run(debug=True)
