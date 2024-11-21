import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

DATABASE_PATH = "parts_database.db"

# --- Database Functions ---
def create_database(db_path=DATABASE_PATH):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Parts (
                part_id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_name TEXT NOT NULL,
                part_number TEXT UNIQUE NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity >= 0),
                location TEXT,
                price REAL NOT NULL CHECK (price >= 0),
                vendor TEXT
            )
        """)
        conn.commit()

def add_part(conn, cursor, part_data):
    try:
        cursor.execute("INSERT INTO Parts (part_name, part_number, quantity, location, price, vendor) VALUES (?, ?, ?, ?, ?, ?)", part_data)
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"Error adding part: {e}")
        return False

def get_parts(conn, cursor, search_term=""):
    where_clause = ""
    params = []
    if search_term:
        search_pattern = "%" + search_term + "%"
        where_clause = "WHERE part_name LIKE ? OR part_number LIKE ? OR location LIKE ? OR vendor LIKE ?"
        params = [search_pattern] * 4

    sql = f"""
        SELECT part_id, part_name, part_number, quantity, location, price, vendor
        FROM Parts
        {where_clause}
    """

    try:
        cursor.execute(sql, params)
        return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Error querying database: {e}")
        return []

def get_total_parts(conn, cursor, search_term=""):
    where_clause = ""
    params = []
    if search_term:
        search_pattern = "%" + search_term + "%"
        where_clause = "WHERE part_name LIKE ? OR part_number LIKE ? OR location LIKE ? OR vendor LIKE ?"
        params = [search_pattern] * 4

    try:
        cursor.execute(f"SELECT COUNT(*) FROM Parts {where_clause}", params)
        return cursor.fetchone()[0]
    except sqlite3.Error as e:
        print(f"Error counting parts: {e}")
        return 0

def update_part(conn, cursor, part_id, part_data):
    try:
        cursor.execute("UPDATE Parts SET part_name=?, part_number=?, quantity=?, location=?, price=?, vendor=? WHERE part_id=?", (*part_data, part_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"Error updating part: {e}")
        return False

def delete_part(conn, cursor, part_id):
    try:
        cursor.execute("DELETE FROM Parts WHERE part_id = ?", (part_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error deleting part: {e}")
        return False

# --- Flask App ---
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (Consider route-specific CORS for production)

# API routes
@app.route('/parts', methods=['GET'])
@cross_origin()
def get_parts_api():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        parts = get_parts(conn, cursor)
        total_parts = len(parts)
        conn.close()
        return jsonify({'parts': [list(part) for part in parts], 'totalCount': total_parts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/parts', methods=['POST'])
@cross_origin()
def add_part_api():
    try:
        data = request.get_json()
        required_fields = ['partName', 'partNumber', 'quantity', 'price']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing or empty "{field}" field'}), 400

        try:
            part_data = (
                data['partName'],
                data['partNumber'],
                int(data['quantity']),
                data.get('location', ''),
                float(data['price']),
                data.get('vendor', '')
            )
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            success = add_part(conn, cursor, part_data)
            conn.close()
            if success:
                return jsonify({'message': 'Part added successfully!'}), 201
            else:
                return jsonify({'error': 'Could not add part. Part number may already exist.'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid input: {e}'}), 400
        except sqlite3.Error as e:
            return jsonify({'error': f'Database error: {e}'}), 500

    except Exception as e:
        print(f"Error in add_part_api: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/parts/<int:part_id>', methods=['GET', 'PUT', 'DELETE'])
@cross_origin()
def get_update_delete_part_api(part_id):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        if request.method == 'GET':
            cursor.execute("SELECT * FROM Parts WHERE part_id = ?", (part_id,))
            part = cursor.fetchone()
            if part:
                return jsonify({
                    "partId": part[0],
                    "partName": part[1],
                    "partNumber": part[2],
                    "quantity": part[3],
                    "location": part[4],
                    "price": part[5],
                    "vendor": part[6]
                })
            else:
                return jsonify({'error': 'Part not found'}), 404
        elif request.method == 'PUT':
            data = request.get_json()
            required_fields = ['partName', 'partNumber', 'quantity', 'price']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({'error': f'Missing or empty "{field}" field'}), 400

            try:
                part_data = (
                    data['partName'],
                    data['partNumber'],
                    int(data['quantity']),
                    data.get('location', ''),
                    float(data['price']),
                    data.get('vendor', '')
                )
                success = update_part(conn, cursor, part_id, part_data)
                if success:
                    return jsonify({'message': 'Part updated successfully!'}), 200
                else:
                    return jsonify({'error': 'Could not update part.'}), 400
            except ValueError as e:
                return jsonify({'error': f'Invalid input: {e}'}), 400
            except sqlite3.Error as e:
                return jsonify({'error': f'Database error: {e}'}), 500

        elif request.method == 'DELETE':
            success = delete_part(conn, cursor, part_id)
            if success:
                return jsonify({'message': 'Part deleted successfully!'}), 200
            else:
                return jsonify({'error': 'Could not delete part.'}), 400
        conn.close()
    except sqlite3.Error as e:
        return jsonify({'error': f'Database error: {e}'}), 500
    except Exception as e:
        return jsonify({'error': f'An unexpected error occurred: {e}'}), 500

if __name__ == '__main__':
    create_database()
    app.run(debug=True)