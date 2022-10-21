from flask import Flask, request, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
socketio = SocketIO(app, cors_allowed_origins='*')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

rooms = defaultdict(list)
room_number = 0
current_users = defaultdict(tuple)

@socketio.on('create_room')
def create_room(user):
    user_id = request.sid
    if user_id not in current_users:
        global room_number
        room_id = str(room_number) # request.sid
        room_number += 1
        rooms[room_id].append(user['name'])
        rooms[room_id] = list(set(rooms[room_id]))

        socketio.emit('current_room_number', room_id)
        socketio.emit('current_players', rooms[room_id])

        print("A new room is successfully created!\nThe list of rooms: ", rooms)
        current_users[user_id] = (room_id, user['name'])

@socketio.on('join_room')
def join_room(room_id, user):
    user_id = request.sid
    print(user_id)
    if user_id not in current_users:
        rooms[room_id].append(user['name'])
        rooms[room_id] = list(set(rooms[room_id]))
        
        socketio.emit('current_room_number', room_id)
        socketio.emit('current_players', rooms[room_id])

        print("New user join room " + str(room_id) + ". The users now are: ", rooms[room_id])
        print(rooms)

        current_users[user_id] = (room_id, user['name'])

@socketio.on('leave_room')
def leave_room():
    user_id = request.sid

    if user_id not in current_users:
        print('User not in any room!')
        return

    room_id = current_users[user_id][0]
    user = current_users[user_id][1]
    rooms[room_id].remove(user)

    if len(rooms[room_id]) == 0:
        del rooms[room_id]
        print("Room is terminated!")
        socketio.emit('current_room_number', None)
        socketio.emit('current_players', None)
    else:
        print("User " + user + " disconnected from " + str(room_id) + ". The users in the current room " +  str(room_id) + " are: ")
        for i, user in enumerate(rooms[room_id]):
            print(str(i+1) + '. ' + user)
        socketio.emit('current_room_number', room_id)
        socketio.emit('current_players', rooms[room_id])
    
    del current_users[user_id]
    print(rooms)

@socketio.on('message')
def messaging(msg):
    user_id = request.sid
    room_id = current_users[user_id][0]
    user = current_users[user_id][1]

    print('Received message from ' + user + ': ' + msg)
    socketio.emit('message', msg)

if __name__ == '__main__':
    socketio.run(app, debug=True)