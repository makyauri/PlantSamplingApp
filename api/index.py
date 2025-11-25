from flask import Flask, render_template, request, jsonify
import psycopg2
import psycopg2.extras
import json
import os
from urllib.parse import urlparse

app = Flask(__name__, template_folder='../public', static_folder='../public')

# Get database URL from environment variable
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Create database connection"""
    try:
        # Parse the connection string
        result = urlparse(DATABASE_URL)
        username = result.username
        password = result.password
        database = result.path[1:]
        hostname = result.hostname
        port = result.port or 5432

        conn = psycopg2.connect(
            host=hostname,
            database=database,
            user=username,
            password=password,
            port=port,
            sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Route: Home page
@app.route('/')
def index():
    return render_template('index.html')

# Route: View all plant samples
@app.route('/api/samples', methods=['GET'])
def get_all_samples():
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM PLANT_SAMPLE')
        samples = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to JSON-serializable format
        samples_list = []
        for sample in samples:
            samples_list.append({
                'sample_id': sample['sample_id'],
                'date_of_sampling': str(sample['date_of_sampling']),
                'plant_sample_detail': sample['plant_sample_detail'],
                'sampling_location': sample['sampling_location'],
                'environmental_conditions': sample['environmental_conditions'],
                'location_id': sample['location_id'],
                'researcher_id': sample['researcher_id']
            })
        
        return jsonify({'success': True, 'data': samples_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: Add new plant sample
@app.route('/api/samples/add', methods=['POST'])
def add_sample():
    try:
        data = request.json
        
        # Validate required fields
        if not all(k in data for k in ['date_of_sampling', 'plant_sample_detail', 'sampling_location', 'environmental_conditions', 'location_id', 'researcher_id']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO PLANT_SAMPLE 
               (date_of_sampling, plant_sample_detail, sampling_location, environmental_conditions, location_id, researcher_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING sample_id""",
            (
                data['date_of_sampling'],
                json.dumps(data['plant_sample_detail']),
                json.dumps(data['sampling_location']),
                json.dumps(data['environmental_conditions']),
                data['location_id'],
                data['researcher_id']
            )
        )
        
        sample_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'sample_id': sample_id, 'message': 'Sample added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: Query sample by ID
@app.route('/api/samples/<int:sample_id>', methods=['GET'])
def get_sample(sample_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute('SELECT * FROM PLANT_SAMPLE WHERE sample_id = %s', (sample_id,))
        sample = cur.fetchone()
        cur.close()
        conn.close()
        
        if sample is None:
            return jsonify({'error': 'Sample not found'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'sample_id': sample['sample_id'],
                'date_of_sampling': str(sample['date_of_sampling']),
                'plant_sample_detail': sample['plant_sample_detail'],
                'sampling_location': sample['sampling_location'],
                'environmental_conditions': sample['environmental_conditions'],
                'location_id': sample['location_id'],
                'researcher_id': sample['researcher_id']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: Update plant sample
@app.route('/api/samples/<int:sample_id>/update', methods=['PUT'])
def update_sample(sample_id):
    try:
        data = request.json
        
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        
        # Build update query dynamically based on provided fields
        update_fields = []
        values = []
        
        if 'date_of_sampling' in data:
            update_fields.append('date_of_sampling = %s')
            values.append(data['date_of_sampling'])
        if 'plant_sample_detail' in data:
            update_fields.append('plant_sample_detail = %s')
            values.append(json.dumps(data['plant_sample_detail']))
        if 'sampling_location' in data:
            update_fields.append('sampling_location = %s')
            values.append(json.dumps(data['sampling_location']))
        if 'environmental_conditions' in data:
            update_fields.append('environmental_conditions = %s')
            values.append(json.dumps(data['environmental_conditions']))
        if 'location_id' in data:
            update_fields.append('location_id = %s')
            values.append(data['location_id'])
        if 'researcher_id' in data:
            update_fields.append('researcher_id = %s')
            values.append(data['researcher_id'])
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        values.append(sample_id)
        query = f"UPDATE PLANT_SAMPLE SET {', '.join(update_fields)} WHERE sample_id = %s"
        cur.execute(query, values)
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sample updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Route: Delete plant sample
@app.route('/api/samples/<int:sample_id>/delete', methods=['DELETE'])
def delete_sample(sample_id):
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cur = conn.cursor()
        cur.execute('DELETE FROM PLANT_SAMPLE WHERE sample_id = %s', (sample_id,))
        
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            return jsonify({'error': 'Sample not found'}), 404
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Sample deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# For local testing
if __name__ == '__main__':
    app.run(debug=True)