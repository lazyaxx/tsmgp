# myapp/views.py
from django.shortcuts import render, redirect
# Add this to your existing views.py file
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import users
import datetime
import hashlib

def login_register_view(request):
    """Display the login/registration page"""
    return render(request, 'user/login_register.html')

def login_before(request):
    """Display the page that should always show pre-login content"""
    # Force this page to ignore login status
    return render(request, 'user/login_before.html', {'ignore_login_status': True})


def base(request):
    """Display the base page"""
    return render(request, 'user/base.html')

def government_monitors(request):
    """Display the Government monitors base page"""
    return render(request, 'user/government_monitors.html')

def citizen_home(request):
    """Display the Government monitors base page"""
    return render(request, 'user/citizen_home.html')


@login_required
def home_view(request):
    """Display the home page after successful login"""
    return render(request, 'user/home.html')

def register_view(request):
    """Handle user registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        phone = request.POST.get('phone')

        # Additional citizen details
        aadhar_number = request.POST.get('aadhar_number')
        date_of_birth = request.POST.get('date_of_birth')
        gender = request.POST.get('gender')
        occupation = request.POST.get('occupation')
        house_number = request.POST.get('house_number')

        # *Fetch village_id directly from the form*
        village_name = request.POST.get('village_name')
        pincode = request.POST.get('pincode')

        # Validate password
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('login_register')

        with connection.cursor() as cursor:
            try:
                # *Step 1: Insert into users table*
                cursor.execute("""
                    INSERT INTO users (username, password, email, phone, role, registration_date) 
                    VALUES (%s, %s, %s, %s, 'citizen', NOW()) RETURNING user_id
                """, [username, password, email, phone])

                user_id = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT village_id FROM village 
                    WHERE village_name = %s AND pincode = %s
                """, [village_name, pincode])

                village_row = cursor.fetchone()

                if village_row:
                    village_id = village_row[0]  # Extracting village_id if it exists


                # *Step 2: Insert into citizen table*
                cursor.execute("""
                    INSERT INTO citizen (user_id, village_id, name, house_number, aadhar_number, date_of_birth, gender, occupation) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, [user_id, village_id, username, house_number, aadhar_number, date_of_birth, gender, occupation])

                messages.success(request, 'Registration successful! Please login.')
                return redirect('login_register')

            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
                print("Error:", e)

    return render(request, 'user/login_register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Hash the password
        # hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, username, email, phone, role, registration_date 
                FROM users 
                WHERE username = %s AND password = %s
            """, [username, password])
            
            user = cursor.fetchone()

            if not user:
                return render(request, 'user/login_register.html', {'error': 'Username or Password is incorrect'})



            # Fetch citizen details using the user_id
            cursor.execute("""
                SELECT * FROM citizen WHERE user_id = %s
            """,[user[0]])
            
            #citizen = cursor.fetchone()
            cursor.execute("SELECT * FROM citizen WHERE user_id = %s", [user[0]])
            citizen = cursor.fetchone()
            if citizen:
                request.session["citizen_id"] = citizen[0]  # Store citizen_id

            
            if user:
                # Store user info in session
                request.session['user_id'] = user[0]
                request.session['username'] = user[1]
                request.session['email'] = user[2]
                request.session['phone'] = user[3]
                request.session['role'] = user[4]
                return redirect('home')
                
                # if user[4] == 'citizen':
                #     return redirect('citizen_home')
                # elif user[4] == 'gm':
                #     return redirect('government_monitors')
                # elif user[4] == 'admin':
                #     return redirect('admin_home')
                # else:
                #     return redirect('employee_home')  # Go to dashboard page
            else:
                messages.error(request, 'Wrong username or password')
                return redirect('user/login_register')
    
    return render(request, 'user/login_register.html')


def home_view(request):
    if request.session['role'] == 'citizen':
        return redirect('citizen_home')
    elif request.session['role'] == 'gm':
        return redirect('government_monitors')
    elif request.session['role'] == 'admin':
        return redirect('admin')
    else:
        return redirect('employee_home')


def logout(request):
    """Handle user logout by clearing the session"""
    # Clear all session data
    request.session.flush()
    
    # You can add a success message if you want
    messages.success(request, 'You have been successfully logged out.')
    
    # Redirect to the login page or home page
    return redirect('login_before')  # Or any other page you want to redirect to



