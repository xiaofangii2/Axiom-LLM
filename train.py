import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import torch
import torch.nn.functional as F
from model import AxiomLLM
import json
from collections import Counter
import signal
import sys
import shutil

# ================= 核心配置区 =================
MODEL_VERSION = "v0.2"
TARGET_D_MODEL = 160
TARGET_LAYERS = 6
TARGET_STEPS = 1500
# ==============================================

model = None
merges, c2i, i2c = None, None, None

def save_current():
    if model is not None and c2i is not None:
        ver_dir = f"version/axiom-llm-{MODEL_VERSION}"
        os.makedirs(ver_dir, exist_ok=True)
        torch.save(model.state_dict(), os.path.join(ver_dir, "axiom-llm.pth"))
        with open(os.path.join(ver_dir, "vocab.json"), "w", encoding="utf-8") as f:
            json.dump({"merges": {f"{k[0]}|{k[1]}": v for k, v in merges.items()}, "c2i": c2i, "i2c": i2c}, f)
        print(f"\n[强行打断] 已自动保存当前状态至 {ver_dir}/")

def signal_handler(sig, frame):
    save_current()
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

print(f"步骤 1/3: 生成问答对语料... (目标版本: {MODEL_VERSION})")
qa_dataset = """
用户: what is your name
助手: my name is axiom
用户: who are you
助手: i am axiom
用户: hello
助手: hello how are you
用户: hi
助手: hello how are you
用户: how are you
助手: i am fine thank you
用户: good morning
助手: good morning my friend
用户: good night
助手: good night sleep well
用户: what is your favorite color
助手: my favorite color is blue
用户: what is your favorite food
助手: my favorite food is rice
用户: 你好
助手: 你好，我是小智
用户: 你是谁
助手: 我是小智
用户: 你好吗
助手: 我很好，谢谢
用户: 你喜欢什么
助手: 我喜欢吃苹果
用户: 你喜欢什么颜色
助手: 我最喜欢的颜色是蓝色
用户: 你叫什么名字
助手: 我叫小智
用户: 早上好
助手: 早上好我的朋友
用户: 晚安
助手: 晚安好梦
用户: 我喜欢你
助手: 谢谢你，我也很喜欢你
用户: do you like music
助手: yes i like music very much
用户: 你喜欢音乐吗
助手: 是的，我很喜欢音乐
"""
text = qa_dataset.strip() + "\n"

print("步骤 2/3: 构建 BPE 词表...")
def build_bpe(text, target_vocab_size=500):
    words = text.split()
    vocab = Counter([tuple(w) + ('</w>',) for w in words])
    chars = sorted(list(set(text)))
    merges = {}
    while len(chars) + len(merges) < target_vocab_size:
        pairs = Counter()
        for word, freq in vocab.items():
            for i in range(len(word)-1):
                pairs[(word[i], word[i+1])] += freq
        if not pairs: break
        best_pair = max(pairs, key=pairs.get)
        merges[best_pair] = "".join(best_pair)
        new_vocab = Counter()
        for word, freq in vocab.items():
            new_word = []
            i = 0
            while i < len(word):
                if i < len(word)-1 and (word[i], word[i+1]) == best_pair:
                    new_word.append("".join(best_pair))
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            new_vocab[tuple(new_word)] += freq
        vocab = new_vocab
    all_tokens = set(chars)
    for merged in merges.values(): all_tokens.add(merged)
    all_tokens.update(["[UNK]", "\n"])
    token_list = sorted(list(all_tokens))
    c2i = {c: i for i, c in enumerate(token_list)}
    i2c = {i: c for i, c in enumerate(token_list)}
    return merges, c2i, i2c

merges, c2i, i2c = build_bpe(text, 500)
V = len(c2i)
print(f"词表大小: {V}")

def encode(text, merges, c2i):
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
    ids.append(c2i["\n"])
    return ids

data_ids = encode(text, merges, c2i)
data = torch.tensor(data_ids, dtype=torch.long)

print(f"步骤 3/3: 开始训练 (400万参数, {TARGET_STEPS}步)...")
model = AxiomLLM(V, d=TARGET_D_MODEL, h=4, L=TARGET_LAYERS, T=32)
opt = torch.optim.AdamW(model.parameters(), lr=1e-4, betas=(0.9, 0.95), weight_decay=0.01)

T = model.T
for step in range(TARGET_STEPS):
    i = torch.randint(0, len(data)-T-1, (16,))
    x = torch.stack([data[j:j+T] for j in i])
    y = torch.stack([data[j+1:j+T+1] for j in i])
    logits = model(x)
    loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
    opt.zero_grad()
    loss.backward()
    
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    for p in model.parameters():
        if p.grad is not None:
            p.grad = torch.nan_to_num(p.grad, nan=0.0, posinf=1.0, neginf=-1.0)
            
    opt.step()
    
    if step >= 0:
        print(f"step {step} | loss: {loss.item():.4f}", flush=True)

save_current()
print(f"完成，已保存至 {ver_dir}/axiom-llm.pth")
