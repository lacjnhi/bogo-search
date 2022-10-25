from socketserver import UDPServer
from flask import Flask, request, render_template
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO, emit, send
from collections import defaultdict
import requests, json, random
import time

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

user_scores = defaultdict(lambda: defaultdict(int)) # key: room_id value: {key: user value: score} 
number_of_questions = defaultdict(int) # key: roomid value: number of questions

file = open('data/lc_questions.json')
algorithms_problems_json = json.load(file)
algorithms_problems_json = algorithms_problems_json['data']['problemsetQuestionList']['questions']
file.close()

file = open('data/title_to_id.json')
title_id_map = json.load(file)
file.close()
# print(title_id_map)

blind_id = {0, 256, 2, 132, 4, 10, 511, 140, 138, 14, 142, 271, 18, 19, 20, 22, 151, 
152, 284, 32, 290, 933, 38, 301, 47, 48, 52, 53, 54, 55, 56, 182, 181, 189, 61, 191, 
197, 198, 199, 69, 72, 202, 75, 203, 204, 78, 208, 464, 344, 217, 90, 349, 221, 97, 
226, 99, 356, 229, 101, 103, 104, 233, 240, 120, 123, 124, 253, 254, 127}
# file = open('data/blind75.json')
# blind75_problems_list = json.load(file)
# for title in blind75_problems_list:
#     if title in title_id_map:
#         blind_id.add(title_id_map[title])
# print(blind_id)
# file.close()

neetcode_id = {0, 1, 2, 3, 4, 6, 9, 10, 14, 16, 18, 19, 20, 21, 22, 24, 537, 541, 32, 
35, 38, 39, 551, 41, 42, 44, 45, 558, 559, 48, 47, 50, 49, 52, 53, 54, 55, 56, 1593, 
61, 65, 69, 71, 72, 73, 75, 587, 77, 78, 590, 593, 83, 89, 90, 604, 96, 97, 99, 101, 
103, 104, 616, 109, 625, 114, 120, 123, 124, 126, 127, 1153, 130, 129, 132, 133, 135, 
137, 138, 140, 142, 145, 149, 151, 152, 154, 160, 683, 690, 181, 182, 189, 190, 191, 
193, 197, 198, 199, 712, 201, 202, 203, 204, 206, 208, 217, 221, 226, 229, 230, 233, 
1260, 240, 249, 253, 254, 256, 262, 264, 271, 276, 279, 284, 290, 295, 810, 301, 818, 
831, 343, 344, 349, 356, 882, 406, 933, 426, 1468, 446, 463, 464, 1506, 492, 511}
# file = open('data/neetcode150.json')
# neetcode150_problems_list = json.load(file)
# for title in neetcode150_problems_list:
#     if title in title_id_map:
#         neetcode_id.add(title_id_map[title])
# print(neetcode_id)
# file.close()

