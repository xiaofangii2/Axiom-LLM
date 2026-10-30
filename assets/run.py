import os, sys, subprocess, tty, termios, shutil, urllib.request, glob

RESET = "\033[0m"
BOLD = "\033[1m"
BG_APP = "\033[48;2;26;27;38m\033[38;2;192;202;245m" 
BORDER_COLOR = "\033[38;2;122;162;247m"          
CYAN = "\033[38;2;187;154;247m"                  
GREEN = "\033[48;2;158;206;106m\033[38;2;26;27;38m"   
RED = "\033[48;2;247;118;142m\033[38;2;26;27;38m"    
BG_SELECTED = "\033[48;2;59;66;82m\033[38;2;125;207;255m" 
COLOR_WARN = "\033[38;2;247;118;142m"
COLOR_OK = "\033[38;2;158;206;106m"
COLOR_INFO = "\033[38;2;125;207;255m"

# ========== 核心配置，全在这里 ==========
CURRENT_VER = "v0.2"
REMOTE_MODEL = "Axiom-LLM.pth"
REMOTE_VOCAB = "Vocab.json"
GITHUB_REPO = "xiaofangii2/Axiom-LLM"
GITEE_REPO = "xiaofangii2/Axiom-LLM"
# ========================================

def get_key():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b': ch += sys.stdin.read(2)
    finally: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def get_versions():
    if not os.path.exists("version"):
        os.makedirs("version")
    return sorted(glob.glob("version/axiom-llm-v*"))

def get_current_path():
    if os.path.exists(".current_version"):
        with open(".current_version", "r") as f:
            path = f.read().strip()
            if os.path.exists(path): return path
    vers = get_versions()
    return vers[0] if vers else None

