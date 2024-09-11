from flask import Flask, render_template, flash, request, redirect, url_for 
from flask_wtf import FlaskForm 
from wtforms import StringField , SubmitField , PasswordField , TextAreaField , FileField
from wtforms.validators import DataRequired , EqualTo
from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash , check_password_hash 
from flask_login import login_user , UserMixin , login_required , logout_user , current_user , LoginManager
from datetime import datetime , date
from flask_ckeditor import CKEditor
from flask_ckeditor import CKEditorField
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import uuid as uuid
import os  

app = Flask(__name__)
ckeditor = CKEditor(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'MY name is Faizan'
UPLOAD_FOLDER = os.path.join(app.root_path, 'static/images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


db = SQLAlchemy(app)
migrate = Migrate(app,db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

#FORMS
class SearchForm(FlaskForm):
    searched = StringField("Search" , validators= [ DataRequired()])
    submit = SubmitField("Submit")
    
class LoginForm(FlaskForm):
    name = StringField("Name" , validators= [ DataRequired()])
    password = PasswordField("Password" , validators= [ DataRequired()])
    submit = SubmitField("Login")
    
class UserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    about_author = TextAreaField("About_Author")
    password = PasswordField("Password", validators=[DataRequired(), EqualTo('password2',message = 'password must match')])
    password2 = PasswordField("Confirm password", validators=[DataRequired()])
    profile_pic = FileField("Profile Pic")
    submit = SubmitField("Submit")
    
    
class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    #content =TextAreaField("Content", validators=[DataRequired()])
    content = CKEditorField('Content', validators=[DataRequired()])
    #author = StringField("Author")
    slug = StringField("Slug", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
class PasswordForm(FlaskForm):
    email = StringField("What's your email", validators=[DataRequired()])
    password_hash = PasswordField("What's your password", validators=[DataRequired()])
    submit = SubmitField("Submit")

class NamerForm(FlaskForm):
    name = StringField("What's your name", validators=[DataRequired()])
    submit = SubmitField("Submit")
    
#MODELS
class Users(db.Model,UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(200),nullable=False)
    email = db.Column(db.String(120),nullable=False)
    about_author = db.Column(db.Text(500),nullable=True)
    date_added = db.Column(db.DateTime,default=datetime.utcnow)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Posts',backref='poster',lazy=True)
    profile_pic = db.Column(db.String(),nullable=True)
    
    @property 
    def password(self):
        raise AttributeError(' Password is not a readable attribute')
    
    @password.setter
    def password(self,password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self,password): 
        return check_password_hash(self.password_hash,password)

    def __repr__(self):
        return f'<name {self.name!r}>'
    
class Posts(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(225))
    content=db.Column(db.Text)
    #author = db.Column(db.String(225))
    date_posted=db.Column(db.DateTime,default=datetime.utcnow)
    slug=db.Column(db.String(225))
    poster_id=db.Column(db.Integer,db.ForeignKey('users.id'),nullable=False)
    
#ROUTES
@app.context_processor
def base():
    form = SearchForm()
    return dict(form=form)

@app.route('/search', methods=['POST'])
def search():
    form = SearchForm()
    posts = Posts.query
    return_url = request.form.get('return_url')
    
    if form.validate_on_submit():
        post_searched = form.searched.data
        if post_searched:
            posts = posts.filter(
                or_(
                    Posts.content.like('%' + post_searched + '%') ,
                    Posts.slug.like('%' + post_searched + '%') , 
                    Posts.title.like('%' + post_searched + '%') ,
                    Posts.date_posted.like('%' + post_searched + '%') 
                )
            )
            posts = posts.order_by(Posts.title).all()
        else: 
            flash('Search term cannot be empty.', 'warning')
            return redirect(return_url)
    else : 
        print('form validaton failed')
        return redirect (return_url)
    return render_template('search.html', form=form, searched= post_searched,posts=posts)

    
@app.route('/')
def index():
    flash('Welcome to our website')
   
    return render_template("index.html")

@app.route('/login', methods = ['GET' , 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(name=form.name.data).first()
        if user: 
            if check_password_hash(user.password_hash, form .password.data):
                      login_user(user)
                      flash('Login successful')
                      return redirect(url_for('dashboard'))
            else:
                      flash('Wrong Password - Try Again')
        else:
            flash('That user does not exist . try again')      
    return render_template('login.html', form = form)

@app.route('/logout',  methods = ['GET' , 'POST'])

def logout():
    logout_user()
    flash ( 'you have been logged out')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = UserForm()
    if current_user.is_authenticated:
        id = current_user.id
        name_to_update = Users.query.get_or_404(id)
        if request.method == 'POST':
            name_to_update.name = request.form['name']
            name_to_update.email = request.form['email']
            name_to_update.about_author = request.form['about_author']
            if form.profile_pic.data:
                pic_file = form.profile_pic.data
                pic_filename = secure_filename(pic_file.filename)
                pic_name = str(uuid.uuid1()) + "_" + pic_filename 
                pic_file.save(os.path.join(app.config['UPLOAD_FOLDER'], pic_name))
                name_to_update.profile_pic= pic_name
            try:
                db.session.commit()
                flash("User updated successfully")
            except Exception as e:
                db.session.rollback()
                flash(f"Error: {str(e)}")
        return render_template('dashboard.html', form=form, name_to_update=name_to_update)
    else:
        flash("You need to log in to access this page.")
        return redirect(url_for('login')) 

    
@app.route('/posts')
def posts():
    posts=Posts.query.order_by(Posts.date_posted).all()
    return render_template("posts.html",posts=posts) 

@app.route('/posts/<int:id>')
def post(id):
    post = Posts.query.get_or_404(id)
    return render_template('post.html',post=post)


@app.route('/posts/edit/<int:id>', methods = ['POST','GET'])
@login_required
def edit_post(id):
    post = Posts.query.get_or_404(id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        #post.author = form.author.data
        post.slug = form.slug.data
        post.content = form.content.data
        db.session.commit()
        flash("Post has been Updated")
        return redirect(url_for('post' , id=post.id))
    if current_user.id == post.poster_id:
        form.title.data = post.title
        #form.author.data = post.author 
        form.slug.data = post.slug 
        form.content.data = post.content
        return render_template('edit_post.html' , form = form , post=post)
    else:
        flash(" You arn't authorized to Delete that post ")
        posts = Posts.query.order_by(Posts.date_posted).all()
        return render_template("posts.html", posts=posts) 

@app.route('/posts/delete/<int:id>')
@login_required
def delete_post(id):
    post_to_delete = Posts.query.get_or_404(id)
    id = current_user.id
    if id == post_to_delete.poster_id:
        try:
            db.session.delete(post_to_delete)
            db.session.commit()
            flash('Deleted successfully')
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts=posts)
        
        except:
            flash("oops there was an problem ")
            posts = Posts.query.order_by(Posts.date_posted)
            return render_template("posts.html", posts=posts)
    else:
        flash(" You arn't authorized to Delete that post ")
        posts = Posts.query.order_by(Posts.date_posted)
        return render_template("posts.html", posts=posts)
    
@app.route('/add-post', methods = ['POST', 'GET'])
@login_required
def add_post():
    form = PostForm()
    if form.validate_on_submit():
        poster = current_user.id 
        post = Posts(title = form.title.data,content = form.content.data, poster_id=poster, slug = form.slug.data)
        form.title.data = ''
        form.content.data = ''
        #form.author.data = ''
        form.slug.data = ''
        db.session.add(post)
        db.session.commit()
        flash("Blog Post subbmitted successfully ")
        return redirect(url_for('add_post'))
    return render_template('add_post.html', form = form)
        
@app.route('/date')
def get_current_date():
    like_pizza = {
        "faizan" : "Fajita",
        "rehman" : "Cheese",
        "rizwam" : "Mushroom"
        }
    response_data = {
        "Date" : date.today(),
        "like_pizza" : like_pizza
    }
    return (response_data)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if id == current_user.id:
        user_to_delete = Users.query.get_or_404(id)
        try :
            db.session.delete(user_to_delete)
            db.session.commit()
            flash('Deleted successfully')
            return redirect(url_for('add_user'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error in db: {e}')
            return redirect(url_for('add_user'))      
    else:
        flash("Sorry you can't delete this user")
        return redirect(url_for('add_user'))
    
@app.route('/update/<int:id>', methods=['POST', 'GET'])
@login_required
def update(id):
    form= UserForm()
    name_to_update = Users.query.get_or_404(id)
    if request.method == 'POST':
        name_to_update.name = request.form['name']
        name_to_update.email = request.form['email']
        try:
            db.session.commit()
            flash("User updated successfully")
            return redirect(url_for('dashboard')) 
        except:  
            db.session.commit()
            flash("Error")
            return render_template('update.html', form=form, name_to_update=name_to_update)
    else: 
        return render_template('update.html', form=form, name_to_update=name_to_update)

@app.route('/user/add', methods=['GET', 'POST'])
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        if Users.query.filter_by(email=form.email.data).first() is None:
            user = Users(name=form.name.data, email=form.email.data)
            user.password = form.password.data 
            db.session.add(user)
            db.session.commit()
            flash('User added successfully')
        else:
            flash('User with this email already exists.')
        form.name.data = ''
        form.email.data = ''
        form.password.data = ''
        form.password2.data = ''
    our_users = Users.query.order_by(Users.date_added)
    return render_template("add_user.html", form=form, our_users=our_users)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500



if __name__ == '__main__':
    app.run(debug=True)
