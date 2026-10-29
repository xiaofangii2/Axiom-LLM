import torch
import torch.nn.functional as F
from model import AxiomLLM
import json
import sys

try:
    with open("vocab.json", "r", encoding="utf-8") as f:
        vocab = json.load(f)
        merges = {tuple(k.split("|")): v for k, v in vocab["merges"].items()}
        c2i = vocab["c2i"]
        i2c = {int(k): v for k, v in vocab["i2c"].items()}
except FileNotFoundError:
    print("找不到 vocab.json，请先运行 train.py")
    sys.exit()

V = len(c2i)
model = AxiomLLM(V)
model.load_state_dict(torch.load("Axiom-LLM.pth"))
model.eval()
T = model.T

def encode(text):
    ids = []
    for w in text.lower().split():
        word = list(w) + ['</w>']
        for pair, merged in merges.items():
            i = 0
            while i < len(word)-1:
                if word[i] == pair[0] and word[i+1] == pair[1]:
                    word[i:i+2] = [merged]
                else:
                    i += 1
        for token in word:
            ids.append(c2i.get(token, c2i["[UNK]"]))
    return ids

print("====================================")
print(f"Axiom-LLM 已加载 | 词表: {V}")
print("====================================")

while True:
    try:
        user_in = input("你: ").strip()
        if user_in == 'exit': break
        if not user_in: continue
        
        ids = encode(user_in)
        idx = ids.copy()
        for _ in range(30):
            logits = model(torch.tensor([idx[-T:]]))[0, -1] / 0.6
            p = F.softmax(logits, dim=-1)
            nx = torch.multinomial(p, 1).item()
            if nx == c2i.get("\n"): break
            idx.append(nx)
            
        out_tokens = [i2c[x] for x in idx[len(ids):]]
        reply = "".join(out_tokens).replace("</w>", " ")
        print(f"AI: {reply.strip()}")
    except KeyboardInterrupt:
        break
