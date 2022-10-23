from socketserver import UDPServer
from flask import Flask, request, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit, send
from collections import defaultdict
import requests, json, random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test'
socketio = SocketIO(app, cors_allowed_origins='*')
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

rooms = defaultdict(list)           # key: room,    value: list of users
current_users = defaultdict(tuple)  # key: room id, value: (room id, username)
room_questions = defaultdict(list)  # key: room id, value: list of questions + its title
room_name_pairs1 = defaultdict(str) # key: room id, value: room name
room_name_pairs2 = defaultdict(str) # key: room name, value: room id
chat_logs = defaultdict(list)       # key: room id, value: list of messages
room_number = 0

LEETCODE_URL = "https://leetcode.com/api/problems/algorithms/"
algorithms_problems_json = requests.get(LEETCODE_URL).content
algorithms_problems_json = json.loads(algorithms_problems_json)["stat_status_pairs"]

@socketio.on('create_room')
def create_room(data):
    global algorithms_problems_json
    # free and easy questions
    algorithms_problems_json = [obj for obj in algorithms_problems_json if not obj['paid_only'] and obj['difficulty']['level'] == 1]
    # free questions
    # algorithms_problems_json = [obj for obj in algorithms_problems_json if not obj['paid_only']]
    number_of_questions = len(algorithms_problems_json)

    # Add user in a room
    user_id = request.sid

    if user_id in current_users:
        leave_room()

    global room_number
    room_number += 1
    room_id = str(room_number) # request.sid
    rooms[room_id].append(data['name'])
    rooms[room_id] = list(set(rooms[room_id]))

    room_name = data['room_name']
    room_name_pairs1[room_id] = room_name
    room_name_pairs2[room_name] = room_id

    print("A new room is successfully created!\nThe list of rooms: ", rooms)
    current_users[user_id] = (room_id, data['name'])

    # Generate random 4 leetcode questions
    list_of_question_numbers = [random.randint(0, number_of_questions) for _ in range(4)]
    list_of_question_links = []
    question_title = []

    for question_id in list_of_question_numbers:
        link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['stat']["question__title_slug"] + '/'
        list_of_question_links.append(link)
        question_title.append(algorithms_problems_json[question_id]['stat']["question__title"])
    
    for i in range(4):
        room_questions[room_id].append((question_title[i], list_of_question_links[i]))
    print(room_questions)

    players = rooms[room_id]
    questions = room_questions[room_id]
    emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name})
    socketio.server.enter_room(user_id, room_id)

    messaging({'message': data['name'] + ' just joined the room!', 'type': 'admin'})

@socketio.on('retrieve_room_info')
def retrieve_room_info():
    user_id = request.sid

    if user_id in current_users:
        room_id = current_users[user_id][0]
        players = rooms[room_id]
        questions = room_questions[room_id]
        convo = chat_logs[room_id]
        room_name = room_name_pairs1[room_id]

        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name}, room=room_id)
        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'chatlog': convo, 'room_name': room_name})

        print('Chat logs:')
        print(chat_logs)

@socketio.on('join_room')
def join_room(data):
    user_id = request.sid
    tmp = data['room_id']

    if not tmp.isdigit():
        room_name = tmp
        room_id = room_name_pairs2[room_name]
    else:
        room_id = tmp
        room_name = room_name_pairs1[room_id]

    user = data['name']

    if room_id in rooms:
        rooms[room_id].append(user)
        rooms[room_id] = list(set(rooms[room_id]))

        if user_id in current_users and current_users[user_id][0] != room_id:
            print('test')
            leave_room()
        
        if user_id not in current_users:
            print('test2')
            socketio.server.enter_room(user_id, room_id)
            current_users[user_id] = (room_id, user)

            room_name = room_name_pairs1[room_id]

            players = rooms[room_id]
            questions = room_questions[room_id]
            convo = user + ' just joined room ' + room_name + '!'

            messaging({'message': convo, 'type': 'admin'})
            emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'chatlog': chat_logs[room_id], 'room_name': room_name})

            print("New user join room " + room_name + ". The users now are: ", rooms[room_id])
            print(rooms)

@socketio.on('leave_room')
def leave_room():
    user_id = request.sid

    if user_id not in current_users:
        print('User not in any room!')
        return

    room_id = current_users[user_id][0]
    user = current_users[user_id][1]
    print(current_users)

    if user in rooms[room_id]:
        rooms[room_id].remove(user)

    if len(rooms[room_id]) == 0:
        print("Room is terminated!")
        if room_id in chat_logs:
            del chat_logs[room_id]
        del rooms[room_id]

        room_name = room_name_pairs1[room_id]
        del room_name_pairs1[room_id]
        del room_name_pairs2[room_name]
    else:
        room_name = room_name_pairs1[room_id]
        print("User " + user + " disconnected from " + str(room_id) + ". The users in the current room " +  str(room_id) + " are: ")
        
        for i, user1 in enumerate(rooms[room_id]):
            print(str(i+1) + '. ' + user1)

        players = rooms[room_id]
        questions = room_questions[room_id]
        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name}, room=room_id)
    
    messaging({'message': user + ' just left the room!', 'type': 'admin'})
    del current_users[user_id]
    socketio.server.leave_room(user_id, room_id)

    print(rooms)

@socketio.on('message')
def messaging(data):
    msg = data['message']
    msg_type = data['type'] if 'type' in data else 'chat'

    print(msg)
    user_id = request.sid
    if user_id in current_users:
        room_id = current_users[user_id][0]
        user = current_users[user_id][1]

        room_name = room_name_pairs1[room_id]

        tmp = {'message': msg, 'user': user_id, 'name': user, 'type': msg_type, 'room_name': room_name}
        chat_logs[room_id].append(tmp)

        print('Received message from ' + user + ': ' + msg + ' in room ' + room_name)
        emit('message', tmp, room=room_id)


user_question_status = defaultdict(list) # key: userid value: list of (question_number, 0/1/2)
# 0: not started
# 1: started but unsuccessful
# 2: successfully solved

@socketio.on('submission')
def send_submission(data):
    user_id = request.sid
    submission_status = data['run_success']

    msg = ''

    if user_id in current_users:
        user = current_users[user_id][1]

        if not submission_status:
            msg = current_users[user_id][1] + ' submitted!'
        else:
            percentile = data['runtime_percentile']
            language = data['pretty_lang']

            msg = user + ' completed the problem in ' + language + ', beat ' + str(percentile) + '% of users!'
        messaging({'message': msg, 'type': 'submission'})
                                          
@socketio.on('leaderboard')
def get_rankings(data):
    order = []

    
if __name__ == '__main__':
    socketio.run(app, debug=True)