# LEETCODE_URL = "https://leetcode.com/api/problems/algorithms/"
@socketio.on('create_room')
def create_room(data):
    global algorithms_problems_json
    # get from either all questions, blind 75, or neetcode 150
    problem_set = data['problemset']

    # free and easy questions
    # algorithms_problems_json = [obj for obj in algorithms_problems_json if not obj['paid_only'] and obj['difficulty']['level'] == 1]
    # free questions
    algorithms_problems_json = [obj for obj in algorithms_problems_json if not obj['paidOnly']]
    easy_questions = [obj for obj in algorithms_problems_json if obj['difficulty'] == 'Easy']
    med_questions = [obj for obj in algorithms_problems_json if obj['difficulty'] == 'Medium']
    hard_questions = [obj for obj in algorithms_problems_json if obj['difficulty'] == 'Hard']

    # Add user in a room
    user_id = request.sid
    room_name = data['room_name']
    easy, med, hard = data['difficulties']

    if room_name in room_name_pairs2:
        return

    if user_id in current_users:
        leave_room()

    global room_number
    room_number += 1
    room_id = str(room_number) # request.sid
    rooms[room_id].append(data['name'])
    rooms[room_id] = list(set(rooms[room_id]))
    number_of_questions[room_id] = easy + med + hard

    room_name_pairs1[room_id] = room_name
    room_name_pairs2[room_name] = room_id

    current_users[user_id] = (room_id, data['name'])

    # Generate random leetcode questions
    easy_question_numbers = []
    med_question_numbers = []
    hard_question_numbers = []

    topics = data['topics']   
    print(easy, med, hard)
    print()

    list_of_question_links = []
    question_title = []

    # user do not provide topics
    if not topics:
        easy_question_numbers = random.sample(range(0, len(easy_questions)), easy)
        med_question_numbers = random.sample(range(0, len(med_questions)), med)
        hard_question_numbers = random.sample(range(0, len(hard_questions)), hard)

        number_of_questions[room_id] = len(easy_question_numbers) + len(med_question_numbers) + len(hard_question_numbers)

        if number_of_questions[room_id] == 0:
            emit({'message': 'Please choose more than 0 questions to get started!', 'type': 'error'})
            return 

        for question_id in easy_question_numbers:
                link = 'https://www.leetcode.com/problems/' + easy_questions[question_id]['titleSlug'] + '/'
                difficulty = 1
                list_of_question_links.append((link, difficulty))
                question_title.append(easy_questions[question_id]["title"])

        # generate med questions
        for question_id in med_question_numbers:
            link = 'https://www.leetcode.com/problems/' + med_questions[question_id]['titleSlug'] + '/'
            difficulty = 2
            list_of_question_links.append((link, difficulty))
            question_title.append(med_questions[question_id]['title'])

        # generate hard questions
        for question_id in hard_question_numbers:
            link = 'https://www.leetcode.com/problems/' + hard_questions[question_id]['titleSlug'] + '/'
            difficulty = 3
            list_of_question_links.append((link, difficulty))
            question_title.append(hard_questions[question_id]["title"])

    # user provides only 1 topic
    elif len(topics) == 1 and (easy == 0 and med == 0) or (easy == 0 or hard == 0) or (hard == 0 and med == 0):
        if easy == 0 and med == 0:
            hard_question_numbers.extend(generate_questions(topics[0] + ', Hard', hard, problem_set))
        elif easy == 0 and hard == 0:
            med_question_numbers.extend(generate_questions(topics[0] + ', Medium', med, problem_set))
        elif hard == 0 and med == 0:
            easy_question_numbers.extend(generate_questions(topics[0] + ', Easy', easy, problem_set))

        number_of_questions[room_id] = len(easy_question_numbers) + len(med_question_numbers) + len(hard_question_numbers)
        if number_of_questions[room_id] == 0:
            emit({'message': 'No questions matched your preferences.', 'type': 'error'})
            return 

        for question_id in easy_question_numbers:
                link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
                difficulty = 1
                list_of_question_links.append((link, difficulty))
                question_title.append(algorithms_problems_json[question_id]["title"])

        # generate med questions
        for question_id in med_question_numbers:
            link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
            difficulty = 2
            list_of_question_links.append((link, difficulty))
            question_title.append(algorithms_problems_json[question_id]['title'])

        # generate hard questions
        for question_id in hard_question_numbers:
            link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
            difficulty = 3
            list_of_question_links.append((link, difficulty))
            question_title.append(algorithms_problems_json[question_id]["title"])

    # user provides multiple topics
    else:
        possible_easy = []
        possible_med = []
        possible_hard = []

        for t in topics:
            possible_easy.append(t + ', Easy')
            possible_med.append(t + ', Medium')
            possible_hard.append(t + ', Hard')

        # print(possible_easy)
        # print(possible_med)
        # print(possible_hard)

        easy_problems = generate_multiple_topics(possible_easy, easy)
        med_problems = generate_multiple_topics(possible_med, med)
        hard_problems = generate_multiple_topics(possible_hard, hard)

        print('\n')
        print(easy_problems)
        print(med_problems)
        print(hard_problems)
        print('\n')

        for k, v in easy_problems.items():
            easy_question_numbers.extend(generate_questions(k, v, problem_set))

        for k, v in med_problems.items():
            med_question_numbers.extend(generate_questions(k, v, problem_set))

        for k, v in hard_problems.items():
            hard_question_numbers.extend(generate_questions(k, v, problem_set))

        print('\n')
        print(easy_question_numbers)
        print(med_question_numbers)
        print(hard_question_numbers)
        print('\n')

        number_of_questions[room_id] = len(easy_question_numbers) + len(med_question_numbers) + len(hard_question_numbers)
        if number_of_questions[room_id] == 0:
            emit({'message': 'No questions matched your preferences.', 'type': 'error'})
            return 

        for question_id in easy_question_numbers:
                link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
                difficulty = 1
                list_of_question_links.append((link, difficulty))
                question_title.append(algorithms_problems_json[question_id]["title"])

        # generate med questions
        for question_id in med_question_numbers:
            link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
            difficulty = 2
            list_of_question_links.append((link, difficulty))
            question_title.append(algorithms_problems_json[question_id]['title'])

        # generate hard questions
        for question_id in hard_question_numbers:
            link = 'https://www.leetcode.com/problems/' + algorithms_problems_json[question_id]['titleSlug'] + '/'
            difficulty = 3
            list_of_question_links.append((link, difficulty))
            question_title.append(algorithms_problems_json[question_id]["title"])
        
    # print(easy_question_numbers)
    # print(med_question_numbers)
    # print(hard_question_numbers)

    # list_of_question_links = [
    #     'https://www.leetcode.com/problems/two-sum/',
    #     'https://www.leetcode.com/problems/best-time-to-buy-and-sell-stock/',
    #     'https://www.leetcode.com/problems/contains-duplicate/',
    #     'https://www.leetcode.com/problems/product-of-array-except-self/'
    # ]
    # question_title = ['two sum blush', 'stonks', 'duplicate sadge', 'brain ded on easy question']

    # add question status
    user_question_status[room_id][data['name']] = []
    user_scores[room_id][data['name']] = 0
    room_questions[room_id] = []

    for i in range(number_of_questions[room_id]):
        # (title, links, difficulty)
        room_questions[room_id].append((question_title[i], list_of_question_links[i][0], list_of_question_links[i][1]))
        user_question_status[room_id][data['name']].append(0)

    print(room_questions)
    print(user_question_status)

    players = rooms[room_id]
    questions = room_questions[room_id]
    emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name})
    socketio.server.enter_room(user_id, room_id)

    print("A new room is successfully created!\nThe list of rooms: ", rooms)
    messaging({'message': data['name'] + ' just joined the room!', 'type': 'admin'})

