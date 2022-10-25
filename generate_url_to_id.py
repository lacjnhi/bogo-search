import json

f = json.load(open('data/lc_questions.json', 'r'))
questions = f["data"]["problemsetQuestionList"]["questions"]
questions = [obj for obj in questions if not obj['paidOnly']]
m = {}
id = []

for i, question in enumerate(questions):
    m[question["titleSlug"]] = i
print(id)
json.dump(m, open('title_to_id.json', 'w'))

