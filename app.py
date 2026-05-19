import os
import joblib

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)
import random

from flask_mail import Mail, Message

import random

from flask import flash

from flask_mysqldb import MySQL

from werkzeug.utils import secure_filename

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

app = Flask(__name__)

# =========================================
# SECRET KEY
# =========================================
app.secret_key = 'secret123'

# =========================================
# UPLOAD FOLDER
# =========================================
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# =========================================
# MYSQL CONFIGURATION
# =========================================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'house_prediction_db'

mysql = MySQL(app)

#mail Config

# =========================================
# MAIL CONFIGURATION
# =========================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'

app.config['MAIL_PORT'] = 587

app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = 'seshathrisesha5@gmail.com'

app.config['MAIL_PASSWORD'] = 'jepe qasp keyy nqrz'

mail = Mail(app)

# =========================================
# LOAD AI MODEL
# =========================================
model = joblib.load('models/house_price_model.pkl')
encoder = joblib.load('models/area_encoder.pkl')


# =========================================
# HOME PAGE
# =========================================
@app.route('/')
def home():

    return render_template('home.html')


# =========================================
# SIGNUP
# =========================================
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        first_name = request.form['first_name']

        last_name = request.form['last_name']

        fullname = first_name + " " + last_name
        email = request.form['email']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO users(fullname, email, password)
            VALUES(%s, %s, %s)
            """,
            (
                fullname,
                email,
                hashed_password
            )
        )

        mysql.connection.commit()
        cur.close()

        return redirect('/login')

    return render_template('signup.html')


# =========================================
# LOGIN
# =========================================
# =========================================
# LOGIN
# =========================================
@app.route('/login', methods=['GET', 'POST'])
def login():

    # =====================================
    # GET REQUEST
    # =====================================

    if request.method == 'GET':

        return render_template('login.html')

    # =====================================
    # POST REQUEST
    # =====================================

    login_type = request.form.get('login_type')

    # =====================================
    # PASSWORD LOGIN
    # =====================================

    if login_type == 'password':

        email = request.form['email']

        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT * FROM users
            WHERE email=%s
            """,
            (email,)
        )

        user = cur.fetchone()

        cur.close()

        if user:

            stored_password = user[3]

            if check_password_hash(
                stored_password,
                password
            ):

                session['loggedin'] = True

                session['user_id'] = user[0]

                session['email'] = user[2]

                return redirect('/dashboard')

        return render_template(
            'login.html',
            error="Invalid Email or Password"
        )

    # =====================================
    # OTP LOGIN
    # =====================================

    elif login_type == 'otp':

        otp_email = request.form.get('otp_email')

        entered_otp = request.form.get('otp')

        # =================================
        # SEND OTP
        # =================================

        if entered_otp is None or entered_otp == '':

            # CHECK USER EXISTS

            cur = mysql.connection.cursor()

            cur.execute(
                """
                SELECT * FROM users
                WHERE email=%s
                """,
                (otp_email,)
            )

            user = cur.fetchone()

            cur.close()

            # IF USER NOT FOUND

            if not user:

                return render_template(
                    'login.html',
                    error="Please Signup First"
                )

            # GENERATE OTP

            generated_otp = str(
                random.randint(100000, 999999)
            )

            # SAVE SESSION

            session['otp'] = generated_otp

            session['otp_email'] = otp_email

            # SEND EMAIL

            msg = Message(

                'SMART PROP AI - Login OTP',

                sender=app.config['MAIL_USERNAME'],

                recipients=[otp_email]
            )

            msg.body = f"""
        Your OTP is: {generated_otp}

        Do not share this OTP.

        SMART PROP AI
        """

            mail.send(msg)

            return render_template(
                'login.html',
                otp_sent=True,
                otp_email=otp_email
            )

        # =================================
        # VERIFY OTP
        # =================================

        else:

            saved_otp = str(session.get('otp')).strip()

            saved_email = str(session.get('otp_email')).strip()

            entered_otp = str(entered_otp).strip()

            otp_email = str(otp_email).strip()

            print("Entered OTP:", entered_otp)
            print("Saved OTP:", saved_otp)

            if (
                entered_otp == saved_otp
                and
                otp_email == saved_email
            ):

                cur = mysql.connection.cursor()

                cur.execute(
                    """
                    SELECT * FROM users
                    WHERE email=%s
                    """,
                    (otp_email,)
                )

                user = cur.fetchone()

                cur.close()

                if user:

                    session['loggedin'] = True

                    session['user_id'] = user[0]

                    session['email'] = user[2]

                    # CLEAR OTP SESSION

                    session.pop('otp', None)

                    session.pop('otp_email', None)

                    return redirect('/dashboard')

                else:

                    return render_template(
                        'login.html',
                        error="User Not Found"
                    )

            return render_template(
                'login.html',
                error="Invalid OTP",
                otp_sent=True,
                otp_email=otp_email
            )

    # =====================================
    # FALLBACK
    # =====================================

    return render_template('login.html')    
