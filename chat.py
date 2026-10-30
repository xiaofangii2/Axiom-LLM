import torch
import torch.nn.functional as F
from model import AxiomLLM
import json
import sys
import os

MODEL_PATH = "axiom-llm.pth"
VOCAB_PATH = "vocab.json"

if len(sys.argv) >= 3:
    MODEL_PATH = sys.argv[1]
    VOCAB_PATH = sys.argv[2]

try:
    with open(VOCAB_PATH, "r", encoding="utf-8") as f:
        vocab = json.load(f)
        merges = {tuple(k.split("|")): v for k, v in vocab["merges"].items()}
        c2i = vocab["c2i"]
        i2c = {int(k): v for k, v in vocab["i2c"].items()}
except FileNotFoundError:
    print(f"找不到词表文件: {VOCAB_PATH}")
    sys.exit()

V = len(c2i)
model = AxiomLLM(V, d=160, h=4, L=6, T=32)  # 匹配 400万 参数
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()
T = model.T

def encode(text):
    ids = []
    for w in text.split():
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
print(f"Axiom-LLM 正式对话版已加载 | 词表: {V}")
print("====================================")

while True:
    try:
        user_in = input("用户: ").strip()
        if user_in == 'exit': break
        if not user_in: continue
        
        prompt = f"用户: {user_in}\n助手: "
        ids = encode(prompt)
        idx = ids.copy()
        
        # 生成回复
        for _ in range(40):
            # 温度稍微调高到 0.5，让它别老死循环
            logits = model(torch.tensor([idx[-T:]]))[0, -1] / 0.5
            p = F.softmax(logits, dim=-1)
            nx = torch.multinomial(p, 1).item()
            
            # 遇到换行符停止
            if i2c[nx] == '\n':
                break
            idx.append(nx)
            
        out_tokens = [i2c[x] for x in idx[len(ids):]]
        reply = "".join(out_tokens).replace("</w>", " ").strip()
        
        # 【终极铡刀】如果它开始背后面的题目，直接一刀切掉
        if "用户:" in reply:
            reply = reply.split("用户:")[0].strip()
        if "助手:" in reply:
            reply = reply.split("助手:")[0].strip()
            
        print(f"助手: {reply}")
    except KeyboardInterrupt:
        break
