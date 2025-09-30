import pymysql

def create_tables():
    connection = None
    try:
        # Connect with SSL
        connection = pymysql.connect(
            host="mysql-2006-kalai-thiruvizha-1.l.aivencloud.com",
            port=23782,
            user="avnadmin",
            password="AVNS_qKPWdqKjJsuuCVhcpBs",
            database="defaultdb",
            ssl={"ssl": {}}
        )
        print("✅ Connected to Aiven MySQL!")

        cursor = connection.cursor()

        # Create participants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id INT AUTO_INCREMENT PRIMARY KEY,
                register_no VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                year VARCHAR(20) NOT NULL,
                department VARCHAR(100) NOT NULL,
                gender VARCHAR(10) NOT NULL,
                participation_type ENUM('solo', 'group') NOT NULL,
                group_size INT DEFAULT 1,
                competition VARCHAR(100) NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Participants table created.")

        # Create group_members table for group registrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                participant_id INT,
                register_no VARCHAR(50) NOT NULL,
                name VARCHAR(100) NOT NULL,
                year VARCHAR(20) NOT NULL,
                department VARCHAR(100) NOT NULL,
                gender VARCHAR(10) NOT NULL,
                FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
            )
        """)
        print("✅ Group members table created.")

        connection.commit()
        print("✅ All tables created successfully!")

    except Exception as e:
        print("❌ Error while creating tables:", e)
    finally:
        if connection:
            connection.close()
            print("🔌 Connection closed.")

if __name__ == "__main__":
    create_tables()