# =========================================
# DASHBOARD
# =========================================
@app.route('/dashboard')
def dashboard():

    if 'loggedin' not in session:

        return redirect('/login')

    return render_template('dashboard.html')


# =========================================
# LOGOUT
# =========================================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# =========================================
# ADD PROPERTY
# =========================================
@app.route('/add-property', methods=['GET', 'POST'])
def add_property():

    if 'loggedin' not in session:

        return redirect('/login')

    if request.method == 'POST':

        house_name = request.form['house_name']
        owner_name = request.form['owner_name']
        location = request.form['location']
        price = request.form['price']

        image = request.files['image']

        filename = secure_filename(image.filename)

        os.makedirs(
            app.config['UPLOAD_FOLDER'],
            exist_ok=True
        )

        image.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )
        )

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO properties
            (
                house_name,
                owner_name,
                location,
                price,
                image,
                status
            )
            VALUES(%s, %s, %s, %s, %s, %s)
            """,
            (
                house_name,
                owner_name,
                location,
                price,
                filename,
                'pending'
            )
        )

        mysql.connection.commit()
        cur.close()

        return """
        <h2 align='center'>Property Added Successfully</h2>
        <h3 align='center'>Waiting for Admin Approval</h3>
        <center>
            <a href='/dashboard'>Go Back</a>
        </center>
        """

    return render_template('add_property.html')


# =========================================
# VIEW PROPERTIES
# =========================================
@app.route('/properties')
def properties():

    location = request.args.get('location')
    budget = request.args.get('budget')

    cur = mysql.connection.cursor()

    if location and budget:

        cur.execute(
            """
            SELECT * FROM properties
            WHERE status='approved'
            AND location LIKE %s
            AND price <= %s
            """,
            (
                '%' + location + '%',
                budget
            )
        )

    elif location:

        cur.execute(
            """
            SELECT * FROM properties
            WHERE status='approved'
            AND location LIKE %s
            """,
            (
                '%' + location + '%',
            )
        )

    elif budget:

        cur.execute(
            """
            SELECT * FROM properties
            WHERE status='approved'
            AND price <= %s
            """,
            (budget,)
        )

    else:

        cur.execute(
            """
            SELECT * FROM properties
            WHERE status='approved'
            """
        )

    all_properties = cur.fetchall()

    cur.close()

    return render_template(
        'properties.html',
        properties=all_properties
    )


# =========================================
# PROPERTY DETAILS + REVIEWS
# =========================================
@app.route('/property/<int:id>', methods=['GET', 'POST'])
def property_details(id):

    if 'loggedin' not in session:

        return """

        <html>

        <head>

            <title>Login Required</title>

            <style>

                body{
                    font-family:Arial;
                    background:#f5f7fb;
                    display:flex;
                    justify-content:center;
                    align-items:center;
                    height:100vh;
                }

                .card{
                    background:white;
                    padding:40px;
                    border-radius:12px;
                    text-align:center;
                    box-shadow:0 0 15px rgba(0,0,0,0.1);
                }

                button{
                    padding:10px 20px;
                    border:none;
                    border-radius:6px;
                    margin:10px;
                    cursor:pointer;
                    background:#0d6efd;
                    color:white;
                    font-size:16px;
                }

                a{
                    text-decoration:none;
                }

            </style>

        </head>

        <body>

            <div class='card'>

                <h1>Please Login or Signup</h1>

                <p>To View Full Property Details</p>

                <a href='/login'>
                    <button>Login</button>
                </a>

                <a href='/signup'>
                    <button>Signup</button>
                </a>

            </div>

        </body>

        </html>
        """

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        rating = request.form['rating']
        review = request.form['review']
        user_email = session['email']

        cur.execute(
            """
            INSERT INTO reviews
            (
                property_id,
                user_email,
                rating,
                review
            )
            VALUES(%s, %s, %s, %s)
            """,
            (
                id,
                user_email,
                rating,
                review
            )
        )

        mysql.connection.commit()

    cur.execute(
        """
        SELECT * FROM properties
        WHERE id=%s
        """,
        (id,)
    )

    property_data = cur.fetchone()

    cur.execute(
        """
        SELECT * FROM reviews
        WHERE property_id=%s
        """,
        (id,)
    )

    reviews = cur.fetchall()

    cur.close()

    return render_template(
        'property_details.html',
        property=property_data,
        reviews=reviews
    )


# =========================================
# SAVE FAVORITE
# =========================================
@app.route('/save-favorite/<int:property_id>')
def save_favorite(property_id):

    if 'loggedin' not in session:

        return redirect('/login')

    user_email = session['email']

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT * FROM favorites
        WHERE user_email=%s
        AND property_id=%s
        """,
        (
            user_email,
            property_id
        )
    )

    existing = cur.fetchone()

    if not existing:

        cur.execute(
            """
            INSERT INTO favorites
            (user_email, property_id)
            VALUES(%s, %s)
            """,
            (
                user_email,
                property_id
            )
        )

        mysql.connection.commit()

    cur.close()

    return redirect('/properties')


