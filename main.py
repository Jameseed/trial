from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room
import random
import string
from datetime import datetime, date
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
socketio = SocketIO(app)

# File to store todo lists
TODO_LISTS_FILE = 'todo_lists.json'

# Load todo lists from file
def load_todo_lists():
    if os.path.exists(TODO_LISTS_FILE):
        try:
            with open(TODO_LISTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading todo lists: {e}")
            return {}
    return {}

def save_todo_lists(todo_lists):
    try:
        with open(TODO_LISTS_FILE, 'w') as f:
            json.dump(todo_lists, f, indent=4)
    except Exception as e:
        print(f"Error saving todo lists: {e}")


# Load todo lists at startup
todo_lists = load_todo_lists()

# HTML templates
index_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskMaster Pro</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container {
            max-width: 500px;
            margin-top: 50px;
        }
        .card {
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .btn-custom {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            border: none;
            color: white;
            transition: all 0.3s ease;
        }
        .btn-custom:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
        }
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card p-5">
            <h1 class="text-center mb-4"><i class="fas fa-tasks me-2"></i>TaskMaster Pro</h1>
            <p class="text-center text-light mb-4">Revolutionize your productivity</p>
            <div class="d-grid gap-3">
                <a href="{{ url_for('create_list') }}" class="btn btn-custom btn-lg">
                    <i class="fas fa-plus-circle me-2"></i>Create New List
                </a>
                <form action="{{ url_for('join_list') }}" method="POST" class="mt-3">
                    <div class="input-group">
                        <input type="text" name="list_code" class="form-control form-control-lg" placeholder="Enter 5-digit list code" required>
                        <button type="submit" class="btn btn-custom">
                            <i class="fas fa-sign-in-alt me-2"></i>Join
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
"""

todo_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TaskMaster Pro - Your List</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container {
            max-width: 800px;
            margin-top: 30px;
        }
        .card {
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .task-item {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            margin-bottom: 10px;
            transition: all 0.3s ease;
        }
        .task-item:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .task-item.today {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        }
        .btn-custom {
            background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
            border: none;
            color: white;
            transition: all 0.3s ease;
        }
        .btn-custom:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .form-control {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
        }
        .form-control::placeholder {
            color: rgba(255, 255, 255, 0.7);
        }
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        }
        .modal-content {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        .success-animation {
            animation: successPulse 2s ease-out;
        }
        @keyframes successPulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        .task-added {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 15px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card p-4">
            <h1 class="text-center mb-4"><i class="fas fa-list-alt me-2"></i>Your TaskMaster List</h1>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                            {{ message }}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <div id="taskAddedMessage" class="task-added">
                <i class="fas fa-check-circle me-2"></i>Task added successfully!
            </div>
            <button type="button" class="btn btn-custom mb-4" data-bs-toggle="modal" data-bs-target="#addTaskModal">
                <i class="fas fa-plus-circle me-2"></i>Add New Task
            </button>
            <ul class="list-group" id="task-list">
            {% for item in items %}
                <li class="list-group-item task-item {% if item['due_date'] == today %}today{% endif %}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h5 class="mb-1">{{ item['text'] }}</h5>
                            <small class="text-light">Due: {{ item['due_date'] }} ({{ item['days_remaining'] }} days left)</small>
                        </div>
                        {% if is_creator %}
                        <form method="POST">
                            <input type="hidden" name="delete" value="{{ loop.index0 }}">
                            <button type="submit" class="btn btn-danger btn-sm">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </form>
                        {% endif %}
                    </div>
                </li>
            {% endfor %}
            </ul>
            <div class="mt-4">
                <p class="text-center">Share this list code: <strong>{{ list_id }}</strong></p>
                <div class="text-center">
                    <a href="{{ url_for('index') }}" class="btn btn-custom btn-sm">
                        <i class="fas fa-home me-2"></i>Home
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Add Task Modal -->
    <div class="modal fade" id="addTaskModal" tabindex="-1" aria-labelledby="addTaskModalLabel" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="addTaskModalLabel">Add New Task</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="addTaskForm">
                        <div class="mb-3">
                            <label for="taskText" class="form-label">Task</label>
                            <input type="text" class="form-control" id="taskText" name="item" required>
                        </div>
                        <div class="mb-3">
                            <label for="dueDate" class="form-label">Due Date</label>
                            <input type="date" class="form-control" id="dueDate" name="due_date" required min="{{ today }}">
                        </div>
                        <button type="submit" class="btn btn-custom">Add Task</button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        var socket = io();
        socket.on('connect', function() {
            socket.emit('join', {list_id: '{{ list_id }}'});
        });
        socket.on('update_list', function(data) {
            location.reload();
        });

        document.getElementById('addTaskForm').addEventListener('submit', function(e) {
            e.preventDefault();
            var form = this;
            var formData = new FormData(form);
            fetch('{{ url_for("todo_list", list_id=list_id) }}', {
                method: 'POST',
                body: formData
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    var modal = bootstrap.Modal.getInstance(document.getElementById('addTaskModal'));
                    modal.hide();
                    
                    var taskAddedMessage = document.getElementById('taskAddedMessage');
                    taskAddedMessage.style.display = 'block';
                    taskAddedMessage.classList.add('success-animation');
                    
                    setTimeout(() => {
                        taskAddedMessage.style.display = 'none';
                        taskAddedMessage.classList.remove('success-animation');
                        location.reload();
                    }, 2000);
                } else {
                    alert(data.message);
                }
            });
        });
    </script>
</body>
</html>
"""

def generate_list_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

@app.route('/')
def index():
    return render_template_string(index_template)

@app.route('/create')
def create_list():
    list_id = generate_list_code()
    while list_id in todo_lists:
        list_id = generate_list_code()
    todo_lists[list_id] = []
    session['creator'] = list_id
    save_todo_lists(todo_lists)
    return redirect(url_for('todo_list', list_id=list_id))

@app.route('/join', methods=['POST'])
def join_list():
    list_id = request.form['list_code']
    if list_id in todo_lists:
        return redirect(url_for('todo_list', list_id=list_id))
    else:
        return "List not found", 404

@app.route('/<list_id>', methods=['GET', 'POST'])
def todo_list(list_id):
    if list_id not in todo_lists:
        return "List not found", 404

    is_creator = session.get('creator') == list_id
    today = date.today().isoformat()

    if request.method == 'POST':
        if 'item' in request.form and 'due_date' in request.form:
            due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
            if due_date < date.today():
                return jsonify({"success": False, "message": "Due date cannot be in the past"})
            else:
                new_item = {
                    'text': request.form['item'],
                    'due_date': request.form['due_date'],
                    'days_remaining': (due_date - date.today()).days
                }
                todo_lists[list_id].append(new_item)
                save_todo_lists(todo_lists)
                socketio.emit('update_list', room=list_id)
                return jsonify({"success": True, "message": "Task added successfully!"})
        elif 'delete' in request.form and is_creator:
            index = int(request.form['delete'])
            if 0 <= index < len(todo_lists[list_id]):
                del todo_lists[list_id][index]
                flash("Task deleted successfully!", "success")
                save_todo_lists(todo_lists)
                socketio.emit('update_list', room=list_id)
        return redirect(url_for('todo_list', list_id=list_id))

    items = sorted(todo_lists[list_id], key=lambda x: x['due_date'])
    for item in items:
        due_date = datetime.strptime(item['due_date'], '%Y-%m-%d').date()
        item['days_remaining'] = (due_date - date.today()).days

    return render_template_string(todo_template, items=items, list_id=list_id, is_creator=is_creator, today=today)

@socketio.on('join')
def on_join(data):
    list_id = data['list_id']
    join_room(list_id)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
