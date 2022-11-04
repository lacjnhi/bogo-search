import json

f = json.load(open('data/lc_questions.json', 'r'))
questions = f["data"]["problemsetQuestionList"]["questions"]
questions = [obj for obj in questions if not obj['paidOnly']]
m = {}
id = []

for i, question in enumerate(questions):
    m[question["titleSlug"]] = (question["title"], question["difficulty"])

# print(id)
json.dump(m, open('data/questions_titleSlug_mappings.json', 'w'))

