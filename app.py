from flask import Flask, render_template, request, redirect, url_for, session, flash
import boto3
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
import uuid
from datetime import datetime
from decimal import Decimal

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'stocker-secret-key-2024')

# ─── AWS CONFIG ───────────────────────────────────────────
AWS_REGION     = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')

# ─── LOCAL TESTING STORAGE ────────────────────────────────
LOCAL_USERS        = {}
LOCAL_PORTFOLIO    = {}
LOCAL_TRANSACTIONS = []

# ─── AWS CONNECTION ───────────────────────────────────────
def get_dynamodb():
    if AWS_ACCESS_KEY.strip() and len(AWS_ACCESS_KEY.strip()) > 10:
        return boto3.resource(
            'dynamodb',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
    return None

def get_sns():
    if AWS_ACCESS_KEY.strip() and len(AWS_ACCESS_KEY.strip()) > 10:
        return boto3.client(
            'sns',
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
    return None

# ─── SNS TOPIC ARNs ───────────────────────────────────────
USER_ACCOUNT_TOPIC_ARN = os.getenv('USER_ACCOUNT_TOPIC_ARN', '')
TRANSACTION_TOPIC_ARN  = os.getenv('TRANSACTION_TOPIC_ARN', '')

# ─── SNS NOTIFICATION ─────────────────────────────────────
def send_notification(topic_arn, subject, message):
    try:
        sns = get_sns()
        if sns and topic_arn:
            sns.publish(TopicArn=topic_arn, Subject=subject, Message=message)
    except Exception as e:
        print(f"SNS Error: {e}")

# ─── MOCK STOCK DATA ──────────────────────────────────────
MOCK_STOCKS = [
    {'id': 'AAPL', 'symbol': 'AAPL', 'name': 'Apple Inc.',      'price': Decimal('178.50'), 'market_cap': Decimal('2800000000000'), 'sector': 'Technology', 'industry': 'Consumer Electronics', 'date_added': '2024-01-01'},
    {'id': 'GOOGL','symbol': 'GOOGL','name': 'Alphabet Inc.',    'price': Decimal('141.80'), 'market_cap': Decimal('1800000000000'), 'sector': 'Technology', 'industry': 'Internet Services',    'date_added': '2024-01-01'},
    {'id': 'MSFT', 'symbol': 'MSFT', 'name': 'Microsoft Corp.',  'price': Decimal('378.90'), 'market_cap': Decimal('2810000000000'), 'sector': 'Technology', 'industry': 'Software',             'date_added': '2024-01-01'},
    {'id': 'AMZN', 'symbol': 'AMZN', 'name': 'Amazon.com Inc.',  'price': Decimal('178.25'), 'market_cap': Decimal('1850000000000'), 'sector': 'Consumer',   'industry': 'E-Commerce',           'date_added': '2024-01-01'},
    {'id': 'TSLA', 'symbol': 'TSLA', 'name': 'Tesla Inc.',       'price': Decimal('177.90'), 'market_cap': Decimal('565000000000'),  'sector': 'Automotive', 'industry': 'Electric Vehicles',    'date_added': '2024-01-01'},
    {'id': 'META', 'symbol': 'META', 'name': 'Meta Platforms',   'price': Decimal('484.10'), 'market_cap': Decimal('1240000000000'), 'sector': 'Technology', 'industry': 'Social Media',         'date_added': '2024-01-01'},
    {'id': 'NFLX', 'symbol': 'NFLX', 'name': 'Netflix Inc.',     'price': Decimal('605.00'), 'market_cap': Decimal('265000000000'),  'sector': 'Technology', 'industry': 'Streaming',            'date_added': '2024-01-01'},
    {'id': 'NVDA', 'symbol': 'NVDA', 'name': 'NVIDIA Corp.',     'price': Decimal('495.00'), 'market_cap': Decimal('1220000000000'), 'sector': 'Technology', 'industry': 'Semiconductors',       'date_added': '2024-01-01'},
]

# ─── AI SUGGESTION ────────────────────────────────────────
def get_ai_suggestion(portfolio):
    if not portfolio:
        return "💡 Start investing! AAPL and MSFT are strong picks for beginners."
    symbols = [p['stock_id'] for p in portfolio]
    if 'TSLA' in symbols and len(symbols) < 3:
        return "⚡ Your TSLA holding is volatile. Consider diversifying into MSFT or GOOGL."
    if len(symbols) == 1:
        return "📊 You have only 1 stock! Diversify across sectors to reduce risk."
    if len(symbols) >= 5:
        return "🏆 Excellent diversification! Your portfolio looks strong and balanced."
    if 'NVDA' in symbols:
        return "🤖 NVDA is an AI-era powerhouse! Consider adding MSFT for cloud exposure."
    return "✅ Good portfolio! Keep monitoring market trends and rebalance regularly."

# ═══════════════════════════════════════════════════════════
#  ROUTES
# ═══════════════════════════════════════════════════════════

# ── INDEX ─────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── SIGNUP ────────────────────────────────────────────────
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = request.form['password']
        role     = request.form.get('role', 'trader')

        db = get_dynamodb()

        if db:
            # AWS Mode
            table    = db.Table('stocker_users')
            existing = table.get_item(Key={'email': email}).get('Item')
            if existing:
                flash('Email already registered!', 'danger')
                return redirect(url_for('signup'))
            table.put_item(Item={
                'email':      email,
                'username':   username,
                'password':   generate_password_hash(password),
                'role':       role,
                'is_active':  True,
                'created_at': datetime.now().isoformat()
            })
        else:
            # Local Mode
            if email in LOCAL_USERS:
                flash('Email already registered!', 'danger')
                return redirect(url_for('signup'))
            LOCAL_USERS[email] = {
                'email':     email,
                'username':  username,
                'password':  generate_password_hash(password),
                'role':      role,
                'is_active': True
            }

        send_notification(
            USER_ACCOUNT_TOPIC_ARN,
            'New User Signup - Stocker',
            f'New user registered!\nUsername: {username}\nEmail: {email}\nRole: {role}'
        )
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

# ── LOGIN ─────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        db   = get_dynamodb()
        user = None

        if db:
            # AWS Mode
            table = db.Table('stocker_users')
            user  = table.get_item(Key={'email': email}).get('Item')
        else:
            # Local Mode
            user = LOCAL_USERS.get(email)

        if user and check_password_hash(user['password'], password):
            session['email']    = email
            session['username'] = user['username']
            session['role']     = user['role']

            send_notification(
                USER_ACCOUNT_TOPIC_ARN,
                'User Login - Stocker',
                f'User logged in!\nUsername: {user["username"]}\nEmail: {email}'
            )

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('trader_dashboard'))

        flash('Invalid email or password!', 'danger')
    return render_template('login.html')

# ── LOGOUT ────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# ── ADMIN DASHBOARD ───────────────────────────────────────
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db    = get_dynamodb()
    users = []
    txns  = []

    if db:
        users = db.Table('stocker_users').scan().get('Items', [])
        txns  = db.Table('stocker_transactions').scan().get('Items', [])
    else:
        users = list(LOCAL_USERS.values())
        txns  = LOCAL_TRANSACTIONS

    return render_template('admin_dashboard.html', users=users, transactions=txns)

# ── TRADER DASHBOARD ──────────────────────────────────────
@app.route('/dashboard')
def trader_dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    db        = get_dynamodb()
    portfolio = []
    txns      = []

    if db:
        portfolio = db.Table('stocker_portfolio').query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(session['email'])
        ).get('Items', [])
        txns = db.Table('stocker_transactions').scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('user_id').eq(session['email'])
        ).get('Items', [])
    else:
        portfolio = list(LOCAL_PORTFOLIO.get(session['email'], {}).values())
        txns      = [t for t in LOCAL_TRANSACTIONS if t['user_id'] == session['email']]

    suggestion = get_ai_suggestion(portfolio)

    return render_template('trader_dashboard.html',
                           portfolio=portfolio,
                           transactions=txns,
                           stocks=MOCK_STOCKS,
                           suggestion=suggestion)