# =========================================
# MY FAVORITES
# =========================================
@app.route('/my-favorites')
def my_favorites():

    if 'loggedin' not in session:

        return redirect('/login')

    user_email = session['email']

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT properties.*
        FROM favorites
        JOIN properties
        ON favorites.property_id = properties.id
        WHERE favorites.user_email=%s
        """,
        (user_email,)
    )

    favorite_properties = cur.fetchall()

    cur.close()

    return render_template(
        'favorites.html',
        properties=favorite_properties
    )


# =========================================
# CHAT SYSTEM
# =========================================
@app.route('/chat/<int:property_id>', methods=['GET', 'POST'])
def chat(property_id):

    if 'loggedin' not in session:

        return redirect('/login')

    sender_email = session['email']

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        message = request.form['message']

        cur.execute(
            """
            INSERT INTO chats
            (
                property_id,
                sender_email,
                message
            )
            VALUES(%s, %s, %s)
            """,
            (
                property_id,
                sender_email,
                message
            )
        )

        mysql.connection.commit()

    cur.execute(
        """
        SELECT * FROM properties
        WHERE id=%s
        """,
        (property_id,)
    )

    property_data = cur.fetchone()

    cur.execute(
        """
        SELECT * FROM chats
        WHERE property_id=%s
        ORDER BY id DESC
        """,
        (property_id,)
    )

    messages = cur.fetchall()

    cur.close()

    return render_template(
        'chat.html',
        property=property_data,
        messages=messages
    )


# =========================================
# AI PREDICTION
# =========================================
@app.route('/predict', methods=['GET', 'POST'])
def predict():

    predicted_price = None
    min_price = None
    max_price = None
    error = None

    available_areas = list(encoder.classes_)

    if request.method == 'POST':

        try:

            area_name = request.form['area'].strip().lower()

            sqft = int(request.form['sqft'])
            bedrooms = int(request.form['bedrooms'])
            bathrooms = int(request.form['bathrooms'])
            rooms = int(request.form['rooms'])

            available_areas_lower = [
                area.lower()
                for area in available_areas
            ]

            if area_name in available_areas_lower:

                original_area = available_areas[
                    available_areas_lower.index(area_name)
                ]

                area = encoder.transform(
                    [original_area]
                )[0]

                prediction = model.predict([
                    [
                        area,
                        sqft,
                        bedrooms,
                        bathrooms,
                        rooms
                    ]
                ])

                predicted_price = round(prediction[0])

                min_price = predicted_price - 1000000
                max_price = predicted_price + 1000000

            else:

                error = "Service for this area not yet started"

        except Exception as e:

            print(e)

            error = "Something went wrong"

    return render_template(
        'predict.html',
        predicted_price=predicted_price,
        min_price=min_price,
        max_price=max_price,
        error=error,
        available_areas=available_areas
    )


# =========================================
# ANALYTICS
# =========================================
@app.route('/analytics')
def analytics():

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT location, price
        FROM properties
        WHERE status='approved'
        """
    )

    data = cur.fetchall()

    cur.close()

    locations = []
    prices = []

    for row in data:

        locations.append(row[0])
        prices.append(int(row[1]))

    return render_template(
        'analytics.html',
        locations=locations,
        prices=prices
    )