def delete_account(request):
    user_id = request.session['user_id']

    if not user_id:
        return redirect('login')  # Redirect if user is not logged in

    try:
        with connection.cursor() as cursor:
            # Delete user account
            cursor.execute("DELETE FROM users WHERE user_id = %s", [user_id])

        # Clear session and redirect after deletion
        request.session.flush()
        return redirect('login_before')

    except Exception as e:
        print(f"Error deleting account: {e}")
        return redirect('dashboard')  # Redirect back in case of an error



# Original dashboard function
def dashboard(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    user_id = request.session['user_id']
    
    # Get user data from session
    context = {
        'user_id': user_id,
        'username': request.session['username'],
        'email': request.session['email'],
        'phone': request.session['phone'],
        'role': request.session['role'],
    }
    
    with connection.cursor() as cursor:
        # Get all citizen information

        cursor.execute("""
            SELECT pe.monitor_id, pe.department, pe.designation
            FROM government_monitor pe
            WHERE pe.user_id = %s
        """, [user_id])

        gm_result = cursor.fetchone()

        cursor.execute("""
            SELECT pe.employee_id, pe.designation, pe.joining_date, pe.department, pe.education
            FROM panchayat_employee pe
            WHERE pe.user_id = %s
        """, [user_id])

        employee_result = cursor.fetchone()

        cursor.execute("""
            SELECT c.citizen_id, c.name, c.house_number, c.aadhar_number, 
                c.date_of_birth, c.gender, c.occupation, v.village_name,
                v.district, v.state, v.pincode
            FROM CITIZEN c
            JOIN VILLAGE v ON c.village_id = v.village_id
            WHERE c.user_id = %s
        """, [user_id])

        citizen_result = cursor.fetchone()
        # print(citizen_result)

        
    

        # Check if result is not None
        if citizen_result:
            temp = {
                'citizen_id': citizen_result[0],
                'name': citizen_result[1],
                'house_number': citizen_result[2],
                'aadhar_number': citizen_result[3],
                'date_of_birth': citizen_result[4],
                'gender': citizen_result[5],
                'occupation': citizen_result[6],
                'village_name': citizen_result[7],
                'district': citizen_result[8],
                'state': citizen_result[9],
                'pincode': citizen_result[10],
            }
        else:
            temp = {}

        
        if employee_result:
            temp1 = {
                'employee_id': employee_result[0],
                'designation': employee_result[1],
                'joining_date': employee_result[2],
                'department': employee_result[3],
                'education': employee_result[4], 
            }
        else:
            temp1 = {}
        
        if gm_result:
            temp2 ={
                'monitor_id': gm_result[0],
                'designation': gm_result[1],
                'department': gm_result[2],
            }
        else:
            temp2 = {}

        context = {
            'citizen_result': temp,
            'employee_result': temp1,
            'gm_result': temp2,
        }

        # print(employee_result)
        
        if citizen_result:
            # Get column names from cursor description
            columns = [col[0] for col in cursor.description]
            citizen_info = dict(zip(columns, citizen_result))
            context['citizen_info'] = citizen_info
            citizen_id = citizen_info['citizen_id']
            
            # Continue with your existing queries for tax_records, certificates, etc.
            # Get tax records
            cursor.execute("""
                SELECT tax_type, amount, due_date, payment_date, payment_status, payment_method
                FROM TAX_RECORD
                WHERE citizen_id = %s
                ORDER BY due_date DESC
            """, [citizen_id])
            tax_records = []
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                tax_records.append(dict(zip(columns, row)))
            context['tax_records'] = tax_records
            
            # Rest of your existing queries remain the same...
            # Get certificates
            cursor.execute("""
                SELECT certificate_type, issue_date, valid_until
                FROM CERTIFICATE
                WHERE citizen_id = %s
                ORDER BY issue_date DESC
            """, [citizen_id])
            certificates = []
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                certificates.append(dict(zip(columns, row)))
            context['certificates'] = certificates
            
            # Get property records
            cursor.execute("""
                SELECT address as name, property_type, area, survey_number as survey_num, 
                       registry_date as registration_date, value
                FROM PROPERTY
                WHERE citizen_id = %s
                ORDER BY registry_date DESC
            """, [citizen_id])
            property_records = []
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                property_records.append(dict(zip(columns, row)))
            context['property_records'] = property_records
            
            # Get complaints
            cursor.execute("""
                SELECT complaint_id, description, complaint_type, complaint_date
                FROM COMPLAINT
                WHERE citizen_id = %s
                ORDER BY complaint_date DESC
            """, [citizen_id])
            complaints = []
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                complaint_dict = dict(zip(columns, row))
                complaint_dict["get_complaint_type_display"] = complaint_dict["complaint_type"]
                complaints.append(complaint_dict)

            context['complaints'] = complaints
        
        # Get schemes (available to all users regardless of citizen status)
        cursor.execute("""
            SELECT scheme_name as name, start_date, end_date, criteria
            FROM SCHEME
            WHERE end_date IS NULL OR end_date >= CURRENT_DATE
            ORDER BY start_date DESC
        """)
        schemes = []
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            schemes.append(dict(zip(columns, row)))
        context['schemes'] = schemes
    
    return render(request, 'user/dashboard.html', context)

# New function to handle profile updates
def update_profile(request):
    # Check if user is logged in
    if 'user_id' not in request.session:
        return redirect('login')
    
    if request.method == 'POST':
        # Get form data
        citizen_id = request.POST.get('citizen_id')
        name = request.POST.get('name')
        house_number = request.POST.get('house_number')
        aadhar_number = request.POST.get('aadhar_number')
        date_of_birth = request.POST.get('date_of_birth')
        occupation = request.POST.get('occupation')
        
        # Validate data
        if not citizen_id or not name or not house_number:
            messages.error(request, "Required fields cannot be empty")
            return redirect('dashboard')
        
        # Update citizen data in the database
        with connection.cursor() as cursor:
            try:
                cursor.execute("""
                    UPDATE CITIZEN
                    SET name = %s, house_number = %s, aadhar_number = %s, 
                        date_of_birth = %s, occupation = %s
                    WHERE citizen_id = %s
                """, [name, house_number, aadhar_number, date_of_birth, occupation, citizen_id])
                
                messages.success(request, "Profile updated successfully")
            except Exception as e:
                messages.error(request, f"Error updating profile: {str(e)}")
    
    return redirect('dashboard')

def add_complaint(request):
    """Handle adding a new complaint."""
    if request.method == "POST":
        citizen_id = request.session.get("citizen_id")
        if not citizen_id:
            return redirect("login")

        complaint_type = request.POST.get("complaint_type")
        description = request.POST.get("description")
        complaint_date = datetime.date.today()

        #print(f"Adding complaint: {complaint_type}, {description}, {complaint_date}")

        # Insert the new complaint
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO COMPLAINT (citizen_id, complaint_type, description, complaint_date)
                VALUES (%s, %s, %s, %s)
            """, [citizen_id, complaint_type, description, complaint_date])

        return redirect("dashboard")



@csrf_exempt
def remove_complaint(request):
    """Handle removing a complaint."""
    if request.method == "POST":
        complaint_id = request.POST.get("complaint_id")

        # Delete the complaint
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM COMPLAINT WHERE complaint_id = %s", [complaint_id])

        return JsonResponse({"success": True})

    return JsonResponse({"success": False}, status=400)



def view_notices(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT notice_id, title, content, notice_date, expiry_date FROM NOTICE ORDER BY notice_date DESC;")
        notices = cursor.fetchall()

    # Convert the result into a list of dictionaries for easier template rendering
    notice_list = [
        {'notice_id': row[0], 'title': row[1], 'content': row[2], 'notice_date': row[3], 'expiry_date': row[4]}
        for row in notices
    ]

    return render(request, 'user/notices.html', {'notices': notice_list})



def view_village_info(request, user_id):
    with connection.cursor() as cursor:
        # Get citizen_id and village_id
        cursor.execute("""
            SELECT citizen_id, village_id
            FROM CITIZEN
            WHERE user_id = %s
        """, [user_id])
        result = cursor.fetchone()

        if not result:
            return JsonResponse({"error": "Citizen not found for user"}, status=400)

        citizen_id, village_id = result

        # Retrieve educational records
        cursor.execute("""
            SELECT schools, colleges, students, teachers, literacy_rate, record_date
            FROM education_record
            WHERE village_id = %s
            ORDER BY record_date DESC
        """, [village_id])

        columns = [col[0] for col in cursor.description]
        education_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Retrieve agricultural records
        cursor.execute("""
            SELECT total_agricultural_land, irrigated_land, major_crops, farmers_count, subsidy_amount, record_date
            FROM agriculture_record
            WHERE village_id = %s
            ORDER BY record_date DESC
        """, [village_id])

        columns = [col[0] for col in cursor.description]
        agriculture_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

        # Retrieve health records
        cursor.execute("""
            SELECT healthcare_facilities, doctors, nurses, beds, patients_treated, vaccination_count, record_date
            FROM HEALTH_RECORD
            WHERE village_id = %s
            ORDER BY record_date DESC
        """, [village_id])

        columns = [col[0] for col in cursor.description]
        health_data = [dict(zip(columns, row)) for row in cursor.fetchall()]

    return render(request, 'user/village_info.html', {'education_data': education_data, 'agriculture_data' : agriculture_data, 'health_data' : health_data})

def update_user_roles(request):
    context = {'users': []}
    
    if request.method == 'POST':
        # Iterate over all POST keys to find role updates
        for key in request.POST:
            if key.startswith('role_'):
                user_id = key.split('_')[1]
                new_role = request.POST.get(key)
                
                # Update user role
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users
                        SET role = %s
                        WHERE user_id = %s
                    """, [new_role, user_id])
        
        messages.success(request, "Roles updated successfully")
        return redirect('update_user_roles')

        # GET request handling
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT user_id, username, email, phone, role
            FROM users
            ORDER BY user_id
        """)
        users = []
        for row in cursor.fetchall():
            users.append({
                'user_id': row[0],
                'username': row[1],
                'email': row[2],
                'phone': row[3],
                'role': row[4]
            })
        context['users'] = users
        context['roles'] = ['citizen', 'admin', 'employee', 'government_monitor']
        
    return render(request, 'user/update_user_roles.html', context)

def admin_home(request):
    return render(request, 'user/admin_home.html')

def citizen_admin(request):
    context = {'citizens': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM citizen
            ORDER BY citizen_id
        """)
        citizens= []
        for row in cursor.fetchall():
            citizens.append({
                'citizen_id': row[0],
                'user_id': row[1],
                'village_id': row[2],
                'name': row[3],
                'address': row[4],
                'aadhar_number': row[5],
                'date_of_birth': row[6],
                'gender': row[7],
                'occupation':row[8]
            })
        context['citizens'] = citizens
    return render(request,'user/citizen_admin.html',context)

