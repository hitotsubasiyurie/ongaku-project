import json

data = {
    (1,1,"sdasd", "dsfs"): 66666,
    (5345,12,"hfghtr", "dsfs"): 5555
}

print(data)

text = json.dumps(data)

print(text)

print(json.loads(text))







