import sys
import os
import cv2
import mss
import numpy as np
import pydirectinput
import time
import win32gui
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

def get_window_region(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"❌ [ERROR] 未找到窗口: '{window_title}'")
        return None
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    x, y, right, bottom = win32gui.GetWindowRect(hwnd)
    return {'left': x, 'top': y, 'width': right - x, 'height': bottom - y}

# 加载资源
template = cv2.imread(resource_path('exclamation_mark.png'), cv2.IMREAD_GRAYSCALE)
if template is None:
    raise FileNotFoundError("❌ 找不到 exclamation_mark.png")

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

# 颜色阈值（与原始一致）
lower_white = np.array([0, 0, 240])
upper_white = np.array([180, 50, 255])
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([40, 255, 255])

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
    time.sleep(0.38)
    pydirectinput.keyUp('space')

def clear_backpack():
    print("🧹 清理背包...")
    pydirectinput.press('t')
    time.sleep(1)
    w, h = region['width'], region['height']
    x0, y0 = region['left'], region['top']
    pydirectinput.click(x0 + int(w * 0.87), y0 + int(h * 0.92))
    time.sleep(0.5)
    pydirectinput.click(x0 + int(w * 0.82), y0 + int(h * 0.92))
    time.sleep(0.5)
    pydirectinput.click(x0 + int(w * 0.92), y0 + int(h * 0.92))
    time.sleep(0.5)
    pydirectinput.click(x0 + int(w * 0.57), y0 + int(h * 0.61))
    time.sleep(0.5)
    pydirectinput.click(x0 + int(w * 0.10), y0 + int(h * 0.12))
    time.sleep(1)

def wait_for_bite(sct):
    global fail_num
    print("⏳ 等待上钩...")
    start_time = time.time()
    
    # 短暂延迟，避开抛竿动画（可调）
    time.sleep(0.5)

    while True:
        elapsed = time.time() - start_time
        if elapsed > 16:
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

        # 检查感叹号（阈值 0.8）
        try:
            hook_img = np.array(sct.grab(hook_pos))
            gray = cv2.cvtColor(hook_img, cv2.COLOR_BGRA2GRAY)
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            max_val = float(np.max(res))
            print(f"检测感叹号，匹配度={max_val:.3f}")
            if max_val >= 0.8:
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

    while time.time() - start_time < 15:
        try:
            roi = np.array(sct.grab(roi_pos))
            bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

            # 黄条检测
            mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
            kernel = np.ones((7, 7), np.uint8)
            mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2)
            pixel_count = cv2.countNonZero(mask_yellow) * 25

            if pixel_count > 8000:
                no_bar_frames = 0

                # 光标检测
                mask_cursor = cv2.inRange(hsv, lower_white, upper_white)
                col_sums = np.sum(mask_cursor, axis=0)
                
                if np.max(col_sums) != 0:  # 有白色像素
                    cursor_x = np.argmax(col_sums)
                    
                    # 防止 cursor_x 越界
                    if cursor_x >= mask_yellow.shape[1]:
                        cursor_x = mask_yellow.shape[1] - 1
                    if cursor_x < 0:
                        cursor_x = 0

                    # 使用中间行判断（与原脚本一致）
                    check_y = mask_yellow.shape[0] // 2
                    
                    # 确保坐标有效
                    if check_y < mask_yellow.shape[0] and cursor_x < mask_yellow.shape[1]:
                        if mask_yellow[check_y, cursor_x]:
                            current_time = time.time()
                            # 防抖：至少间隔 0.1 秒才可再次按
                            if current_time - last_press_time > 0.1:
                                pydirectinput.press('space')
                                last_press_time = current_time
                                qte_press_count += 1

            else:
                no_bar_frames += 1
                if no_bar_frames > 120:
                    print("🎣 QTE 结束")
                    break

        except Exception as e:
            print(f"⚠️ QTE 异常: {e}")
            no_bar_frames += 10

        time.sleep(0.032)
    print(f"🎣 本轮 QTE 尝试触发了 {qte_press_count} 次")
        
def main():
    global fail_num
    print("\n🚀 启动自动钓鱼\n")
    time.sleep(2)

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
            if wait_for_bite(sct):
                play_qte(sct)
            finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
            time.sleep(1.5)
            print(f"🔁 第 {cycle} 轮钓鱼结束")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 用户终止")
    except Exception as e:
        print(f"\n💥 崩溃: {e}")