# ── BUY STOCK ─────────────────────────────────────────────
@app.route('/buy', methods=['POST'])
def buy_stock():
    if 'email' not in session:
        return redirect(url_for('login'))

    stock_id = request.form['stock_id']
    quantity = int(request.form['quantity'])
    stock    = next((s for s in MOCK_STOCKS if s['id'] == stock_id), None)

    if not stock:
        flash('Stock not found!', 'danger')
        return redirect(url_for('trader_dashboard'))

    price = stock['price']
    db    = get_dynamodb()

    if db:
        # AWS Mode
        db.Table('stocker_transactions').put_item(Item={
            'id':               str(uuid.uuid4()),
            'user_id':          session['email'],
            'stock_id':         stock_id,
            'action':           'buy',
            'price':            price,
            'quantity':         quantity,
            'status':           'completed',
            'transaction_date': datetime.now().isoformat()
        })
        port_table = db.Table('stocker_portfolio')
        existing   = port_table.get_item(
            Key={'user_id': session['email'], 'stock_id': stock_id}
        ).get('Item')

        if existing:
            new_qty = existing['quantity'] + quantity
            new_avg = ((existing['average_price'] * existing['quantity']) + (price * quantity)) / new_qty
            port_table.update_item(
                Key={'user_id': session['email'], 'stock_id': stock_id},
                UpdateExpression='SET quantity = :q, average_price = :a',
                ExpressionAttributeValues={':q': new_qty, ':a': new_avg}
            )
        else:
            port_table.put_item(Item={
                'user_id':       session['email'],
                'stock_id':      stock_id,
                'quantity':      quantity,
                'average_price': price
            })
    else:
        # Local Mode
        LOCAL_TRANSACTIONS.append({
            'id':               str(uuid.uuid4()),
            'user_id':          session['email'],
            'stock_id':         stock_id,
            'action':           'buy',
            'price':            price,
            'quantity':         quantity,
            'status':           'completed',
            'transaction_date': datetime.now().isoformat()
        })
        user_portfolio = LOCAL_PORTFOLIO.setdefault(session['email'], {})
        if stock_id in user_portfolio:
            existing = user_portfolio[stock_id]
            new_qty  = existing['quantity'] + quantity
            new_avg  = ((existing['average_price'] * existing['quantity']) + (price * quantity)) / new_qty
            user_portfolio[stock_id]['quantity']      = new_qty
            user_portfolio[stock_id]['average_price'] = new_avg
        else:
            user_portfolio[stock_id] = {
                'user_id':       session['email'],
                'stock_id':      stock_id,
                'quantity':      quantity,
                'average_price': price
            }

    send_notification(
        TRANSACTION_TOPIC_ARN,
        'Stock Purchase - Stocker',
        f'Stock Bought!\nUser: {session["username"]}\nStock: {stock_id}\nQty: {quantity}\nPrice: ${price}'
    )
    flash(f'Successfully bought {quantity} shares of {stock_id}!', 'success')
    return redirect(url_for('trader_dashboard'))