def employee_home(request):
    return render(request,'user/employee_home.html')


# Add this to your existing views.py file (keep all existing code)

def employee_query(request):
    """Handle database queries from employees"""
    context = {
        'query_executed': False,
        'query_results': None,
        'column_names': None,
        'error_message': None
    }
    
    # Check if user is logged in and is an employee
    if 'user_id' not in request.session or request.session.get('role') != 'employee':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login_register')
    
    if request.method == 'POST':
        table_selection = request.POST.get('table_selection')
        filter_field = request.POST.get('filter_field')
        filter_value = request.POST.get('filter_value')
        limit = int(request.POST.get('limit', 100))
        
        # Validate limit to prevent excessive data queries
        if limit < 1:
            limit = 1
        elif limit > 1000:
            limit = 1000
            
        # Define allowed tables and their fields for security
        allowed_tables = {
            'citizen': ['citizen_id', 'user_id', 'village_id', 'name', 'house_number', 'aadhar_number', 'date_of_birth', 'gender', 'occupation'],
            'village': ['village_id', 'village_name', 'district', 'state', 'pincode', 'population'],
            'tax_record': ['tax_id', 'citizen_id', 'tax_type', 'amount', 'due_date', 'payment_date', 'payment_status', 'payment_method'],
            'certificate': ['certificate_id', 'citizen_id', 'certificate_type', 'issue_date', 'valid_until'],
            'property': ['property_id', 'citizen_id', 'address', 'property_type', 'area', 'survey_number', 'registry_date', 'value'],
            'complaint': ['complaint_id', 'citizen_id', 'complaint_type', 'description', 'complaint_date', 'status'],
            'scheme': ['scheme_id', 'scheme_name', 'start_date', 'end_date', 'criteria', 'benefits']
        }
        
        # Validate inputs
        if table_selection not in allowed_tables:
            context['error_message'] = "Invalid table selection"
            return render(request, 'user/employee_query.html', context)
            
        if filter_field and filter_field not in allowed_tables[table_selection]:
            context['error_message'] = "Invalid filter field"
            return render(request, 'user/employee_query.html', context)
            
        try:
            with connection.cursor() as cursor:
                # Construct query safely (avoiding SQL injection)
                query = f"SELECT * FROM {table_selection}"
                params = []
                
                if filter_field and filter_value:
                    query += f" WHERE {filter_field} = %s"
                    params.append(filter_value)
                    
                query += f" LIMIT {limit}"
                
                # Execute query
                cursor.execute(query, params)
                
                # Get column names
                column_names = [col[0] for col in cursor.description]
                
                # Fetch results
                results = cursor.fetchall()
                
                context['query_executed'] = True
                context['query_results'] = results
                context['column_names'] = column_names
                
        except Exception as e:
            context['error_message'] = f"Query error: {str(e)}"
            
    return render(request, 'user/employee_query.html', context)


