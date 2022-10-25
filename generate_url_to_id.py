import json

f = json.load(open('lc_questions.json', 'r'))
questions = f["data"]["problemsetQuestionList"]["questions"]
m = {}

for i, question in enumerate(questions):
    m[question["titleSlug"]] = i

json.dump(m, open('title_to_id.json', 'w'))

