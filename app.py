from cs50 import SQL
from waitress import serve
from flask import Flask, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from re import match


# Connecting to sqlite
db = SQL("sqlite:///chef.db")

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# mail regex
pattern = r"[A-Za-z0-9\._%+\-]+@[A-Za-z0-9\.\-]+\.[A-Za-z]{2,}"

def login_required(f):
    """
    Decorate routes to require login.
    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.
        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

@app.errorhandler(404)
def notfound(e):
    return apology("are you lost my friend?", 404)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET","POST"])
def login():

    # forgot user
    session.clear()

    if request.method == "POST":
        usr = request.form.get("username")
        pas = request.form.get("password")

        if not usr:
            return apology("must provide username", 403)
        elif not pas:
            return apology("must provide password", 403)

        rows = db.execute("SELECT * FROM users WHERE username = ?", usr)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], pas
        ):
            return apology("invalid username and/or password", 403)
        
        session["user_id"] = rows[0]["id"]

        return redirect("/dashboard")

    else:
        return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    
    # forgot user
    session.clear()

    if request.method == "POST":
        usr = request.form.get("username")
        pas = request.form.get("password")
        cnf = request.form.get("confirmation")
        typ = request.form.get("accounttype")

        if not usr:
            return apology("must provide username", 400)
        elif not pas:
            return apology("must provide password", 400)
        elif not typ:
            return apology("must provide account type", 400)
        elif len(pas) < 8:
            return apology("password length should be atleast 8 chars!", 400)
        elif cnf != pas:
            return apology("passwords do not match!", 400)
        
        has = generate_password_hash(pas, method='pbkdf2', salt_length=16)
        try:
            db.execute("INSERT INTO users (username, type, hash) VALUES(?, ?, ?)", usr, typ, has)
        except ValueError:
            return apology("username already taken !")

        return redirect("/login")
    
    else:
        return render_template("register.html")


@app.route("/browse")
def browse():
    query = db.execute("SELECT * FROM chef")
    length = len(query)
    try:
        usrid = session['user_id']
    except KeyError:
        usrid = 'browse'
    users = [query[i]['id'] for i in range(length)]
    user = db.execute("SELECT * FROM users WHERE id IN (?)", users)
    usernames = [] 
    userids = []
    for i in range(length):
        usernames.append(user[i]['username'])
        userids.append(user[i]['id'])
    return render_template("browse.html", query=query, user=user, length=length, usernames=usernames, userids=userids, usrid=usrid)


@app.route("/profile", methods=["GET","POST"])
def profile():
    if request.method == 'POST':
        try:
            usrid = session['user_id']
        except KeyError:
            usrid = 'browse'
        db.execute("UPDATE investor SET contacted = contacted + 1 WHERE id = ?", usrid)
    
    else:
        profileid = request.args.get("profile", None)
        invid = request.args.get("id")
        if not invid == 'browse':
            db.execute("UPDATE investor SET viewed = viewed + 1 WHERE id = ?", invid)
        if profileid == None:
            return redirect("/")
        else:
            rows = db.execute("SELECT * FROM users WHERE username = ?", profileid)
            db.execute("UPDATE chef SET views = views + 1 WHERE id = ?", rows[0]['id'])
            query = db.execute("SELECT * FROM chef WHERE id = ?", rows[0]['id'])
            return render_template("profile.html", query=query, userid=profileid)


@app.route("/dashboard", methods=["GET","POST"])
@login_required
def dashboard():
    if request.method == "POST":
        usrid = session["user_id"]
        rows = db.execute("SELECT * FROM users WHERE id = ?", usrid)
        if rows[0]['type'] == 1:
            intro = request.form.get("introduction")
            wage = request.form.get("wage")
            sts = request.form.get("status")
            exp = request.form.get("experience")
            mail = request.form.get("email")

            if not match(pattern, mail):
                return apology("Please enter a valid email", 403)
            elif len(sts) > 22:
                return apology("You have exceeded the maximum length of status", 400)
            
            db.execute("UPDATE chef SET status = ?, intro = ?, wage = ?, exp = ?, mail = ? WHERE id = ?", sts, intro, wage, exp, mail, usrid)

            return redirect("/dashboard")
        else:
            bal = request.form.get("balance")
            thr = request.form.get("tohire")

            try:
                thr = int(thr)
                bal = int(bal)
            except ValueError:
                return apology("value should be integer!", 400)

            if int(thr) < 0 or int(bal) < 0:
                return apology("enter a valid amount", 400)
            
            db.execute("UPDATE investor SET balance = ?, tohire = ? WHERE id = ?", bal, thr, usrid)

            return redirect("/dashboard")

    else:
        usrid = session["user_id"]
        rows = db.execute("SELECT * FROM users WHERE id = ?", usrid)
        try:
            if rows[0]['type'] == 1:
                try:
                    db.execute("INSERT INTO chef VALUES(?, ?, ?, ?, ?, ?, ?)", usrid, 'Unemployed', 'Hello!', 0, 0, 'Empty', 0)
                except ValueError:
                    pass
                query = db.execute("SELECT * FROM chef WHERE id = ?", usrid)
                return render_template("chef.html", query=query)
            else:
                try:
                    db.execute("INSERT INTO investor VALUES(?, ?, ?, ?, ?)", usrid, 0, 0, 0, 0)
                except ValueError:
                    pass
                query = db.execute("SELECT * FROM investor WHERE id = ?", usrid)
                return render_template("investor.html", query=query)
        except IndexError:
            return apology("Server error, delete existing sessions!", 500)


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == "POST":

        usrid = session["user_id"]
        pas = request.form.get("password")
        cnf = request.form.get("confirmation")

        if not pas:
            return apology("must provide password", 403)
        elif len(pas) < 8:
            return apology("password length should be atleast 8 chars!", 400)
        elif cnf != pas:
            return apology("passwords do not match!", 403)

        has = generate_password_hash(pas, method='pbkdf2', salt_length=16)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", has, usrid)
        session.clear()
        return redirect("/login")
    else:
        return render_template("change.html")
    

@app.route("/logout")
@login_required
def logout():
    """Log user out"""
    
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=5000)
