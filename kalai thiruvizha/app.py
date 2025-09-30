from flask import Flask, render_template, request, redirect, url_for, flash,send_file
import pymysql 

app = Flask(__name__)
app.secret_key = 'kalai_thiruvizha_25_secret_key'

def get_db_connection():
    try:
        connection = pymysql.connect(
            host="mysql-2006-kalai-thiruvizha-1.l.aivencloud.com",
            port=23782,
            user="avnadmin",
            password="AVNS_qKPWdqKjJsuuCVhcpBs",
            database="defaultdb",
            ssl={"ssl": {}}
        )
        return connection
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None

def check_registration_limit(register_no, connection):
    """
    Check if a student has already registered for 3 or more competitions
    Returns: (can_register, current_count, error_message)
    """
    try:
        cursor = connection.cursor()
        
        # Check in participants table (as main participant)
        cursor.execute('''
            SELECT COUNT(DISTINCT competition) as comp_count 
            FROM participants 
            WHERE register_no = %s
        ''', (register_no,))
        main_count = cursor.fetchone()[0]
        
        # Check in group_members table (as group member)
        cursor.execute('''
            SELECT COUNT(DISTINCT p.competition) as comp_count 
            FROM group_members gm
            JOIN participants p ON gm.participant_id = p.id
            WHERE gm.register_no = %s
        ''', (register_no,))
        group_count = cursor.fetchone()[0]
        
        total_count = main_count + group_count
        
        if total_count >= 3:
            return False, total_count, f"Register No {register_no} has already registered for {total_count} competitions. Maximum allowed is 3."
        else:
            return True, total_count, None
            
    except Exception as e:
        print(f"Error checking registration limit: {e}")
        return False, 0, f"Error checking registration limit: {str(e)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    connection = None
    try:
        # Get form data
        participation_type = request.form['participation_type']
        competition = request.form['competition']
        
        # Main participant data
        register_no = request.form['register_no'].strip()
        name = request.form['name'].strip()
        year = request.form['year']
        department = request.form['department']
        gender = request.form['gender']
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed. Please try again.', 'error')
            return redirect(url_for('index'))
        
        cursor = connection.cursor()
        
        # Check registration limit for main participant
        can_register, current_count, error_msg = check_registration_limit(register_no, connection)
        if not can_register:
            flash(error_msg, 'error')
            return redirect(url_for('index'))
        
        # Check group members if it's a group registration
        if participation_type == 'group':
            group_size = int(request.form.get('group_size', 1))
            group_members_to_check = []
            
            # Collect all group member register numbers
            for i in range(1, group_size):
                member_register_no = request.form.get(f'register_no_{i}', '').strip()
                if member_register_no:
                    group_members_to_check.append(member_register_no)
            
            # Check registration limit for each group member
            for member_register_no in group_members_to_check:
                can_register, current_count, error_msg = check_registration_limit(member_register_no, connection)
                if not can_register:
                    flash(error_msg, 'error')
                    return redirect(url_for('index'))
        
        # Insert main participant
        if participation_type == 'group':
            group_size = int(request.form.get('group_size', 1))
        else:
            group_size = 1
        
        insert_participant_query = '''
            INSERT INTO participants (register_no, name, year, department, gender, 
                                    participation_type, group_size, competition)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        participant_data = (register_no, name, year, department, gender, 
                          participation_type, group_size, competition)
        
        cursor.execute(insert_participant_query, participant_data)
        participant_id = cursor.lastrowid
        
        # Handle group members if participation type is group
        if participation_type == 'group':
            group_size = int(request.form.get('group_size', 1))
            for i in range(1, group_size):
                member_register_no = request.form.get(f'register_no_{i}', '').strip()
                member_name = request.form.get(f'name_{i}', '').strip()
                member_year = request.form.get(f'year_{i}')
                member_department = request.form.get(f'dept_{i}')
                member_gender = request.form.get(f'gender_{i}')
                
                if all([member_register_no, member_name, member_year, member_department, member_gender]):
                    insert_member_query = '''
                        INSERT INTO group_members (participant_id, register_no, name, year, department, gender)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    '''
                    member_data = (participant_id, member_register_no, member_name, 
                                 member_year, member_department, member_gender)
                    cursor.execute(insert_member_query, member_data)
        
        connection.commit()
        
        # Show success message with current count
        _, new_count, _ = check_registration_limit(register_no, connection)
        flash(f'Registration successful! {register_no} has now registered for {new_count} out of 3 competitions.', 'success')
        
    except Exception as e:
        if connection:
            connection.rollback()
        flash(f'Registration failed: {str(e)}', 'error')
        print(f"❌ Error: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()
        
    return redirect(url_for('index'))

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/view-registrations')
def view_registrations():
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return "Database connection failed"
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        # Get all participants
        cursor.execute('''
            SELECT p.*, COUNT(gm.id) as member_count 
            FROM participants p 
            LEFT JOIN group_members gm ON p.id = gm.participant_id 
            GROUP BY p.id 
            ORDER BY p.registration_date DESC
        ''')
        participants = cursor.fetchall()
        
        return render_template('view_registrations.html', participants=participants)
        
    except Exception as e:
        return f"Error: {e}"
    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/view-teams')
def view_teams():
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return "Database connection failed"
        
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        
        # Get all participants with their group members
        cursor.execute('''
            SELECT 
                p.id as team_id,
                p.register_no as leader_register_no,
                p.name as leader_name,
                p.year as leader_year,
                p.department as leader_department,
                p.gender as leader_gender,
                p.participation_type,
                p.group_size,
                p.competition,
                p.registration_date,
                gm.register_no as member_register_no,
                gm.name as member_name,
                gm.year as member_year,
                gm.department as member_department,
                gm.gender as member_gender
            FROM participants p
            LEFT JOIN group_members gm ON p.id = gm.participant_id
            ORDER BY p.registration_date DESC, p.id, gm.id
        ''')
        
        rows = cursor.fetchall()
        
        # Organize data into teams
        teams = {}
        for row in rows:
            team_id = row['team_id']
            
            if team_id not in teams:
                teams[team_id] = {
                    'leader': {
                        'register_no': row['leader_register_no'],
                        'name': row['leader_name'],
                        'year': row['leader_year'],
                        'department': row['leader_department'],
                        'gender': row['leader_gender']
                    },
                    'participation_type': row['participation_type'],
                    'group_size': row['group_size'],
                    'competition': row['competition'],
                    'registration_date': row['registration_date'],
                    'members': []
                }
            
            # Add group members if they exist
            if row['member_register_no']:
                teams[team_id]['members'].append({
                    'register_no': row['member_register_no'],
                    'name': row['member_name'],
                    'year': row['member_year'],
                    'department': row['member_department'],
                    'gender': row['member_gender']
                })
        
        return render_template('view_teams.html', teams=teams)
        
    except Exception as e:
        return f"Error: {e}"
    finally:
        if connection:
            cursor.close()
            connection.close()

@app.route('/check-limit/<register_no>')
def check_limit(register_no):
    """API endpoint to check registration limit for a student"""
    connection = None
    try:
        connection = get_db_connection()
        if not connection:
            return {"error": "Database connection failed"}
        
        can_register, current_count, error_msg = check_registration_limit(register_no, connection)
        
        return {
            "register_no": register_no,
            "can_register": can_register,
            "current_count": current_count,
            "max_allowed": 3,
            "message": error_msg if error_msg else f"Can register for {3 - current_count} more competitions"
        }
        
    except Exception as e:
        return {"error": str(e)}
    finally:
        if connection:
            connection.close()
 


if __name__ == '__main__':

    app.run(debug=True)
