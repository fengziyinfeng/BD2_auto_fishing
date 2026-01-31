import sys
import os
import cv2
import mss
import numpy as np
import pydirectinput
import time
import win32gui
import win32con
import ctypes

def resource_path(relative_path):
    try:
        # PyInstaller 创建临时文件夹 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II"

#设置游戏分辨率
def drag_resize_game_window_fixed_ratio(window_title, target_width=1920):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"❌ 未找到窗口: '{window_title}'")
        return False

    # 还原窗口，避免最大化或最小化
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.2)

    # 获取当前窗口位置
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    current_width = right - left

    # 判断是否需要调整
    dx = target_width - current_width
    if dx == 0:
        print(f"✅ 窗口宽度已是目标 {target_width}px，无需调整")
        return True

    # 如果需要调整，提示用户切换窗口
    print("当前需要调整游戏窗口大小")
    print("请将游戏窗口拖至屏幕左上角，并调整窗口调整到1920*1080以内")
    print("脚本会调整游戏窗口调整到1920*1080，为啥大了不行？我也想知道！！！")
    print("在脚本调整完分辨率后，请返回以指定感叹号检测阈值")
    print("按回车3秒内请切换到游戏窗口，3秒后脚本将会进行调整")
    input("按回车以继续...")
    time.sleep(3)
    
    # 获取当前窗口位置
    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    current_width = right - left
    
    # 窗口右下角起始位置
    start_x = right - 2
    start_y = bottom - 2

    # 模拟鼠标拖动右下角
    pydirectinput.moveTo(start_x, start_y)
    time.sleep(0.05)
    pydirectinput.mouseDown()
    time.sleep(0.05)
    pydirectinput.moveTo(start_x + dx, start_y, duration=0.2)
    time.sleep(0.05)
    pydirectinput.mouseUp()

    print(f"✅ 窗口 '{window_title}' 已调整宽度到 {target_width}px")
    return True

#运行设置游戏分辨率
drag_resize_game_window_fixed_ratio(GAME_TITLE, 1920)

# 获取窗口信息
def get_window_region(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"❌ [ERROR] 未找到窗口: '{window_title}'")
        return None

    x, y, right, bottom = win32gui.GetWindowRect(hwnd)
    return {'left': x, 'top': y, 'width': right - x, 'height': bottom - y}

# 加载资源
template = cv2.imread(resource_path('exclamation_mark.png'), cv2.IMREAD_GRAYSCALE)
if template is None:
    raise FileNotFoundError("❌ 找不到 exclamation_mark.png")

# 获取窗口区域
region = get_window_region(GAME_TITLE)
if region is None:
    exit(1)

# 完全保留原始区域定义
hook_pos = {
    'left': region['left'] + int(region['width'] * 0.47),
    'top': region['top'] + int(region['height'] * 0.28),
    'width': int(region['width'] * (0.53 - 0.47)),
    'height': int(region['height'] * (0.39 - 0.28))
}
roi_pos = {
    'left': region['left'] + int(region['width'] * 0.37),
    'top': region['top'] + int(region['height'] * 0.86),
    'width': int(region['width'] * (0.65 - 0.37)),
    'height': int(region['height'] * (0.89 - 0.86))
}

# 颜色阈值
lower_white = np.array([0, 0, 240])
upper_white = np.array([180, 50, 255])

lower_yellow = np.array([20, 100, 100])  # 黄色条的HSV范围
upper_yellow = np.array([40, 255, 255])

lower_green = np.array([40, 100, 100])  # 绿色条的HSV范围
upper_green = np.array([80, 255, 255])

lower_blue = np.array([100, 100, 100])  # 蓝色条的HSV范围
upper_blue = np.array([140, 255, 255])
fail_num = 0

def handle_timeout():
    print("🔄 异常恢复：回正并重置状态...")
    pydirectinput.keyDown('up')
    time.sleep(2.0)
    pydirectinput.keyUp('up')
    finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
    time.sleep(0.5)
    pydirectinput.press('space')
    time.sleep(0.3)
    pydirectinput.press('space')

def finish_fishing(cx, cy):
    pydirectinput.moveTo(cx, cy)
    time.sleep(0.2)
    pydirectinput.click()

def cast_rod():
    print("🎣 抛竿...")
    pydirectinput.keyDown('space')
    time.sleep(0.4)
    pydirectinput.keyUp('space')

def clear_backpack():
    print("🧹 清理背包...")
    pydirectinput.press('t')
    time.sleep(2)
    w, h = region['width'], region['height']
    x0, y0 = region['left'], region['top']
    pydirectinput.click(x0 + int(w * 0.87), y0 + int(h * 0.92))
    time.sleep(1)
    pydirectinput.click(x0 + int(w * 0.82), y0 + int(h * 0.92))
    time.sleep(1)
    pydirectinput.click(x0 + int(w * 0.92), y0 + int(h * 0.92))
    time.sleep(1)
    pydirectinput.click(x0 + int(w * 0.57), y0 + int(h * 0.61))
    time.sleep(1)
    pydirectinput.click(x0 + int(w * 0.10), y0 + int(h * 0.12))
    time.sleep(1)

