import sqlite3

def print_schema():
    # Connect to the database
    conn = sqlite3.connect('database/hamna.db')
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Database Schema:")
    print("=" * 50)
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        print("-" * 50)
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        # Print column information
        print(f"{'Column Name':<20} {'Type':<15} {'Nullable':<10} {'Primary Key'}")
        print("-" * 50)
        for col in columns:
            col_id, name, col_type, notnull, dflt_value, pk = col
            print(f"{name:<20} {col_type:<15} {'NO' if notnull else 'YES':<10} {'YES' if pk else 'NO'}")
        
        # Print any indexes
        cursor.execute(f"PRAGMA index_list({table_name});")
        indexes = cursor.fetchall()
        
        if indexes:
            print("\nIndexes:")
            for idx in indexes:
                idx_name = idx[1]
                cursor.execute(f"PRAGMA index_info({idx_name});")
                idx_columns = cursor.fetchall()
                cols = ", ".join([col[2] for col in idx_columns])
                print(f"- {idx_name}: {cols}")
    
    conn.close()

if __name__ == "__main__":
    print_schema()
