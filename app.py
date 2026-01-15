from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from models import db, MedicinalPlant, User, Favorite
from disease_aliases import normalize_disease

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS

db.init_app(app)


# ---------- LOGIN REQUIRED DECORATOR ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------- HOME PAGE ----------
@app.route("/")
def home():
    return render_template("home.html")


# ---------- SEARCH PAGE (PROTECTED) ----------
@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    results = []
    disease = ""

    if request.method == "POST":
        disease = request.form["disease"]
        normalized = normalize_disease(disease)

        results = MedicinalPlant.query.filter(
            MedicinalPlant.disease.ilike(f"%{normalized}%")
        ).all()

    return render_template("index.html", results=results, disease=disease)


# ---------- PLANT DETAIL ----------
@app.route("/plant/<int:id>")
@login_required
def plant_detail(id):
    plant = MedicinalPlant.query.get_or_404(id)
    return render_template("plant_detail.html", plant=plant)


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = User(
            username=request.form["username"],
            password=generate_password_hash(request.form["password"])
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password, request.form["password"]):
            session["user"] = user.username
            return redirect(url_for("search"))

    return render_template("login.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ---------- ADD TO FAVORITES ----------
@app.route("/favorite/<int:plant_id>")
@login_required
def favorite(plant_id):
    user = User.query.filter_by(username=session["user"]).first()

    existing = Favorite.query.filter_by(
        user_id=user.id, plant_id=plant_id
    ).first()

    if not existing:
        fav = Favorite(user_id=user.id, plant_id=plant_id)
        db.session.add(fav)
        db.session.commit()

    return redirect(url_for("search"))


# ---------- FAVORITES ----------
@app.route("/favorites")
@login_required
def favorites():
    user = User.query.filter_by(username=session["user"]).first()

    plants = db.session.query(MedicinalPlant).join(
        Favorite, MedicinalPlant.id == Favorite.plant_id
    ).filter(Favorite.user_id == user.id).all()

    return render_template("favorites.html", plants=plants)


# ---------- RUN ----------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
