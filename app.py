from flask import Flask, render_template
from flask import flash, redirect, url_for, session, logging, request
#from data import Articles    #  importing articles function from data.py file
from flask_mysqldb import MySQL
from functools import wraps

from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'admin123'
app.config['MYSQL_DB'] = 'myFlaskApp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # by default a tuple is returned we want dict
# init MYSQL
#mysql = MySQL(app)

#Articles = Articles()  # function call


# Index
@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')
# All Articles
@app.route('/articles')
def articles():
     # Cursor Create
    cur = mysql.connection.cursor()

    result = cur.execute("Select * From articles")

    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    cur.close()

# Single Article
@app.route('/article/<string:id>/')     #   for indvidual article
def article(id):
    # Cursor Create
    cur = mysql.connection.cursor()

    result = cur.execute("Select * From articles Where id = %s",[id])

    article = cur.fetchone()
    return render_template('article.html', article=article)

#   Registration Form Class
class RegistrationForm(Form):
    name = StringField('Name', [validators.length(min=5,max=50)])
    username = StringField('Username', [validators.length(min=5,max=25)])
    email = StringField('Email', [validators.length(min=5,max=50)])
    password = PasswordField('Password',[
        validators.DataRequired(),
        validators.EqualTo('confirm', message="Passwords do not match")
    ])
    confirm = PasswordField('Confirm Password')

# Register User
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create cursor
        cur = mysql.connection.cursor()

        cur.execute("INSERT INTO users(name, username, email, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

        # Commit the DB
        mysql.connection.commit()

        # Close the Connection
        cur.close()

        flash("Registratered Successful, You can now Login",'Success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form) 

# Login User
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields Values
        username = request.form['username']
        password_candidate = request.form['password']

        # Creating Cursor
        cur = mysql.connection.cursor()

        # Getting user by username
        result = cur.execute("Select * From users Where username = %s", [username])

        if result > 0:
            # Get Stored Hash
            data = cur.fetchone()
            password = data['password']

            # compare Password
            if sha256_crypt.verify(password_candidate, password):
                # app.logger.info('Password Matched')
                # Login Confirmed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now Logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                # app.logger.info('Password Not Matched')
                error = 'Invalid Login'
                return render_template('login.html', error=error)
            # Connection Closed
            cur.close()
        else:
            # app.logger.info('Invalid User')
            error = 'Username not found'
            return render_template('login.html', error=error)
    return render_template('login.html')

# check that if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please Login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Dashboard
@app.route('/dashboard')
@is_logged_in  #  confirm if user login then goto dashboard
def dashboard():
    # Cursor Create
    cur = mysql.connection.cursor()

    result = cur.execute("Select * From articles")
    articles = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()

# Logout
@app.route('/logout')
@is_logged_in  #  confirm if user login then logged out
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

#   Add Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.length(min=5,max=250)])
    body = TextAreaField('Body', [validators.length(min=30)])

# Add Article
@app.route('/add_article', methods=['Get', 'POST'])
@is_logged_in  #  confirm if user login then add article
def add_article():
    form = ArticleForm(request.form)

    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
        # Create Cursor
        cur = mysql.connection.cursor()
        
        # Inserting article into database
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username'])) 

        # Commit to database
        mysql.connection.commit()
        
        # Connection Close
        cur.close()

        flash('Article Created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


# Edit Article
@app.route('/edit_article/<string:id>', methods=['Get', 'POST'])
@is_logged_in  #  confirm if user login then add article
def edit_article(id):

    # Create Cursor
    cur = mysql.connection.cursor()
     
    # Get Article by its id
    result = cur.execute("Select * From articles Where id = %s",[id])
    article = cur.fetchone()

    # Get Form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        
        # Inserting article into database
        cur.execute("Update articles Set title=%s, body=%s Where id=%s",(title, body, id)) 

        # Commit to database
        mysql.connection.commit()
        
        # Connection Close
        cur.close()

        flash('Article Updated  ', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)

# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create Cursor
    cur = mysql.connection.cursor()

    cur.execute("Delete From articles Where id = %s",[id])

    # Commit to database
    mysql.connection.commit()
        
    # Connection Close
    cur.close()

    flash('Article Deleted  ', 'success')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)