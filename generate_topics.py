from collections import defaultdict
import json

question_topics = defaultdict(list)
topic_list = set()
def generate_topics():
    f = open('data/lc_questions.json')
    questions = json.load(f)['data']['problemsetQuestionList']['questions']
    questions = [obj for obj in questions if not obj['paidOnly']]

    for i in range(len(questions)):
        obj = questions[i]
        topics = obj['topicTags']

        for each_topic in topics:
            question_topics[each_topic['name'] + ', ' + obj['difficulty']].append(i)
            topic_list.add(each_topic['name'])
        
    # print(sorted(topic_list))

# file = open('lc_topics.txt', 'w')
# generate_topics()
# file.write(json.dumps(question_topics))