# Add these updated functions to your views.py file

# Add these updated functions to your views.py file

def advanced_query_begin(request):
    """Initial entry point for advanced query - shows table selection form"""
    # Get all available tables for selection
    tables = {
        "users": "users",
        "village": "village",
        "citizen": "citizen",
        "panchayat_employee": "panchayat_employee",
        "government_monitor": "government_monitor",
        "scheme": "scheme",
        "scheme_enrollment": "scheme_enrollment",
        "complaint": "complaint",
        "certificate": "certificate",
        "tax_record": "tax_record",
        "property": "property",
        "notice": "notice",
        "health_record": "health_record",
        "education_record": "education_record",
        "agriculture_record": "agriculture_record",

        # Add more tables as needed
    }
    
    # Clear any previous query state
    if 'selected_tables' in request.session:
        del request.session['selected_tables']
    if 'selected_columns' in request.session:
        del request.session['selected_columns']
    if 'filters' in request.session:
        del request.session['filters']
    
    return render(request, 'user/advanced_query_step1.html', {'tables': tables})

def advanced_query_step1(request):
    """Process table selection and show column/filter selection form"""
    if request.method == "POST":
        # Get selected tables from form
        selected_tables = request.POST.getlist('tables')
        
        if not selected_tables:
            messages.error(request, "Please select at least one table")
            print("Error")
            return redirect('advanced_query_begin')
        
        # Store selected tables in session
        request.session['selected_tables'] = selected_tables
        #print("OKAY")
        
        # Define available columns for each selected table
        table_columns = {
            'users' : ['user_id','username','password','email','phone','role','registration_date'],
            'village' : ['village_id','village_name','district','state','population','area','pincode'],
            'citizen': ['citizen_id', 'user_id', 'village_id', 'name', 'house_number', 'aadhar_number', 'date_of_birth', 'gender', 'occupation'],
            'panchayat_employee': ['employee_id', 'user_id', 'name', 'designation', 'joining_date', 'department', 'education'],
            'government_monitor': ['monitor_id', 'user_id', 'name', 'department', 'designation'],
            'scheme': ['scheme_id', 'scheme_name','description','criteria' 'start_date', 'end_date', 'budget_allocated'],
            'scheme_enrollment': ['enrollment_id', 'scheme_id','citizen_id','enrollment_date', 'status', 'benefit_amount'],
            'complaint': ['complaint_id', 'citizen_id', 'complaint_type', 'description', 'complaint_date'],
            'certificate': ['certificate_id', 'citizen_id', 'certificate_type', 'issue_date', 'valid_until'],
            'tax_record': ['tax_id', 'citizen_id', 'tax_type', 'amount', 'due_date', 'payment_date', 'payment_status', 'payment_method'],
            'property': ['property_id', 'citizen_id', 'property_type', 'address', 'area', 'survey_number', 'registry_date', 'value'],
            'notice': ['notice_id', 'title', 'content', 'notice_date', 'expiry_date', 'employee_id'],
            'health_record': ['health_id', 'village_id', 'record_date', 'healthcare_facilities', 'doctors', 'nurses','beds','patients_treated','vaccination_count'],
            'education_record': ['education_id', 'village_id', 'record_date', 'schools', 'colleges', 'students','teachers','literacy_rate'],
            'agriculture_record': ['agriculture_id', 'village_id', 'record_date', 'total_agricultural_land', 'irrigated_land', 'major_crops','farmers_count','subsidy_amount'],
        }
        
        # Create a dict of only the selected tables and their columns
        selected_tables_columns = {}
        for table in selected_tables:
            if table in table_columns:
                selected_tables_columns[table] = table_columns[table]
        
        return render(request, 'user/advanced_query_step2.html', {'selected_tables': selected_tables_columns})
    
    # If not a POST request, redirect back to the beginning
    return redirect('advanced_query_begin')

