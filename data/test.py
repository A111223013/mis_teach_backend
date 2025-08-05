import json

def add_keypoints(kp_field, container):
    if isinstance(kp_field, list):
        for kp in kp_field:
            container.add(kp)
    elif isinstance(kp_field, str):
        container.add(kp_field)
    else:
        # 如果不是字串也不是list，可以視情況處理
        pass

with open("./error_questions.json", "r", encoding="utf-8") as f:
    data = json.load(f)

key_points_set = set()

for question in data:
    if "key-points" in question:
        add_keypoints(question["key-points"], key_points_set)
    if "sub_questions" in question:
        for sub_q in question["sub_questions"]:
            if "key-points" in sub_q:
                add_keypoints(sub_q["key-points"], key_points_set)

print("出現過的 key-points 項目：")
for kp in sorted(key_points_set):
    print(kp)