# =========================================
# ADMIN LOGIN
# =========================================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == 'admin123':

            session['admin'] = True

            return redirect('/admin-dashboard')

        return "Invalid Admin Credentials"

    return render_template('admin_login.html')


# =========================================
# ADMIN DASHBOARD
# =========================================
@app.route('/admin-dashboard')
def admin_dashboard():

    if 'admin' not in session:

        return redirect('/admin-login')

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT * FROM properties
        WHERE status='pending'
        """
    )

    pending_properties = cur.fetchall()

    cur.close()

    return render_template(
        'admin_dashboard.html',
        properties=pending_properties
    )


# =========================================
# APPROVE PROPERTY
# =========================================
@app.route('/approve-property/<int:id>')
def approve_property(id):

    if 'admin' not in session:

        return redirect('/admin-login')

    cur = mysql.connection.cursor()

    cur.execute(
        """
        UPDATE properties
        SET status='approved'
        WHERE id=%s
        """,
        (id,)
    )

    mysql.connection.commit()

    cur.close()

    return redirect('/admin-dashboard')


# =========================================
# DELETE PROPERTY
# =========================================
@app.route('/delete-property/<int:id>')
def delete_property(id):

    if 'admin' not in session:

        return redirect('/admin-login')

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE FROM properties
        WHERE id=%s
        """,
        (id,)
    )

    mysql.connection.commit()

    cur.close()

    return redirect('/admin-dashboard')


# =========================================
# UPDATE PROFILE
# =========================================
@app.route('/update-profile')
def update_profile():

    if 'loggedin' not in session:

        return redirect('/login')

    return f"""
    <h1 align='center'>Update Profile</h1>

    <p align='center'>
        Logged in as: {session['email']}
    </p>
    """


# =========================================
# MESSAGE CENTER
# =========================================
@app.route('/message-center')
def message_center():

    if 'loggedin' not in session:

        return redirect('/login')

    return """
    <h1 align='center'>Message Center</h1>

    <p align='center'>No New Messages</p>
    """


# =========================================
# NOTIFICATIONS
# =========================================
@app.route('/notifications')
def notifications():

    if 'loggedin' not in session:

        return redirect('/login')

    return """
    <h1 align='center'>Notifications</h1>

    <p align='center'>No Notifications Available</p>
    """


# =========================================
# FEEDBACKS
# =========================================
@app.route('/feedbacks')
def feedbacks():

    if 'loggedin' not in session:

        return redirect('/login')

    return """
    <h1 align='center'>Feedback Messages</h1>

    <p align='center'>No Feedback Messages</p>
    """


# =========================================
# MAIN
# =========================================
if __name__ == '__main__':

    app.run(debug=True)
