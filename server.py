import json
import os
import time
import threading
from urllib.parse import urlparse, parse_qs
from datetime import datetime

PORT = 3000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'database.json')
HTML_FILE = os.path.join(BASE_DIR, 'index.html')

file_lock = threading.Lock()
DEFAULT_TOKEN = "STORE-KUNDAN-389"

DEFAULT_MEDICINES = [
    {"id": "med_1", "name": "Calpol 650 Tablet", "qty": 45, "price": 32.50},
    {"id": "med_2", "name": "Azithral 500 Tablet (Azithromycin)", "qty": 18, "price": 119.00},
    {"id": "med_3", "name": "Pan-D Capsule (Pantoprazole + Domperidone)", "qty": 25, "price": 145.00},
    {"id": "med_4", "name": "Combiflam Tablet", "qty": 30, "price": 42.00},
    {"id": "med_5", "name": "Dolo 650 Tablet", "qty": 50, "price": 30.00},
    {"id": "med_6", "name": "Amoxyclav 625 (Augmentin)", "qty": 8, "price": 185.00},
    {"id": "med_7", "name": "Cetirizine 10mg (Okacet)", "qty": 4, "price": 18.00},
    {"id": "med_8", "name": "Ascoril D Plus Cough Syrup (100ml)", "qty": 3, "price": 125.00},
    {"id": "med_9", "name": "Betadine 10% Ointment (20g)", "qty": 0, "price": 95.00}
]

def get_current_time_str():
    now = datetime.now()
    return now.strftime("%d %b %Y, %I:%M %p")

def load_database():
    with file_lock:
        if not os.path.exists(DATA_FILE):
            initial_data = {
                "version": 1,
                "token": DEFAULT_TOKEN,
                "lastUpdated": int(time.time() * 1000),
                "lastModifiedBy": "System",
                "lastAction": "Database Initialized",
                "inventory": DEFAULT_MEDICINES,
                "salesHistory": [],
                "stores": {
                    DEFAULT_TOKEN: {
                        "token": DEFAULT_TOKEN,
                        "inventory": DEFAULT_MEDICINES,
                        "salesHistory": [],
                        "lastUpdated": int(time.time() * 1000),
                        "lastModifiedBy": "System",
                        "lastAction": "Database Initialized"
                    }
                }
            }
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
            return initial_data

        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "stores" not in data:
                    data["stores"] = {}
                # Ensure DEFAULT_TOKEN store is populated
                if DEFAULT_TOKEN not in data["stores"]:
                    data["stores"][DEFAULT_TOKEN] = {
                        "token": DEFAULT_TOKEN,
                        "inventory": data.get("inventory", DEFAULT_MEDICINES),
                        "salesHistory": data.get("salesHistory", []),
                        "lastUpdated": data.get("lastUpdated", int(time.time() * 1000)),
                        "lastModifiedBy": data.get("lastModifiedBy", "System"),
                        "lastAction": data.get("lastAction", "Migrated")
                    }
                return data
        except Exception as e:
            return {
                "version": 1,
                "token": DEFAULT_TOKEN,
                "lastUpdated": int(time.time() * 1000),
                "lastModifiedBy": "System Recovery",
                "lastAction": "Recovery",
                "inventory": DEFAULT_MEDICINES,
                "salesHistory": [],
                "stores": {
                    DEFAULT_TOKEN: {
                        "token": DEFAULT_TOKEN,
                        "inventory": DEFAULT_MEDICINES,
                        "salesHistory": [],
                        "lastUpdated": int(time.time() * 1000),
                        "lastModifiedBy": "System Recovery",
                        "lastAction": "Recovery"
                    }
                }
            }

def save_database(data):
    with file_lock:
        data["lastUpdated"] = int(time.time() * 1000)
        data["version"] = data.get("version", 0) + 1
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return data

# Initialize on import
load_database()

