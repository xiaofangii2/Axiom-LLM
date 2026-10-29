import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import torch
import torch.nn.functional as F
from model import AxiomLLM
import json
from collections import Counter
import random
import signal
import sys

model = None
def signal_handler(sig, frame):
    sys.stderr = sys.__stderr__
    if model is not None:
        torch.save(model.state_dict(), "Axiom-LLM.pth")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
sys.stderr = open(os.devnull, 'w')

print("步骤 1/3: 生成中英双语语料...")
en_words = ["apple", "banana", "dog", "cat", "car", "book", "water", "sun", "moon", "hello", "hi", "good", "bad", "friend", "happy", "sad", "computer", "music", "play", "run", "eat", "sleep"]
zh_words = ["苹果", "香蕉", "狗", "猫", "汽车", "书", "水", "太阳", "月亮", "你好", "朋友", "高兴", "伤心", "电脑", "音乐", "玩", "跑步", "吃", "睡觉"]

sentences = []
for _ in range(250):
    sentences.append(f"i like {random.choice(en_words)}")
    sentences.append(f"do you like {random.choice(en_words)}")
    sentences.append(f"i am {random.choice(en_words)}")
    sentences.append(f"我喜欢{random.choice(zh_words)}")
    sentences.append(f"你喜欢{random.choice(zh_words)}吗")
    sentences.append(f"我是{random.choice(zh_words)}")

sentences.extend(["hello how are you", "i am fine thank you", "what is your name", "my name is axiom", "你好吗", "我很好", "你叫什么名字", "我叫小智"])
text = "\n".join(sentences).lower().strip()

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

with open("vocab.json", "w", encoding="utf-8") as f:
    json.dump({"merges": {f"{k[0]}|{k[1]}": v for k, v in merges.items()}, "c2i": c2i, "i2c": i2c}, f)

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

print("步骤 3/3: 开始训练...")
model = AxiomLLM(V, d=128, h=4, L=4, T=32)
opt = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.01)
steps = 3000
T = model.T

for step in range(steps):
    i = torch.randint(0, len(data)-T-1, (16,))
    x = torch.stack([data[j:j+T] for j in i])
    y = torch.stack([data[j+1:j+T+1] for j in i])
    logits = model(x)
    loss = F.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    if step % 100 == 0:
        print(f"step {step} loss {loss.item():.3f}", flush=True)

torch.save(model.state_dict(), "Axiom-LLM.pth")
sys.stderr = sys.__stderr__
print("完成，已保存 Axiom-LLM.pth")