def generate_multiple_topics(possible, count):
    problems = defaultdict(int)
    if count <= len(possible):
        request_idx = random.sample(range(0, len(possible)), count)

        for num in request_idx:
            problems[possible[num]] = 1
    elif count > 0:
        val, remain = divmod(count, len(possible))
        for p in possible:
            problems[p] = val
        
        count = remain
        # print(count, len(possible))
        request_idx = random.sample(range(0, len(possible)), count)
        for num in request_idx:
            problems[possible[num]] += 1
    
    return problems

file = open('data/lc_topics.json')
question_topic_difficulty = json.load(file)
def generate_questions(request, count, type): # request is formatted as "Topic, Diff"
    if request in question_topic_difficulty:
        question_list = question_topic_difficulty[request]
        questions = []
        
        if type == 'blind75':
            new_list = []

            for q in question_list:
                if q in blind_id:
                    new_list.append(q)

            if len(new_list) <= count:
                return new_list
            else:
                questions = random.sample(range(0, len(new_list)), count)

                return [new_list[i] for i in questions]
        elif type == 'neetcode150':
            new_list = []

            for q in question_list:
                if q in neetcode_id:
                    new_list.append(q)

            if len(new_list) <= count:
                return new_list
            else:
                questions = random.sample(range(0, len(new_list)), count)

                return [new_list[i] for i in questions]
        else:
            if len(question_list) <= count:
                return question_list
            else:
                questions = random.sample(range(0, len(question_list)), count)

                return [question_list[i] for i in questions]
    else:
        return []

@socketio.on('retrieve_room_info')
def retrieve_room_info():
    user_id = request.sid
    print(current_users)

    if user_id in current_users:
        room_id = current_users[user_id][0]
        players = rooms[room_id]
        questions = room_questions[room_id]
        convo = chat_logs[room_id]
        room_name = room_name_pairs1[room_id]

        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name}, room=room_id)
        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'chatlog': convo, 'room_name': room_name})

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
            emit('room_info', {'players': players}, room=room_id)

            print("New user join room " + room_name + ". The users now are: ", rooms[room_id])
            print(rooms)

            # add question status
            if user not in user_scores[room_id]:
                user_scores[room_id][user] = 0
                for _ in range(number_of_questions[room_id]):
                    user_question_status[room_id][user].append(0)
                print(user_question_status)