def advanced_query_step2(request):
    """Process column/filter selection and execute query"""
    # Get selected tables from session
    selected_tables = request.session.get('selected_tables', [])
    
    if not selected_tables:
        # If no tables in session, start over
        print("Error")
        return redirect('advanced_query_begin')
    
    if request.method == "POST":
        # Initialize containers for filters and display columns
        filters = {}
        display_columns = []
        
        # Process the form data
        for key, value in request.POST.items():
            # Check for display column selections
            if key.startswith('display_'):
                # Remove the 'display_' prefix
                remaining = key[8:]  # 'display_' is 8 characters
                
                # Find the last underscore which separates the column name
                last_underscore_index = remaining.rfind('_')
                
                if last_underscore_index != -1:
                    table = remaining[:last_underscore_index]
                    column = remaining[last_underscore_index+1:]
                    
                    # Handle tables with underscores in their names
                    for t in selected_tables:
                        if remaining.startswith(t) and len(t) <= len(table):
                            table = t
                            column = remaining[len(t)+1:]  # +1 for the underscore
                            break
                    
                    display_columns.append(f"{table}.{column}")
            
            # Check for filter values
            elif key.startswith('filter_'):
                # Remove the 'filter_' prefix
                remaining = key[7:]  # 'filter_' is 7 characters
                
                # Find the last underscore which separates the column name
                last_underscore_index = remaining.rfind('_')
                
                if last_underscore_index != -1 and value.strip():
                    table = remaining[:last_underscore_index]
                    column = remaining[last_underscore_index+1:]
                    
                    # Handle tables with underscores in their names
                    for t in selected_tables:
                        if remaining.startswith(t) and len(t) <= len(table):
                            table = t
                            column = remaining[len(t)+1:]  # +1 for the underscore
                            break
                    
                    filters[f"{table}.{column}"] = value.strip()
        
        # Store in session for use in execute
        request.session['filters'] = filters
        request.session['display_columns'] = display_columns
        request.session.modified = True  # Ensure session is saved
        
        # Redirect to execute the query
        return redirect('advanced_query_execute')
    
    # If not a POST request (or session is missing data)
    return redirect('advanced_query_begin')

