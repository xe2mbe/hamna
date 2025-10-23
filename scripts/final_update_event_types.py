import sqlite3
import os

def update_event_types():
    db_path = 'database/hamna.db'
    
    print("Updating event types in the database...")
    print("Current database path:", os.path.abspath(db_path))
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Error: Database file not found at:", os.path.abspath(db_path))
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Get current event types
        cursor.execute("SELECT * FROM eventos_type;")
        current_types = cursor.fetchall()
        
        print("\nCurrent event types:")
        for row in current_types:
            print(f"- {row[0]}: {row[1]}")
        
        # Ask for confirmation
        confirm = input("\nDo you want to update event types? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
            
        # Start transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Delete existing event types
        cursor.execute("DELETE FROM eventos_type;")
        
        # Insert new event types
        new_types = ['Boletín', 'Programa', 'Anuncio']
        cursor.executemany("INSERT INTO eventos_type (nombre) VALUES (?);", 
                         [(tipo,) for tipo in new_types])
        
        # Verify the changes
        cursor.execute("SELECT * FROM eventos_type ORDER BY id;")
        updated_types = cursor.fetchall()
        
        print("\nUpdated event types:")
        for row in updated_types:
            print(f"- {row[0]}: {row[1]}")
        
        # Commit changes
        conn.commit()
        print("\n✅ Event types updated successfully!")
        
        # Remove this script
        try:
            os.remove(__file__)
            print("This script has been deleted.")
        except Exception as e:
            print("Note: Could not delete this script. You may need to remove it manually.")
            
    except sqlite3.Error as e:
        print("\n❌ An error occurred:", e)
        if 'conn' in locals():
            conn.rollback()
            print("Changes were rolled back.")
    except Exception as e:
        print("\n❌ An unexpected error occurred:", e)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_event_types()
    input("\nPress Enter to exit...")