def get_store_snapshot(db, token):
    if not token or "SONALI" in token or "SONELEE" in token:
        token = DEFAULT_TOKEN
    stores = db.setdefault("stores", {})
    if token not in stores:
        for old_k in ("STORE-SONELEE-389", "STORE-SONALI-389"):
            if old_k in stores:
                stores[token] = stores[old_k]
                stores[token]["token"] = token
                break
        else:
            stores[token] = {
                "token": token,
                "inventory": DEFAULT_MEDICINES.copy(),
                "salesHistory": [],
                "lastUpdated": int(time.time() * 1000),
                "lastModifiedBy": "Kundan",
                "lastAction": f"Store initialized for token {token}"
            }
    store = stores[token]
    return store

def process_action(payload):
    action = payload.get('action')
    author = payload.get('author', 'Anonymous User')
    token = payload.get('token') or DEFAULT_TOKEN

    db = load_database()
    store = get_store_snapshot(db, token)
    inventory = store.get('inventory', [])
    sales = store.get('salesHistory', [])
    action_desc = ""
    extra_response = {}

    if action == 'ADD_STOCK':
        name = payload.get('name', '').strip()
        qty = int(payload.get('qty', 0))
        price = float(payload.get('price', 0))
        if not name or qty <= 0 or price < 0:
            raise ValueError("Kripya sahi dawa details dalein")

        existing = next((m for m in inventory if m['name'].lower() == name.lower()), None)
        if existing:
            existing['qty'] += qty
            existing['price'] = price
            action_desc = f"{author} ne '{existing['name']}' ka stock badhakar {existing['qty']} kiya"
        else:
            new_med = {
                "id": f"med_{int(time.time() * 1000)}",
                "name": name,
                "qty": qty,
                "price": price
            }
            inventory.insert(0, new_med)
            action_desc = f"{author} ne nayi dawa '{name}' ({qty} units) add ki"

    elif action == 'UPDATE_MEDICINE':
        med_id = payload.get('id')
        new_name = payload.get('name', '').strip()
        new_qty = int(payload.get('qty', 0))
        new_price = float(payload.get('price', 0))

        target = next((m for m in inventory if m['id'] == med_id), None)
        if not target:
            raise ValueError("Dawa nahi mili")

        old_name = target['name']
        target['name'] = new_name if new_name else target['name']
        target['qty'] = new_qty
        target['price'] = new_price
        action_desc = f"{author} ne '{old_name}' update ki (Stock: {new_qty}, Price: ₹{new_price})"

    elif action == 'QUICK_ADD_STOCK':
        med_id = payload.get('id')
        amount = int(payload.get('amount', 10))
        target = next((m for m in inventory if m['id'] == med_id), None)
        if not target:
            raise ValueError("Dawa nahi mili")
        target['qty'] += amount
        action_desc = f"{author} ne '{target['name']}' me +{amount} stock add kiya"

    elif action == 'DELETE_MEDICINE':
        med_id = payload.get('id')
        target = next((m for m in inventory if m['id'] == med_id), None)
        med_name = target['name'] if target else 'Medicine'
        inventory = [m for m in inventory if m['id'] != med_id]
        action_desc = f"{author} ne '{med_name}' delete ki"

    elif action == 'SELL_MEDICINE':
        med_id = payload.get('id')
        qty = int(payload.get('qty', 0))
        gst_percent = float(payload.get('gstPercent', 0) or 0)
        target = next((m for m in inventory if m['id'] == med_id), None)
        if not target:
            raise ValueError("Dawa stock me nahi mili")
        if target['qty'] < qty:
            raise ValueError(f"Stock kam hai! Sirf {target['qty']} available hai")

        target['qty'] -= qty
        unit_price = float(target['price'])
        subtotal = round(unit_price * qty, 2)
        gst_amount = round((subtotal * gst_percent) / 100, 2)
        total_amount = round(subtotal + gst_amount, 2)
        timestamp_now = int(time.time() * 1000)

        new_sale = {
            "id": f"sale_{timestamp_now}",
            "timestamp": timestamp_now,
            "datetime": get_current_time_str(),
            "medicineId": target['id'],
            "medicineName": target['name'],
            "pricePerUnit": unit_price,
            "qty": qty,
            "subtotal": subtotal,
            "gstPercent": gst_percent,
            "gstAmount": gst_amount,
            "total": total_amount,
            "author": author
        }
        sales.insert(0, new_sale)
        if gst_percent > 0:
            action_desc = f"{author} ne {qty}x '{target['name']}' bechi (+{gst_percent}% GST, Bill: ₹{total_amount})"
        else:
            action_desc = f"{author} ne {qty}x '{target['name']}' bechi (Bill: ₹{total_amount})"
        extra_response['createdSale'] = new_sale

    elif action == 'DELETE_SALE':
        sale_id = payload.get('id')
        sales = [s for s in sales if s['id'] != sale_id]
        action_desc = f"{author} ne bill record delete kiya"

    elif action == 'CLEAR_ALL_SALES':
        sales = []
        action_desc = f"{author} ne puri sales history clear ki"

    elif action == 'RESET_DEMO':
        inventory = DEFAULT_MEDICINES.copy()
        action_desc = f"{author} ne demo medicines reload ki"

    elif action == 'RESTORE_BACKUP':
        if 'inventory' in payload and isinstance(payload['inventory'], list):
            inventory = payload['inventory']
        if 'salesHistory' in payload and isinstance(payload['salesHistory'], list):
            sales = payload['salesHistory']
        action_desc = f"{author} ne backup data restore kiya"

    else:
        raise ValueError(f"Unknown action: {action}")

    # Update store object
    now_ts = int(time.time() * 1000)
    store['inventory'] = inventory
    store['salesHistory'] = sales
    store['lastModifiedBy'] = author
    store['lastAction'] = action_desc
    store['lastUpdated'] = now_ts
    store['token'] = token

    # Sync to root for default token
    if token == DEFAULT_TOKEN or not db.get("inventory"):
        db['inventory'] = inventory
        db['salesHistory'] = sales
        db['lastModifiedBy'] = author
        db['lastAction'] = action_desc

    saved_db = save_database(db)

    return {
        "status": "success",
        "token": token,
        "action": action,
        "lastAction": action_desc,
        "lastModifiedBy": author,
        "lastUpdated": now_ts,
        "version": saved_db["version"],
        "inventory": inventory,
        "salesHistory": sales,
        **extra_response
    }