@socketio.on('leave_room')
def leave_room():
    user_id = request.sid

    if user_id not in current_users:
        print('User not in any room!')
        emit({'message': 'You are not in a room', 'type': 'error'})
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
        del user_question_status[room_id]
        del number_of_questions[room_id]
        del room_questions[room_id]
        if room_id in user_scores:
            del user_scores[room_id]

    else:
        room_name = room_name_pairs1[room_id]
        print("User " + user + " disconnected from " + str(room_id) + ". The users in the current room " +  str(room_id) + " are: ")

        for i, user1 in enumerate(rooms[room_id]):
            print(str(i+1) + '. ' + user1)

        players = rooms[room_id]
        questions = room_questions[room_id]
        emit('room_info', {'room_id': room_id, 'players': players, 'questions': questions, 'room_name': room_name}, room=room_id, include_self=False)
    
    messaging({'message': user + ' just left the room!', 'type': 'admin', 'include_self': False})

    del current_users[user_id]
    # if room_id in user_question_status and user in user_question_status[room_id]:
    #     del user_question_status[room_id][user]

    # if room_id in user_scores and user in user_scores[room_id]:
    #     del user_scores[room_id][user]

    socketio.server.leave_room(user_id, room_id)

    print(rooms)

@socketio.on('message')
def messaging(data):
    msg = data['message']
    msg_type = data['type'] if 'type' in data else 'chat'
    include_self = data['include_self'] if 'include_self' in data else True

    # get current time
    t = time.localtime()
    cur_time = time.strftime('%H:%M', t)
    print(cur_time)

    print(msg)
    user_id = request.sid
    if user_id in current_users:
        room_id = current_users[user_id][0]
        user = current_users[user_id][1]

        room_name = room_name_pairs1[room_id]

        tmp = {'message': msg, 'user': user_id, 'name': user, 'type': msg_type, 'room_name': room_name, 'time': cur_time}
        chat_logs[room_id].append(tmp)

        print('Received message from ' + user + ': ' + msg + ' in room ' + room_name)
        emit('message', tmp, room=room_id, include_self=include_self)


user_question_status = defaultdict(lambda: defaultdict(list)) # key: roomid value: {key: username value: status 0/1/2}
# 0: not started
# 1: started but unsuccessful
# 2: successfully solved

@socketio.on('submission')
def send_submission(data):
    user_id = request.sid
    submission_status = data['status_msg']
    id = data['curr_id']
    difficulty = data['difficulty']

    msg = ''

    if user_id in current_users:
        user = current_users[user_id][1]
        room_id = current_users[user_id][0]

        if submission_status != 'Accepted':
            if submission_status == 'Wrong Answer' or submission_status == 'Runtime Error':
                msg = current_users[user_id][1] + ' submitted question ' + str(id+1) + '. Error: Code is wrong, do better.'
            elif submission_status == 'Compile Error':
                msg = current_users[user_id][1] + ' submitted question ' + str(id+1) + '. Error: Code cannot be compiled, do better.'
            elif submission_status == 'Time Limit Exceeded':
                msg = current_users[user_id][1] + ' submitted question ' + str(id+1) + '. Error: Time Limit Exceeded. Your code runs slower than my grandma, do better.'
            else:
                msg = current_users[user_id][1] + ' submitted question ' + str(id+1) + '!'

            # set status to 1: started but unsuccessful
            user_question_status[room_id][user][id] = 1
            messaging({'message': msg, 'type': 'submission'})
        elif user_question_status[room_id][user][id] != 2:
            percentile = data['runtime_percentile']
            language = data['pretty_lang']

            # set status to 2: successfully solved
            user_question_status[room_id][user][id] = 2

            msg = user + ' completed the problem ' + str(id+1) + ' in ' + language + ', beat ' + str(round(percentile, 2)) + '% of users!'
            messaging({'message': msg, 'type': 'submission'})
            user_scores[room_id][user] += difficulty

            # user successfully solved every problems
            if len(set(user_question_status[room_id][user])) == 1 and list(set(user_question_status[room_id][user]))[0] == 2:
                msg = user + ' finished the contest!'
                messaging({'message': msg, 'type': 'submission'})

@socketio.on('leaderboard')
def get_rankings():
    # return users, their question statuses and rankings
    user_id = request.sid 
    if user_id in current_users:
        room_id = current_users[user_id][0]

        rankings = user_scores[room_id]
        rankings = sorted(rankings.items(), key=lambda i: i[1], reverse=True)

        for i, value in enumerate(rankings):
            print('\nRoom ' + room_id + ' current rankings:')
            print(str(i+1) + '. ' + value[0] + ' with the score of ' + str(value[1]))

        print(rankings)
        print(user_question_status[room_id])
        emit('leaderboard', {'room_id': room_id, 'rankings': rankings, 'question_status': user_question_status[room_id]})


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')

