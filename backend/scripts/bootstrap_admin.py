"""
Bootstrap Initial Administrator for River Sentinel 2.0
Promotes an authenticated user to 'authority_admin' role in public.profiles.
"""
import sys
import os
import pg8000.native
from dotenv import dotenv_values

def bootstrap_admin(identifier: str):
    """
    identifier can be either a user UUID or user email in auth.users.
    """
    env = dotenv_values('backend/.env')
    host = env.get('SUPABASE_DB_HOST')
    port = int(env.get('SUPABASE_DB_PORT', 5432))
    user = env.get('SUPABASE_DB_USER')
    password = env.get('SUPABASE_DB_PASSWORD')
    database = env.get('SUPABASE_DB_NAME', 'postgres')

    con = pg8000.native.Connection(
        user=user, host=host, port=port, password=password, database=database, ssl_context=True
    )

    # Check if identifier is email or UUID
    user_rows = con.run("SELECT id, email FROM auth.users WHERE email = :id_or_email OR id::text = :id_or_email;", id_or_email=identifier)
    
    if not user_rows:
        print(f"[ERROR] No user found with email or ID: {identifier}")
        print("Existing users in auth.users:")
        all_users = con.run("SELECT id, email, created_at FROM auth.users;")
        for u in all_users:
            print(f"  - ID: {u[0]} | Email: {u[1]} | Created: {u[2]}")
        con.close()
        return False

    user_id = user_rows[0][0]
    email = user_rows[0][1]

    # Run the bootstrap procedure
    con.run("SELECT public.bootstrap_initial_admin(:uid::uuid);", uid=user_id)
    
    # Verify profile
    prof = con.run("SELECT id, role, account_status FROM public.profiles WHERE id = :uid::uuid;", uid=user_id)
    print(f"[SUCCESS] User {email} ({user_id}) elevated to role: {prof[0][1]} (status: {prof[0][2]})")
    con.close()
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/bootstrap_admin.py <email_or_user_uuid>")
        # List users
        bootstrap_admin("")
    else:
        bootstrap_admin(sys.argv[1])
