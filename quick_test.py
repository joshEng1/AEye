# quick_test.py
from natlangprocessing import handle_command  # e.g., from nlp_core import handle_command

frame = [
    {'label':'person','conf':0.92,'box':[50,120,220,460],'img_w':640,'img_h':480},
    {'label':'person','conf':0.81,'box':[420,130,560,460],'img_w':640,'img_h':480},
    {'label':'dog','conf':0.76,'box':[360,300,460,420],'img_w':640,'img_h':480,'color':'brown'}
]

queries = [
    "how many people on the left?",
    "is there a dog?",
    "where is the dog?",
    "describe the scene"
]

for q in queries:
    print(f"> {q}")
    print(handle_command(q, frame))