def advanced_query_execute(request):
    """Execute the query and display results"""
    # Get data from session
    selected_tables = request.session.get('selected_tables', [])
    filters = request.session.get('filters', {})
    display_columns = request.session.get('display_columns', [])
    
    if not selected_tables:
        messages.error(request, "Missing query parameters. Please start over.")
        return redirect('advanced_query_begin')
    
    try:
        # Build the SELECT clause with only checked columns
        if not display_columns:
            # If no columns explicitly selected, select all from all tables
            select_parts = []
            for table in selected_tables:
                select_parts.append(f"{table}.*")
            select_clause = "SELECT " + ", ".join(select_parts)
        else:
            # Use only the selected columns
            select_clause = "SELECT " + ", ".join(display_columns)
        print(select_clause)
        print('1oxcv\n')
        # FROM clause with first table
        from_clause = f"FROM {selected_tables[0]}"
        
        # Add JOINS for remaining tables with automatic common column detection
        join_clauses = []
        joined_tables = {selected_tables[0]}
        
        if len(selected_tables) > 1:
            for table_to_join in selected_tables[1:]:
                # Try to find a common column between this table and any already joined table
                join_found = False
                
                for joined_table in joined_tables:
                    with connection.cursor() as cursor:
                        # Get columns for the joined table
                        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s", [joined_table])
                        joined_table_columns = [row[0] for row in cursor.fetchall()]
                        
                        # Get columns for the table to join
                        cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table_to_join])
                        table_to_join_columns = [row[0] for row in cursor.fetchall()]
                        
                        # Find common columns (potential join keys)
                        common_columns = set(joined_table_columns) & set(table_to_join_columns)
                        
                        # Prioritize columns that look like foreign keys
                        potential_join_columns = []
                        for col in common_columns:
                            if col.endswith('_id'):
                                potential_join_columns.append(col)
                        
                        # If no columns ending with _id, use any common column
                        if not potential_join_columns and common_columns:
                            potential_join_columns = list(common_columns)
                        
                        # Use the first potential join column
                        if potential_join_columns:
                            join_col = potential_join_columns[0]
                            join_clauses.append(f"LEFT JOIN {table_to_join} ON {joined_table}.{join_col} = {table_to_join}.{join_col}")
                            join_found = True
                            break
                
                if not join_found:
                    # If no common column found, use CROSS JOIN
                    join_clauses.append(f"CROSS JOIN {table_to_join}")
                
                joined_tables.add(table_to_join)
        
        # Build the WHERE clause for filters
        where_clauses = []
        params = []
        for filter_col, filter_val in filters.items():
            where_clauses.append(f"{filter_col} = %s")
            params.append(filter_val)
        
        # Assemble the complete query
        query_sql = select_clause + " " + from_clause
        if join_clauses:
            query_sql += " " + " ".join(join_clauses)
        if where_clauses:
            query_sql += " WHERE " + " AND ".join(where_clauses)
        
        # Add a reasonable limit
        query_sql += " LIMIT 1000"
        
        # Execute the query
        with connection.cursor() as cursor:
            cursor.execute(query_sql, params)
            
            # Get column names
            column_names = [col[0] for col in cursor.description]
            
            # Fetch the results
            query_results = cursor.fetchall()
        
        # Render the results page
        return render(request, 'user/query_results.html', {
            'query_sql': query_sql,
            'query_results': query_results,
            'column_names': column_names
        })
    
    except Exception as e:
        # print('1000\n')
        messages.error(request, f"Query execution error: {str(e)}")
        return redirect('advanced_query_begin')