def wait_for_bite(sct,threshold):
    global fail_num
    print("⏳ 等待上钩...")
    start_time = time.time()

    # 短暂延迟，避开抛竿动画（可调）
    time.sleep(0.5)

    while True:
        elapsed = time.time() - start_time
        if elapsed > 8:
            print("⏰ 检测上钩超时")
            fail_num += 1
            handle_timeout()
            return False

        # 检查是否已意外进入 QTE 阶段
        try:
            roi_img = np.array(sct.grab(roi_pos))
            bgr = cv2.cvtColor(roi_img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            yellow_mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
            pixel_count = cv2.countNonZero(yellow_mask) * 25
            if pixel_count > 8000:
                print("✅ 检测到 QTE 条（鱼可能已上钩），进入 QTE")
                return True
        except:
            pass

        # 检查感叹号（使用用户定义的阈值）
        try:
            hook_img = np.array(sct.grab(hook_pos))
            gray = cv2.cvtColor(hook_img, cv2.COLOR_BGRA2GRAY)
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            max_val = float(np.max(res))
            print(f"检测感叹号，匹配度={max_val:.3f}")
            if max_val >= threshold:  # 使用用户输入的阈值
                print(f"✅ 检测到感叹号，（匹配度={max_val:.3f}），鱼已上钩，进入 QTE")
                pydirectinput.press('space')
                return True
        except:
            pass

        time.sleep(0.05)


def play_qte(sct):
    print("🎮 进入 QTE...")
    no_bar_frames = 0
    start_time = time.time()
    qte_press_count = 0
    last_press_time = 0  # 防抖：避免连续按空格
    last_action_time = time.time() #记录上次按空格时间
    while time.time() - start_time < 20:
        try:
            roi = np.array(sct.grab(roi_pos))
            bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            # 黄色条
            mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            # 绿色条
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            # 蓝色条
            mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

            kernel = np.ones((7, 7), np.uint8)
            mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2)
            mask_green = cv2.dilate(mask_green, kernel, iterations=2)
            mask_blue = cv2.dilate(mask_blue, kernel, iterations=2)

            pixel_count_yellow = cv2.countNonZero(mask_yellow) * 25
            pixel_count_green = cv2.countNonZero(mask_green) * 25
            pixel_count_blue = cv2.countNonZero(mask_blue) * 25

            selected_mask = None
            action_duration = 0  # 按空格时间

            # qte检测
            #print("qte检测")
            if pixel_count_yellow > 8000:
                #print("检测到黄条")
                no_bar_frames = 0
                selected_mask = mask_yellow
                action_duration = 0.1
            elif pixel_count_green > 8000:
                #print("检测到绿条")
                no_bar_frames = 0
                selected_mask = mask_green
                action_duration = 0.2
            elif pixel_count_blue > 8000:
                #print("检测到蓝条")
                no_bar_frames = 0
                selected_mask = mask_blue
                action_duration = 0.1  
            else:
                no_bar_frames += 1
                if no_bar_frames > 120:
                    print("120帧未检测到qte条，qte结束")
                    break

            # 如果有有效的条形被检测到，继续检查光标
            if selected_mask is not None:
                # 光标检测
                mask_cursor = cv2.inRange(hsv, lower_white, upper_white)
                col_sums = np.sum(mask_cursor, axis=0)

                if np.max(col_sums) != 0:  # 有白色像素
                    cursor_x = np.argmax(col_sums)
                    #print("检测到光标")
                    # 防止 cursor_x 越界
                    if cursor_x >= selected_mask.shape[1]:
                        cursor_x = selected_mask.shape[1] - 1
                    if cursor_x < 0:
                        cursor_x = 0

                    # 打印光标位置
                    # print(f"🔳 光标位置: {cursor_x} (QTE 阶段)")

                    # 使用中间行判断（与原脚本一致）
                    check_y = selected_mask.shape[0] // 2
                    
                    # 确保坐标有效
                    if check_y < selected_mask.shape[0] and cursor_x < selected_mask.shape[1]:
                        if selected_mask[check_y, cursor_x]:
                            current_time = time.time()
                            # 防抖：至少间隔 0.1 秒才可再次按
                            if current_time - last_press_time > 0.1:
                                #print("触发攻击")
                                pydirectinput.keyDown('space')  # 按下空格
                                time.sleep(action_duration)  # 按住空格指定时间
                                pydirectinput.keyUp('space')  # 释放空格
                                last_press_time = current_time
                                last_action_time = current_time  # 更新上次按空格时间
                                qte_press_count += 1
                    # 三秒未按空格就双击空格(模拟光标被冻结）
                    if time.time() - last_action_time > 5:
                        print("⏳ 5秒未按空格，预测为光标被冻结")
                        for _ in range(2):
                            pydirectinput.press('space')
                            time.sleep(0.1)
                        last_action_time = time.time()  # 重置计时
                                
         
                
        except Exception as e:
            print(f"⚠️ QTE 异常: {e}")
            no_bar_frames += 10

        time.sleep(0.032)
    print(f"🎣 本轮 QTE 尝试触发了 {qte_press_count} 次")
        
def main():
    threshold_input = input("请输入感叹号匹配度阈值（默认值 0.85，直接按回车使用默认值）: ")
    threshold = float(threshold_input) if threshold_input else 0.85  # 默认为0.85
    print(f"感叹号检测阈值已设置为: {threshold}")
    print(f"如果在抛竿时直接进入qte阶段，并且持续抛竿，说明阈值过低")
    print("请3秒内手动切换至游戏窗口，脚本将会启动")
    time.sleep(3)
    global fail_num
    print("\n🚀 启动自动钓鱼\n")
    time.sleep(0.5)
    with mss.mss() as sct:
        cycle = 0
        while True:
            cycle += 1
            print("====================================================================")
            print(f"🔁 第 {cycle} 轮钓鱼开始")

            if fail_num >= 3:
                clear_backpack()
                fail_num = 0
                continue

            cast_rod()
            if wait_for_bite(sct,threshold):
                play_qte(sct)
            finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
            time.sleep(1.5)
            print(f"🔁 第 {cycle} 轮钓鱼结束")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户终止")
        input("按回车关闭窗口...")
    except Exception as e:
        print(f"\n💥 崩溃: {e}")
        input("按回车关闭窗口...")
