from flask import Flask,render_template,flash,redirect,url_for,session,request,logging
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps
app = Flask(__name__) 
app.secret_key="lecturenotes"

class RegisterForm(Form):
    name=StringField("Name - Surname",validators=[validators.Length(min=6, max=40)])
    #username = StringField("Kullanıcı adı",validators=[validators.Length(min=6, max=30)])
    email = StringField("E-Mail",validators=[validators.email(message="Please enter a valid email address!")])
    password = PasswordField("Password",validators=[
        validators.DataRequired("Please set a password!"),
        validators.length(min=8),
        validators.EqualTo(fieldname="confirm",message="Your password does not match!")        
    ])
    confirm=PasswordField("Confirm Password")

class LoginForm(Form):
    name=StringField("User Name and Surname")
    password=PasswordField("Password")

class LectureForm(Form):
    lecture_name=StringField("Lecture Name",validators=[validators.Length(min=4, max=75)])
    content=TextAreaField("Content",validators=[validators.Length(min=8)])

def login_required(f):
    @wraps(f)
    def decorator_function(*args,**kwargs):
        if "logged_in" in session:
            return f(*args,**kwargs)
        else:
            flash("You must be logged in to view this page!!!","danger")
            return redirect(url_for("login"))
    return decorator_function

#Db connection configuration started.
app.config["MYSQL_HOST"] ="localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "lecturenotes"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)
#Db connection configuration finished.

@app.route("/")
def index():
    return render_template("index.html")
    
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/lecture/<string:id>")
def lecture(id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from lecture where id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        lecture = cursor.fetchone()
        return render_template("lecture.html",lecture=lecture)
    else:
        return render_template("lecture.html")

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if(request.method=="POST" and form.validate()):
        name=form.name.data
        email=form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu= "Insert into user(name,email,password) VALUES(%s,%s,%s) "
        cursor.execute(sorgu,(name,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("You have successfully registered...","success")
        return redirect(url_for("login"))

    else:
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if(request.method=="POST"):
        name=form.name.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        sorgu= "Select * from user where name = %s"
        result=cursor.execute(sorgu,(name,))

        if result>0:
            data=cursor.fetchone()
            real_passw=data["password"]
            if sha256_crypt.verify(password,real_passw):
                flash("You have successfully logged in...","success")
                session["logged_in"] = True
                session["name"] = name
                return redirect(url_for("index"))
            else:
                flash("You entered your password incorrectly!!!","danger")
                return redirect(url_for("login"))
        else:
            flash("There is no such user!!!","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)

@app.route("/lectures")
def lectures():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from lecture"
    result=cursor.execute(sorgu)
    if result >0:
        lectures=cursor.fetchall()
        return render_template("lectures.html",lectures=lectures)
    else:
        return render_template("lectures.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu= "Select * from lecture where uploader = %s"
    result = cursor.execute(sorgu,(session["name"],))
    if result>0:
        lectures = cursor.fetchall()
        return render_template("dashboard.html",lectures=lectures)
    else:
        return render_template("dashboard.html")

@app.route("/addlecture",methods=["GET","POST"])
@login_required
def addlecture():
    form=LectureForm(request.form)
    if request.method=="POST" and form.validate:
        lecture_name = form.lecture_name.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        sorgu="Insert into lecture (lecture_name,uploader,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(lecture_name,session["name"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Lecture Saved Successfully...","success")
        return redirect(url_for("dashboard"))
    return render_template("addlecture.html",form=form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor=mysql.connection.cursor()
    sorgu="Select * from lecture where uploader = %s and id = %s"
    result = cursor.execute(sorgu,(session["name"],id))
    if result > 0:
        sorgu2="Delete from lecture where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("There is no such course or you are not authorized for this action!","danger")
        return redirect(url_for("dashboard"))
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from lecture where  id = %s and uploader = %s "
        result = cursor.execute(sorgu,(id,session["name"]))
        if result == 0:
            flash("There is no such course or you are not authorized for this action!","danger")
            session.clear()
            return redirect(url_for("index"))
        else:
            lecture=cursor.fetchone()
            form =LectureForm()
            form.lecture_name.data = lecture["lecture_name"]
            form.content.data = lecture["content"]
            return render_template("update.html",form = form)
    else:
        form = LectureForm(request.form)
        newlname=form.lecture_name.data
        newcontent = form.content.data
        sorgu2="Update lecture Set lecture_name = %s, content = %s where id=%s"
        cursor= mysql.connection.cursor()
        cursor.execute(sorgu2,(newlname,newcontent,id))
        mysql.connection.commit()
        flash("Lecture Successfully updated!","success")
        return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    flash("You have successfully logged out...","success")
    return redirect(url_for("index"))

if __name__ =="__main__":
    app.run(debug = True)