from ast import Pass
from email.utils import parseaddr
import hashlib
from tokenize import String
from wsgiref.validate import validator
from colorama import Cursor
from flask import Flask, message_flashed,render_template,flash,redirect,url_for,session,logging,request,g
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps


# Kullanıcı Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu Sayfası Görüntülemek İçin Lütfen Giriş Yapınız","danger")
            return redirect(url_for("login"))
    return decorated_function

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators =[validators.Length(min =4, max =25)])
    username = StringField("Kullanıcı Adı", validators =[validators.Length(min =5, max =15)])
    email = StringField("Email Adresi", validators =[validators.Email(message="Lütfen Geçerli Bir Email Adresi Giriniz")])
    password = PasswordField("Parola", validators=[
        validators.data_required(message= "Lütfen Bir Parola Belirleyiniz"),
        validators.equal_to(fieldname="confirm",message = "Parolanız Uyuşmuyor"),
        validators.Length(min =6, max =20)
    ])
    confirm = PasswordField("Parola Doğrula")
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key = "cnbblogsecret"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "user"
app.config["MYSLQ_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# Kayıt Olma
@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        cursor = mysql.connection.cursor()
        #sql veritabanına eklemek için kullanılan kısım
        sorgu = "Insert into user(name,username,email,password) VALUES(%s,%s,%s,%s)"
        #sql veritabanına eklemek için kullanılan sorgu

        cursor.execute(sorgu,(name,username,email,password))
        #sorgulamak için kullandığımı satır
        
        mysql.connection.commit()
        #Veritabanı üzerinde değişiklik ve güncelleme yaptığın zaman kullanman gerekiyor
        
        cursor.close()
        #cursor'ı kapatman gerekiyor yoksa hata verir
        
        flash("Başarıyla Kayıt Oldunuz...","success")
        #message için flash kullanıyoruz.

        return redirect(url_for("login"))
        #redirect ile index sayfasına yönlendiriliyor.
    else:
        return render_template("register.html",form = form)

#login İşlemi
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username  = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()
        #Veritabanı üzerinde işlem yapmamız için cursor oluşturuyoruz.

        sorgu = "SELECT * from user where username = %s"

        result = cursor.execute(sorgu,(username,))
        #Demet şeklinde vermemiz gerektiği için "," ile bitiriyoruz.
        if result > 0:
            data = cursor.fetchone()
            #Kullanıcıların tüm bilgilerini fetchone ile direkt alabiliriz.
            old_pass = data[4]
            if sha256_crypt.verify(password_entered,old_pass):
                #verify fonksiyonu ile passwordleri direkt kontrol edebiliyoruz.
                flash("Başarıyla Giriş Yaptınız...","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Parolarınızı Yanlış Girdiniz...","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir  kullanıcı bulunmuyor...","danger")
            return redirect(url_for("login"))
    return render_template("login.html",form = form)

#Logout İşlemleri
@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış Yaptınız","danger")
    return redirect(url_for("index"))

#Dashboard işlemleri
@app.route("/dashboard")
@login_required
#decorator çağırmak için yukarıda yazdığımız login_required'i çağırıyoruz.
def dashboard():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")


#Bilgi Ekleme
@app.route("/addarticle",methods = ["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        #Veritabanı üzerinde işlem yapmamız için cursor oluşturuyoruz.

        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        usernameaddarticle = session["username"]
        cursor.execute(sorgu,(title,usernameaddarticle,content,))

        mysql.connection.commit()

        cursor.close()

        flash("Başarıyla Eklediniz", "success")

        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form)
class ArticleForm(Form):
    title = StringField("Başlığınız",validators=[validators.length(min = 5,max = 100)])
    content = TextAreaField("İçerik",validators =[validators.Length(min = 10)])

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)
    
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")


#Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where id = %s"
    
    result = cursor.execute(sorgu,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html")
#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu  = "Select * From articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"])) 
        if result == 0:
            flash("Böyle bir Metin bulunmamaktadır","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()
            #Formumuz articleform'dan aldığımız için eski bilgiler direkt olarak gelir.
            form.title.data = article[1]
            form.content.data = article[3]
            return render_template("update.html",form = form)
    else:
        #POST REQUEST
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        
        sorgu2 = "Update articles Set title = %s,content = %s where id = %s"
        
        cursor = mysql.connection.cursor()

        cursor.execute(sorgu2,(newTitle,newContent,id))

        mysql.connection.commit()

        flash("Metniniz başarıyla güncellendi","success")

        return redirect(url_for("dashboard"))

#Silme Sayfası        
@app.route("/delete/<string:id>")
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles where author = %s and id = %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result > 0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir Metin bulunmamaktadır.","danger")
        return redirect(url_for("index"))

#Arama URL
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        #search bar üzerinde alan değeri almak için kullanıyoruz.

        cursor = mysql.connection.cursor()

        sorgu = "Select * from articles where title like '%" + keyword + "%'"
        #Title'in içerisinde geçen keyword(kullanıcıdan aldığımız search yazısı) geçen kelimeleri getiriyor.

        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)
 
if __name__ == "__main__":
    app.run(debug=True)