# ── SELL STOCK ────────────────────────────────────────────
@app.route('/sell', methods=['POST'])
def sell_stock():
    if 'email' not in session:
        return redirect(url_for('login'))

    stock_id = request.form['stock_id']
    quantity = int(request.form['quantity'])
    stock    = next((s for s in MOCK_STOCKS if s['id'] == stock_id), None)

    if not stock:
        flash('Stock not found!', 'danger')
        return redirect(url_for('trader_dashboard'))

    price = stock['price']
    db    = get_dynamodb()

    if db:
        # AWS Mode
        port_table = db.Table('stocker_portfolio')
        existing   = port_table.get_item(
            Key={'user_id': session['email'], 'stock_id': stock_id}
        ).get('Item')

        if not existing or existing['quantity'] < quantity:
            flash('Insufficient shares!', 'danger')
            return redirect(url_for('trader_dashboard'))

        new_qty = existing['quantity'] - quantity
        if new_qty == 0:
            port_table.delete_item(Key={'user_id': session['email'], 'stock_id': stock_id})
        else:
            port_table.update_item(
                Key={'user_id': session['email'], 'stock_id': stock_id},
                UpdateExpression='SET quantity = :q',
                ExpressionAttributeValues={':q': new_qty}
            )
        db.Table('stocker_transactions').put_item(Item={
            'id':               str(uuid.uuid4()),
            'user_id':          session['email'],
            'stock_id':         stock_id,
            'action':           'sell',
            'price':            price,
            'quantity':         quantity,
            'status':           'completed',
            'transaction_date': datetime.now().isoformat()
        })
    else:
        # Local Mode
        user_portfolio = LOCAL_PORTFOLIO.get(session['email'], {})
        existing       = user_portfolio.get(stock_id)

        if not existing or existing['quantity'] < quantity:
            flash('Insufficient shares!', 'danger')
            return redirect(url_for('trader_dashboard'))

        new_qty = existing['quantity'] - quantity
        if new_qty == 0:
            del user_portfolio[stock_id]
        else:
            user_portfolio[stock_id]['quantity'] = new_qty

        LOCAL_TRANSACTIONS.append({
            'id':               str(uuid.uuid4()),
            'user_id':          session['email'],
            'stock_id':         stock_id,
            'action':           'sell',
            'price':            price,
            'quantity':         quantity,
            'status':           'completed',
            'transaction_date': datetime.now().isoformat()
        })

    send_notification(
        TRANSACTION_TOPIC_ARN,
        'Stock Sale - Stocker',
        f'Stock Sold!\nUser: {session["username"]}\nStock: {stock_id}\nQty: {quantity}\nPrice: ${price}'
    )
    flash(f'Successfully sold {quantity} shares of {stock_id}!', 'success')
    return redirect(url_for('trader_dashboard'))