# Update the employee_home view to include a link to the advanced query page
def employee_home(request):
    return render(request, 'user/employee_home.html')
def citizen_admin(request):
    context = {'citizens': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM citizen
            ORDER BY citizen_id
        """)
        citizens= []
        for row in cursor.fetchall():
            citizens.append({
                'citizen_id': row[0],
                'user_id': row[1],
                'village_id': row[2],
                'name': row[3],
                'address': row[4],
                'aadhar_number': row[5],
                'date_of_birth': row[6],
                'gender': row[7],
                'occupation':row[8]
            })
        context['citizens'] = citizens
    return render(request,'user/citizen_admin.html',context)
def monitor_admin(request):
    context = {'monitors': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM government_monitor
            ORDER BY monitor_id
        """)
        monitors= []
        for row in cursor.fetchall():
            monitors.append({
                'monitor_id': row[0],
                'user_id': row[1],
                'name': row[2],
                'department': row[3],
                'designation': row[4]
  
            })
        context['monitors'] = monitors
    return render(request,'user/monitor_admin.html',context)
def employee_admin(request):
    context = {'employees': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM panchayat_employee
            ORDER BY employee_id
        """)
        employees = []
        for row in cursor.fetchall():
            employees.append({
                'employee_id': row[0],
                'user_id': row[1],
                'name': row[2],
                'designation': row[3],
                'joining_date': row[4],
                'department': row[5],
                'education': row[6]
            })
        context['employees'] = employees
    return render(request, 'user/employee_admin.html', context)
def scheme_admin(request):
    context = {'schemes': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM scheme
            ORDER BY scheme_id
        """)
        schemes = []
        for row in cursor.fetchall():
            schemes.append({
                'scheme_id': row[0],
                'scheme_name': row[1],
                'description': row[2],
                'criteria': row[3],
                'start_date': row[4],
                'end_date': row[5],
                'budget_allocated': row[6]
            })
        context['schemes'] = schemes
    return render(request, 'user/scheme_admin.html', context)
def scheme_enrollment_admin(request):
    context = {'enrollments': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM scheme_enrollment
            ORDER BY enrollment_id
        """)
        enrollments = []
        for row in cursor.fetchall():
            enrollments.append({
                'enrollment_id': row[0],
                'scheme_id': row[1],
                'citizen_id': row[2],
                'enrollment_date': row[3],
                'status': row[4],
                'benefit_amount': row[5]
            })
        context['enrollments'] = enrollments
    return render(request, 'user/scheme_enrollment_admin.html', context)
def complaint_admin(request):
    context = {'complaints': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM complaint
            ORDER BY complaint_id
        """)
        complaints = []
        for row in cursor.fetchall():
            complaints.append({
                'complaint_id': row[0],
                'citizen_id': row[1],
                'complaint_type': row[2],
                'description': row[3],
                'complaint_date': row[4]
            })
        context['complaints'] = complaints
    return render(request, 'user/complaint_admin.html', context)
