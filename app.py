import os
import joblib

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session
)

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

        fullname = request.form['fullname']

        email = request.form['email']

        password = request.form['password']

        # HASH PASSWORD
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
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

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

        return "Invalid Email or Password"

    return render_template('login.html')

# =========================================
# DASHBOARD
# =========================================
@app.route('/dashboard')
def dashboard():

    if 'loggedin' in session:

        return render_template('dashboard.html')

    return redirect('/login')

# =========================================
# LOGOUT
# =========================================
@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

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

        # CREATE FOLDER
        os.makedirs(
            app.config['UPLOAD_FOLDER'],
            exist_ok=True
        )

        # SAVE IMAGE
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
        <h2>Property Added Successfully</h2>

        <h3>Waiting for Admin Approval</h3>

        <a href='/dashboard'>Go Back</a>
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

    # LOCATION + BUDGET
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

    # ONLY LOCATION
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

    # ONLY BUDGET
    elif budget:

        cur.execute(
            """
            SELECT * FROM properties
            WHERE status='approved'
            AND price <= %s
            """,
            (
                budget,
            )
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

    cur = mysql.connection.cursor()

    # ADD REVIEW
    if request.method == 'POST':

        if 'loggedin' not in session:

            return redirect('/login')

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

    # PROPERTY DETAILS
    cur.execute(
        """
        SELECT * FROM properties
        WHERE id=%s
        """,
        (id,)
    )

    property_data = cur.fetchone()

    # REVIEWS
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
# REMOVE FAVORITE
# =========================================
@app.route('/remove-favorite/<int:property_id>')
def remove_favorite(property_id):

    if 'loggedin' not in session:

        return redirect('/login')

    user_email = session['email']

    cur = mysql.connection.cursor()

    cur.execute(
        """
        DELETE FROM favorites
        WHERE user_email=%s
        AND property_id=%s
        """,
        (
            user_email,
            property_id
        )
    )

    mysql.connection.commit()

    cur.close()

    return redirect('/my-favorites')

# =========================================
# CHAT SYSTEM
# =========================================
@app.route('/chat/<int:property_id>', methods=['GET', 'POST'])
def chat(property_id):

    if 'loggedin' not in session:

        return redirect('/login')

    sender_email = session['email']

    cur = mysql.connection.cursor()

    # SEND MESSAGE
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

    # PROPERTY
    cur.execute(
        """
        SELECT * FROM properties
        WHERE id=%s
        """,
        (property_id,)
    )

    property_data = cur.fetchone()

    # MESSAGES
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
# ANALYTICS CHART
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

        else:

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

    # PENDING PROPERTIES
    cur.execute(
        """
        SELECT * FROM properties
        WHERE status='pending'
        """
    )

    pending_properties = cur.fetchall()

    # TOTAL USERS
    cur.execute(
        """
        SELECT COUNT(*) FROM users
        """
    )

    total_users = cur.fetchone()[0]

    # TOTAL PROPERTIES
    cur.execute(
        """
        SELECT COUNT(*) FROM properties
        """
    )

    total_properties = cur.fetchone()[0]

    # APPROVED
    cur.execute(
        """
        SELECT COUNT(*) FROM properties
        WHERE status='approved'
        """
    )

    approved_properties = cur.fetchone()[0]

    # PENDING COUNT
    cur.execute(
        """
        SELECT COUNT(*) FROM properties
        WHERE status='pending'
        """
    )

    pending_count = cur.fetchone()[0]

    # REVIEWS
    cur.execute(
        """
        SELECT COUNT(*) FROM reviews
        """
    )

    total_reviews = cur.fetchone()[0]

    # FAVORITES
    cur.execute(
        """
        SELECT COUNT(*) FROM favorites
        """
    )

    total_favorites = cur.fetchone()[0]

    # CHATS
    cur.execute(
        """
        SELECT COUNT(*) FROM chats
        """
    )

    total_chats = cur.fetchone()[0]

    cur.close()

    return render_template(
        'admin_dashboard.html',
        properties=pending_properties,
        total_users=total_users,
        total_properties=total_properties,
        approved_properties=approved_properties,
        pending_count=pending_count,
        total_reviews=total_reviews,
        total_favorites=total_favorites,
        total_chats=total_chats
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
# MAIN
# =========================================
if __name__ == '__main__':

    app.run(debug=True)