# Axiom-LLM

![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)
![Python 3.14+](https://img.shields.io/badge/Python-3.14%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red.svg)

Axiom-LLM 是一个专为资源受限环境（如 Termux、移动端 Android）从零手写的中英双语微型 Transformer 语言模型。本项目不依赖任何重型深度学习框架，抛弃了所有臃肿的 API 封装，旨在探索底层矩阵运算与模型架构的纯粹极限。

## 开源协议声明

本项目采用 CC BY-NC-SA 4.0（Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International）协议开源。
这意味着：
1. 署名：您必须给出适当的署名，并提供指向本协议的链接。
2. 非商业性使用：您不得将本项目的代码及衍生模型用于商业目的。
3. 相同方式共享：如果您再混合、转换或者基于本项目进行创作，您必须基于与原先许可协议相同的许可协议分发您的作品。

## 核心特性

1. 极致轻量：整个模型架构约 200 万参数，显存占用极低，可直接在手机端进行训练与推理。
2. 纯手写 BPE 分词器：针对中文无空格和英文词根问题，项目内置了从头实现的 BPE 算法，无需安装 HuggingFace 的 tokenizers 库即可原生兼容中英双语混排。
3. LLaMA 同源架构：采用了与当前主流大模型一致的现代架构，包括 RMSNorm 归一化、SwiGLU 激活函数以及因果多头自注意力机制。
4. 工业级防爆机制：针对手机端浮点数溢出和 BLAS 内存回收异常，内置了全局梯度裁剪、NaN 强制清洗过滤以及防中断静默保存机制，确保训练绝对稳定。

## 模型架构解析

Axiom-LLM 采用 Decoder-Only 的 Transformer 架构，具体参数如下：
- 隐藏层维度（d_model）：128
- 多头注意力头数（heads）：4
- Transformer 层数（layers）：4
- 最大上下文长度（seq_len）：32
- 词表大小（vocab_size）：约 300-500（由语料动态决定）

在处理序列时，模型使用了上三角为负无穷的因果掩码（Causal Mask），确保每个字符只能关注到它之前的字符。在反向传播阶段，除了原生 AdamW 优化器外，还加入了梯度模长限制（Clip Grad Norm）以及 nan_to_num 硬拦截，防止梯度爆炸导致模型崩溃。

## 快速开始

### 环境要求
仅需 Python 环境及 PyTorch 基础包。在 Termux 等移动端环境建议设置 OPENBLAS_NUM_THREADS=1 以降低 CPU 负载和内存回收警告。

### 1. 启动训练
直接运行训练脚本。程序会自动生成数千条中英双语语料，构建 BPE 词表，并开启 3000 步的训练。在训练过程中随时按下 Ctrl+C 中断，程序会自动静默保存当前的模型权重并安全退出，绝对不报错。
执行：python train.py

### 2. 开始对话
训练结束或中断后，会生成权重文件。运行对话脚本即可在终端开启交互。
执行：python chat.py
输入 exit 退出对话。

## 目录结构说明

model.py：模型核心文件，包含 RMSNorm、SwiGLU、Block 以及 AxiomLLM 的类定义。
train.py：训练主程序，包含语料生成、BPE 训练、分词编码及优化器循环。
chat.py：推理程序，负责加载 vocab.json 和 Axiom-LLM.pth 进行流式生成。
.gitignore：配置了忽略大文件，防止数十 MB 的权重文件污染 Git 仓库。

## 进阶玩法

如果你想让它学会更多的词，或者教它说特定的话，请直接打开 train.py，找到 en_words 和 zh_words 两个列表，往里添加你自己的词汇，或者修改 sentences.extend 部分的固定长句。重新运行 train.py，模型就会在几分钟内重新训练并记住你的新设定。

## 开发者致谢

感谢每一个在 Termux 终端里手敲下 python train.py 的极客。Axiom 意为“公理”，代表不容置疑的基础真理。我们希望能在最简陋的算力上，跑出最基础的智能。