# =====================================================================
# WSGI Application Handler (For PythonAnywhere 24/7 Deployment)
# =====================================================================
def application(environ, start_response):
    raw_uri = environ.get('RAW_URI') or environ.get('REQUEST_URI') or environ.get('PATH_INFO', '/')
    parsed_url = urlparse(raw_uri)
    path = parsed_url.path or '/'
    query_params = parse_qs(parsed_url.query)
    method = environ.get('REQUEST_METHOD', 'GET').upper()

    cors_headers = [
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
        ('Access-Control-Allow-Headers', 'Content-Type, Cache-Control, X-Store-Token')
    ]

    if method == 'OPTIONS':
        start_response('204 No Content', cors_headers)
        return [b'']

    if method == 'GET':
        if path in ('/', '/index.html'):
            try:
                with open(HTML_FILE, 'rb') as f:
                    content = f.read()
                headers = cors_headers + [
                    ('Content-Type', 'text/html; charset=utf-8'),
                    ('Cache-Control', 'no-cache')
                ]
                start_response('200 OK', headers)
                return [content]
            except Exception as e:
                start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
                return [str(e).encode('utf-8')]

        elif path == '/api/data':
            # Extract token from query or header
            req_token = query_params.get('token', [None])[0] or environ.get('HTTP_X_STORE_TOKEN') or DEFAULT_TOKEN
            db = load_database()
            store = get_store_snapshot(db, req_token)
            
            resp_data = {
                "token": req_token,
                "inventory": store.get("inventory", DEFAULT_MEDICINES),
                "salesHistory": store.get("salesHistory", []),
                "lastUpdated": store.get("lastUpdated", int(time.time() * 1000)),
                "lastModifiedBy": store.get("lastModifiedBy", "System"),
                "lastAction": store.get("lastAction", "Fetched"),
                "version": db.get("version", 1)
            }
            body = json.dumps(resp_data, ensure_ascii=False).encode('utf-8')
            headers = cors_headers + [
                ('Content-Type', 'application/json; charset=utf-8'),
                ('Cache-Control', 'no-cache, no-store, must-revalidate')
            ]
            start_response('200 OK', headers)
            return [body]

        elif path == '/api/ping':
            headers = cors_headers + [('Content-Type', 'application/json')]
            start_response('200 OK', headers)
            return [b'{"status":"ok","connected":true}']

    elif method == 'POST':
        if path == '/api/action':
            try:
                length = int(environ.get('CONTENT_LENGTH', 0) or 0)
                raw_body = environ['wsgi.input'].read(length).decode('utf-8')
                payload = json.loads(raw_body)
                result = process_action(payload)
                resp_body = json.dumps(result, ensure_ascii=False).encode('utf-8')
                headers = cors_headers + [('Content-Type', 'application/json; charset=utf-8')]
                start_response('200 OK', headers)
                return [resp_body]
            except Exception as e:
                err_body = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
                headers = cors_headers + [('Content-Type', 'application/json')]
                start_response('400 Bad Request', headers)
                return [err_body]

        elif path in ('/api/save', '/api/sync'):
            try:
                length = int(environ.get('CONTENT_LENGTH', 0) or 0)
                raw_body = environ['wsgi.input'].read(length).decode('utf-8')
                payload = json.loads(raw_body)
                token = payload.get('token') or DEFAULT_TOKEN
                author = payload.get('author', 'User')

                db = load_database()
                store = get_store_snapshot(db, token)
                if 'inventory' in payload:
                    store['inventory'] = payload['inventory']
                if 'salesHistory' in payload:
                    store['salesHistory'] = payload['salesHistory']

                store['lastModifiedBy'] = author
                store['lastAction'] = payload.get('action', f"Saved by {author}")
                store['lastUpdated'] = int(time.time() * 1000)

                if token == DEFAULT_TOKEN:
                    db['inventory'] = store['inventory']
                    db['salesHistory'] = store['salesHistory']
                    db['lastModifiedBy'] = author

                saved_db = save_database(db)

                resp_body = json.dumps({
                    "status": "success",
                    "token": token,
                    "lastUpdated": store["lastUpdated"],
                    "version": saved_db["version"],
                    "lastModifiedBy": author,
                    "inventory": store["inventory"],
                    "salesHistory": store["salesHistory"]
                }).encode('utf-8')

                headers = cors_headers + [('Content-Type', 'application/json; charset=utf-8')]
                start_response('200 OK', headers)
                return [resp_body]
            except Exception as e:
                err_body = json.dumps({"status": "error", "message": str(e)}).encode('utf-8')
                headers = cors_headers + [('Content-Type', 'application/json')]
                start_response('400 Bad Request', headers)
                return [err_body]

    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return [b'Not Found']


# =====================================================================
# Standalone Local Runner (For running locally on port 3000)
# =====================================================================
if __name__ == '__main__':
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            if args and any('/api/data' in str(a) for a in args):
                return
            super().log_message(format, *args)

    httpd = make_server('0.0.0.0', PORT, application, handler_class=QuietHandler)
    print(f"[*] Medical Store Server with Token Persistence running on port {PORT}...")
    httpd.serve_forever()