# ── DELETE TRADER ─────────────────────────────────────────
@app.route('/delete_trader/<email>', methods=['POST'])
def delete_trader(email):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = get_dynamodb()
    if db:
        db.Table('stocker_users').delete_item(Key={'email': email})
    else:
        LOCAL_USERS.pop(email, None)

    flash(f'Trader {email} deleted!', 'success')
    return redirect(url_for('admin_dashboard'))


    # ── SERVICE ROUTES ────────────────────────────────────────
@app.route('/service1')
def service1():
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == 'AAPL'), None)
    return render_template('service-details-1.html', stock=stock)

@app.route('/service2')
def service2():
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == 'GOOGL'), None)
    return render_template('service-details-2.html', stock=stock)

@app.route('/service3')
def service3():
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == 'MSFT'), None)
    return render_template('service-details-3.html', stock=stock)

@app.route('/service4')
def service4():
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == 'TSLA'), None)
    return render_template('service-details-4.html', stock=stock)

@app.route('/service5')
def service5():
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == 'NVDA'), None)
    return render_template('service-details-5.html', stock=stock)

# ── BUY PAGE ──────────────────────────────────────────────
@app.route('/buy_page/<stock_id>')
def buy_page(stock_id):
    if 'email' not in session:
        return redirect(url_for('login'))
    stock = next((s for s in MOCK_STOCKS if s['id'] == stock_id), None)
    return render_template('buy_stock.html', stock=stock)

# ── SELL PAGE ─────────────────────────────────────────────
@app.route('/sell_page/<stock_id>')
def sell_page(stock_id):
    if 'email' not in session:
        return redirect(url_for('login'))
    db = get_dynamodb()
    if db:
        portfolio = db.Table('stocker_portfolio').get_item(
            Key={'user_id': session['email'], 'stock_id': stock_id}
        ).get('Item')
    else:
        portfolio = LOCAL_PORTFOLIO.get(session['email'], {}).get(stock_id)
    stock = next((s for s in MOCK_STOCKS if s['id'] == stock_id), None)
    return render_template('sell_stock.html', stock=stock, portfolio=portfolio)

# ─── MAIN ─────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
app.run(debug=False, host='0.0.0.0', port=port)