def draw_base_box(start_x, start_y, box_width, box_height, title_str):
    def print_at(y, x, text, color=""):
        sys.stdout.write(f"\033[{y};{x}H{color}{text}{RESET}{BG_APP}")
    print_at(start_y, start_x, "┌" + "─" * (box_width - 2) + "┐", BORDER_COLOR + BOLD)
    for i in range(1, box_height - 1):
        print_at(start_y + i, start_x, "│", BORDER_COLOR + BOLD)
        print_at(start_y + i, start_x + box_width - 1, "│", BORDER_COLOR + BOLD)
    print_at(start_y + box_height - 1, start_x, "└" + "─" * (box_width - 2) + "┘", BORDER_COLOR + BOLD)
    print_at(start_y + 1, start_x + (box_width - len(title_str)) // 2, title_str, BOLD + CYAN)

def draw_menu(selected_idx, btn_idx):
    cols, lines = shutil.get_terminal_size((80, 24))
    sys.stdout.write("\033[H" + BG_APP + (" " * cols + "\n") * lines + "\033[H")
    box_width, box_height = 64, 16
    start_x, start_y = max(0, (cols - box_width) // 2), max(0, (lines - box_height) // 2)
    draw_base_box(start_x, start_y, box_width, box_height, "┤ AXIOM-LLM LAUNCHER ├")
    
    def print_at(y, x, text, color=""):
        sys.stdout.write(f"\033[{y};{x}H{color}{text}{RESET}{BG_APP}")
        
    cur_ver = get_current_path()
    ver_name = os.path.basename(cur_ver) if cur_ver else "无"
    print_at(start_y + 2, start_x + 4, f"当前版本: {ver_name}", COLOR_INFO)
    print_at(start_y + 3, start_x + 4, "您想要选择哪个选项？", BOLD)
    
    options = [
        "1. 运行模型 (Run Model)         ",
        "2. 重新训练 (Train Model)       ",
        "3. 下载权重 (Download Weights)  ",
        "4. 权重列表 (Weight List)       ",
        "5. 退出系统 (Exit)              "
    ]
    
    has_weights = bool(cur_ver)
    for i, opt in enumerate(options):
        display_opt = opt[:15] + f" {COLOR_WARN}[缺少权重]{RESET}{BG_APP}" if (i == 0 and not has_weights) else opt
        if i == selected_idx: 
            print_at(start_y + 5 + i, start_x + 8, f" > {display_opt}", BG_SELECTED + BOLD)
        else: 
            print_at(start_y + 5 + i, start_x + 10, display_opt)
            
    x_btn = start_x + 12
    ok_str, cancel_str = "   <Ok>   ", " <Cancel> "
    if btn_idx == 0:
        print_at(start_y + 12, x_btn, ok_str, GREEN + BOLD)
        print_at(start_y + 12, x_btn + 14, cancel_str)
    else:
        print_at(start_y + 12, x_btn, ok_str)
        print_at(start_y + 12, x_btn + 14, cancel_str, RED + BOLD)
    sys.stdout.flush()

def draw_download_menu(selected_idx):
    cols, lines = shutil.get_terminal_size((80, 24))
    sys.stdout.write("\033[H" + BG_APP + (" " * cols + "\n") * lines + "\033[H")
    box_width, box_height = 64, 12
    start_x, start_y = max(0, (cols - box_width) // 2), max(0, (lines - box_height) // 2)
    draw_base_box(start_x, start_y, box_width, box_height, "┤ 下载权重 ├")
    
    def print_at(y, x, text, color=""):
        sys.stdout.write(f"\033[{y};{x}H{color}{text}{RESET}{BG_APP}")
    print_at(start_y + 2, start_x + 4, f"远程: {REMOTE_MODEL} / {REMOTE_VOCAB}", COLOR_INFO)
    print_at(start_y + 4, start_x + 4, "请选择下载源 (自动存入 version 文件夹):", BOLD)
    options = ["1. GitHub", "2. Gitee", "3. 返回上一级"]
    for i, opt in enumerate(options):
        if i == selected_idx: 
            print_at(start_y + 6 + i, start_x + 8, f" > {opt}", BG_SELECTED + BOLD)
        else: 
            print_at(start_y + 6 + i, start_x + 10, opt)
    sys.stdout.flush()

def draw_weight_list(selected_idx):
    cols, lines = shutil.get_terminal_size((80, 24))
    vers = get_versions()
    
    sys.stdout.write("\033[H" + BG_APP + (" " * cols + "\n") * lines + "\033[H")
    box_width, box_height = 64, 16
    start_x, start_y = max(0, (cols - box_width) // 2), max(0, (lines - box_height) // 2)
    draw_base_box(start_x, start_y, box_width, box_height, "┤ 权重列表 (回车切换) ├")
    
    def print_at(y, x, text, color=""):
        sys.stdout.write(f"\033[{y};{x}H{color}{text}{RESET}{BG_APP}")
        
    if not vers:
        print_at(start_y + 4, start_x + 4, "version 目录下没有找到任何版本", COLOR_WARN)
    else:
        print_at(start_y + 3, start_x + 4, "方向键选择，回车确认使用该版本:", BOLD)
        cur = get_current_path()
        for i, v in enumerate(vers[:8]):
            name = os.path.basename(v)
            mark = " " if v != cur else "*"
            if i == selected_idx:
                print_at(start_y + 5 + i, start_x + 8, f"{mark} > {name}", BG_SELECTED + BOLD)
            else:
                print_at(start_y + 5 + i, start_x + 8, f"{mark}   {name}")
                
    print_at(start_y + 13, start_x + 4, "按 Esc 或左键返回", BOLD)
    sys.stdout.flush()

def do_download(source):
    sys.stdout.write("\033[?1049l\033[?25h" + RESET)
    os.system('clear')
    
    ver_dir = f"version/axiom-llm-{CURRENT_VER}"
    os.makedirs(ver_dir, exist_ok=True)
    
    if source == "github":
        base_url = f"https://github.com/{GITHUB_REPO}"
    else:
        base_url = f"https://gitee.com/{GITEE_REPO}"
        
    url_model = f"{base_url}/releases/download/{CURRENT_VER}/{REMOTE_MODEL}"
    url_vocab = f"{base_url}/releases/download/{CURRENT_VER}/{REMOTE_VOCAB}"
    
    print(f"\n{COLOR_INFO}正在从 {source.capitalize()} 下载...{RESET}\n")
    try:
        print(f"下载 {REMOTE_MODEL} -> {ver_dir}/axiom-llm.pth ...")
        urllib.request.urlretrieve(url_model, os.path.join(ver_dir, "axiom-llm.pth"))
        print(f"下载 {REMOTE_VOCAB} -> {ver_dir}/vocab.json ...")
        urllib.request.urlretrieve(url_vocab, os.path.join(ver_dir, "vocab.json"))
        print(f"\n{COLOR_OK}下载成功！已存入 {ver_dir}{RESET}")
    except Exception as e:
        print(f"\n{COLOR_WARN}下载失败: {e}{RESET}")
        print("提示: 请确保 Releases 里有对应版本和附件。")
    input(f"\n{COLOR_INFO}按回车返回菜单...{RESET}")
    sys.stdout.write("\033[?1049h\033[?25l")

def main():
    sys.stdout.write("\033[?1049h\033[?25l\033[H\033[2J")
    sys.stdout.flush()
    
    main_idx, main_btn = 0, 0
    wl_idx = 0
    
    try:
        while True:
            draw_menu(main_idx, main_btn)
            key = get_key()
            if key == '\x1b[A' and main_btn == 0: main_idx = (main_idx - 1) % 5
            elif key == '\x1b[B' and main_btn == 0: main_idx = (main_idx + 1) % 5
            elif key == '\x1b[D': main_btn = 0
            elif key == '\x1b[C': main_btn = 1
            elif key in ('\r', '\n'):
                if main_btn == 1: break 
                
                if main_idx == 0:
                    cur_ver = get_current_path()
                    if not cur_ver:
                        sys.stdout.write("\033[?1049l\033[?25h" + RESET)
                        print(f"\n{COLOR_WARN}错误: 找不到权重文件！{RESET}")
                        input(f"\n{COLOR_INFO}按回车返回...{RESET}")
                        sys.stdout.write("\033[?1049h\033[?25l")
                    else:
                        sys.stdout.write("\033[?1049l\033[?25h" + RESET)
                        sys.stdout.flush()
                        os.execvp("python", ["python", "chat.py", os.path.join(cur_ver, "axiom-llm.pth"), os.path.join(cur_ver, "vocab.json")])
                        
                elif main_idx == 1:
                    sys.stdout.write("\033[?1049l\033[?25h" + RESET)
                    sys.stdout.flush()
                    os.execvp("python", ["python", "train.py"])
                    
                elif main_idx == 2:
                    dl_idx = 0
                    while True:
                        draw_download_menu(dl_idx)
                        dl_key = get_key()
                        if dl_key == '\x1b[A': dl_idx = (dl_idx - 1) % 3
                        elif dl_key == '\x1b[B': dl_idx = (dl_idx + 1) % 3
                        elif dl_key in ('\r', '\n'):
                            if dl_idx == 0: do_download("github"); break
                            elif dl_idx == 1: do_download("gitee"); break
                            elif dl_idx == 2: break
                        elif dl_key == '\x03': raise KeyboardInterrupt
                        
                elif main_idx == 3:
                    vers = get_versions()
                    if wl_idx >= len(vers): wl_idx = max(0, len(vers) - 1)
                    while True:
                        draw_weight_list(wl_idx)
                        wl_key = get_key()
                        if wl_key == '\x1b[A' and vers:
                            wl_idx = (wl_idx - 1) % len(vers)
                        elif wl_key == '\x1b[B' and vers:
                            wl_idx = (wl_idx + 1) % len(vers)
                        elif wl_key in ('\r', '\n') and vers:
                            with open(".current_version", "w") as f:
                                f.write(vers[wl_idx])
                            break
                        elif wl_key in ('\x1b[D', '\x03'):
                            break
                            
                elif main_idx == 4: 
                    break
                    
    except KeyboardInterrupt: pass
    finally:
        sys.stdout.write("\033[?1049l\033[?25h" + RESET)
        sys.stdout.flush()

if __name__ == "__main__":
    main()