def certificate_admin(request):
    context = {'certificates': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM certificate
            ORDER BY certificate_id
        """)
        certificates = []
        for row in cursor.fetchall():
            certificates.append({
                'certificate_id': row[0],
                'citizen_id': row[1],
                'certificate_type': row[2],
                'issue_date': row[3],
                'valid_until': row[4]
            })
        context['certificates'] = certificates
    return render(request, 'user/certificate_admin.html', context)
def tax_record_admin(request):
    context = {'tax_records': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM tax_record
            ORDER BY tax_id
        """)
        tax_records = []
        for row in cursor.fetchall():
            tax_records.append({
                'tax_id': row[0],
                'citizen_id': row[1],
                'tax_type': row[2],
                'amount': row[3],
                'due_date': row[4],
                'payment_date': row[5],
                'payment_status': row[6],
                'payment_method': row[7]
            })
        context['tax_records'] = tax_records
    return render(request, 'user/tax_record_admin.html', context)
def property_admin(request):
    context = {'properties': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM property
            ORDER BY property_id
        """)
        properties = []
        for row in cursor.fetchall():
            properties.append({
                'property_id': row[0],
                'citizen_id': row[1],
                'property_type': row[2],
                'address': row[3],
                'area': row[4],
                'survey_number': row[5],
                'registry_date': row[6],
                'value': row[7]
            })
        context['properties'] = properties
    return render(request, 'user/property_admin.html', context)
def notice_admin(request):
    context = {'notices': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM notice
            ORDER BY notice_id
        """)
        notices = []
        for row in cursor.fetchall():
            notices.append({
                'notice_id': row[0],
                'title': row[1],
                'content': row[2],
                'notice_date': row[3],
                'expiry_date': row[4],
                'employee_id': row[5]
            })
        context['notices'] = notices
    return render(request, 'user/notice_admin.html', context)
def health_record_admin(request):
    context = {'health_records': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM health_record
            ORDER BY health_id
        """)
        health_records = []
        for row in cursor.fetchall():
            health_records.append({
                'health_id': row[0],
                'village_id': row[1],
                'record_date': row[2],
                'healthcare_facilities': row[3],
                'doctors': row[4],
                'nurses': row[5],
                'beds': row[6],
                'patients_treated': row[7],
                'vaccination_count': row[8]
            })
        context['health_records'] = health_records
    return render(request, 'user/health_record_admin.html', context)
def education_record_admin(request):
    context = {'education_records': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM education_record
            ORDER BY education_id
        """)
        education_records = []
        for row in cursor.fetchall():
            education_records.append({
                'education_id': row[0],
                'village_id': row[1],
                'record_date': row[2],
                'schools': row[3],
                'colleges': row[4],
                'students': row[5],
                'teachers': row[6],
                'literacy_rate': row[7]
            })
        context['education_records'] = education_records
    return render(request, 'user/education_record_admin.html', context)
def agriculture_record_admin(request):
    context = {'agriculture_records': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM agriculture_record
            ORDER BY agriculture_id
        """)
        agriculture_records = []
        for row in cursor.fetchall():
            agriculture_records.append({
                'agriculture_id': row[0],
                'village_id': row[1],
                'record_date': row[2],
                'total_agricultural_land': row[3],
                'irrigated_land': row[4],
                'major_crops': row[5],
                'farmers_count': row[6],
                'subsidy_amount': row[7]
            })
        context['agriculture_records'] = agriculture_records
    return render(request, 'user/agriculture_record_admin.html', context)
def village_admin(request):
    context = {'village_records': []}
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM VILLAGE
            ORDER BY village_id
        """)
        village_records = []
        for row in cursor.fetchall():
            village_records.append({
                'village_id': row[0],
                'village_name': row[1],
                'district': row[2],
                'state': row[3],
                'population': row[4],
                'area': row[5],
                'pincode': row[6]
            })
        context['village_records'] = village_records
    return render(request, 'user/village_admin.html', context)
