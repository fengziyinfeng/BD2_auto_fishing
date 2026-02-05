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

# ================== 加载资源 ==================

#设置运行目录
def resource_path(relative_path):
    try:
        # PyInstaller 创建临时文件夹 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

#获取游戏DPI
ctypes.windll.user32.SetProcessDPIAware()

#定义游戏名称
GAME_TITLE = "BrownDust II"

#加载感叹号模板
EXCLAMATION_TEMPLATE = cv2.imread(
    resource_path('exclamation_mark.png'),
    cv2.IMREAD_GRAYSCALE
)

if EXCLAMATION_TEMPLATE is None:
    raise FileNotFoundError("❌ 找不到 exclamation_mark.png")

#加载清理背包按钮模板
button_templates = {
    "AllSell": resource_path("AllSell.png"),
    "All": resource_path("All.png"),
    "OK1": resource_path("OK1.png"),
    "OK2": resource_path("OK2.png"),
    "Back": resource_path("Back.png"),
    "shaonv": resource_path("shaonv.png"),
}

# ================== 获取窗口区域信息 ==================

# 获取游戏窗口位置信息
def get_window_region(window_title):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"❌ [ERROR] 未找到窗口: '{window_title}'")
        return None

    x, y, right, bottom = win32gui.GetWindowRect(hwnd)
    return {'left': x, 'top': y, 'width': right - x, 'height': bottom - y}

# 根据窗口位置信息获取截图
def get_window_screenshot(region):
    with mss.mss() as sct:
        return np.array(sct.grab(region))
    
# 获取窗口截图
region = get_window_region(GAME_TITLE)
if region is None:
    exit(1)

# ================== 基础设置 ==================

# 定义感叹号检测区域
hook_pos = {
    'left': region['left'] + int(region['width'] * 0.47),
    'top': region['top'] + int(region['height'] * 0.28),
    'width': int(region['width'] * (0.53 - 0.47)),
    'height': int(region['height'] * (0.39 - 0.28))
}
#定义QTE条和光标检测区域
roi_pos = {
    'left': region['left'] + int(region['width'] * 0.37),
    'top': region['top'] + int(region['height'] * 0.86),
    'width': int(region['width'] * (0.65 - 0.37)),
    'height': int(region['height'] * (0.89 - 0.86))
}

# qte颜色范围
lower_white = np.array([0, 0, 240])
upper_white = np.array([180, 50, 255])

lower_yellow = np.array([20, 100, 100])  # 黄色条的HSV范围
upper_yellow = np.array([40, 255, 255])

lower_green = np.array([40, 100, 100])  # 绿色条的HSV范围
upper_green = np.array([80, 255, 255])

lower_blue = np.array([100, 100, 100])  # 蓝色条的HSV范围
upper_blue = np.array([140, 255, 255])

fail_num = 0

#定义各个按钮所处区域
BUTTON_REGIONS = {
    "AllSell": (0.8, 0.8, 1, 1),
    "All":     (0.6, 0.8, 1, 1),
    "OK1":     (0.8, 0.8, 1, 1),
    "OK2":     (0.3, 0.3, 0.8,0.8),
    "Back":    (0,0, 0.3, 0.3),
    "shaonv":  (0,0, 0.3, 0.3),
}

#计算区域坐标
def calc_roi(region, ratio):
    l, t, r, b = ratio
    return {
        "left": region["left"] + int(region["width"] * l),
        "top": region["top"] + int(region["height"] * t),
        "width": int(region["width"] * (r - l)),
        "height": int(region["height"] * (b - t)),
    }

# ================== 钓鱼 ==============================

#抛竿
def cast_rod():
    print("🎣 抛竿...")
    pydirectinput.keyDown('space')
    time.sleep(0.38)
    pydirectinput.keyUp('space')

#感叹号匹配
def match_exclamation_multi_scale(gray, template):

    best_val = 0.0

    # 多个缩放尺度（从小到接近原始）
    scales = [0.2,0.3,0.45,0.55, 0.65, 0.75, 0.85, 1.0]

    for scale in scales:
        new_w = int(template.shape[1] * scale)
        new_h = int(template.shape[0] * scale)

        # 模板过小直接跳过
        if new_w < 6 or new_h < 6:
            continue

        # ROI 比模板小，无法匹配
        if gray.shape[1] < new_w or gray.shape[0] < new_h:
            continue

        resized = cv2.resize(
            template,
            (new_w, new_h),
            interpolation=cv2.INTER_AREA
        )

        res = cv2.matchTemplate(
            gray,
            resized,
            cv2.TM_CCOEFF_NORMED
        )

        val = float(np.max(res))
        if val > best_val:
            best_val = val
    print(f"检测感叹号匹配度：{best_val:.3f}")
    return best_val

#感叹号检测
def wait_for_bite(sct,threshold):
    global fail_num
    print("⏳ 等待上钩...")
    start_time = time.time()
    
    # 短暂延迟，避开抛竿动画
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
        except Exception as e:
            print("⚠️ QTE 条检测异常:", e)

        # 检查感叹号
        try:
            hook_img = np.array(sct.grab(hook_pos))

            if hook_img.size == 0:
                raise ValueError("hook_img 为空")

            gray = cv2.cvtColor(hook_img, cv2.COLOR_BGRA2GRAY)
            val = match_exclamation_multi_scale(gray, EXCLAMATION_TEMPLATE)

            if val >= threshold:
                print(f"✅ 检测到感叹号（匹配度={val:.3f}），鱼已上钩，进入 QTE")
                pydirectinput.press('space')
                return True

        except Exception as e:
            print("⚠️ 感叹号检测异常:", e)

        time.sleep(0.25)

#qte阶段
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
                if no_bar_frames > 30:
                    print("未检测到qte条，qte结束")
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
                                
                    # 3秒未按空格就双击空格(模拟光标被冻结）
                    if time.time() - last_action_time > 3:
                        print("⏳ 3秒未按空格，预测为光标被冻结")
                        for _ in range(3):
                            pydirectinput.press('space')
                            time.sleep(0.1)
                        last_action_time = time.time()  # 重置计时
                                
        except Exception as e:
            print(f"⚠️ QTE 异常: {e}")
            no_bar_frames += 10
        time.sleep(0.032)# 1帧的时间
   
#钓鱼结束点击
def finish_fishing(cx, cy):
    pydirectinput.moveTo(cx, cy)
    time.sleep(0.2)
    pydirectinput.click()

#超时恢复
def handle_timeout():
    print("🔄 异常恢复：回正并重置状态...")
    pydirectinput.keyDown('down')
    time.sleep(0.75)
    pydirectinput.keyUp('down')
    finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
    time.sleep(0.5)
    pydirectinput.press('space')
    time.sleep(0.3)
    pydirectinput.press('space')
    
#===========================背包清理=============================

#查找按钮位置
def find_button_location(button_name, region):
    template_raw = cv2.imread(button_templates[button_name], cv2.IMREAD_GRAYSCALE)
    if template_raw is None:
        print(f"❌ 模板缺失: {button_name}")
        return None

    scale = region["width"] / 1920
    tw = int(template_raw.shape[1] * scale)
    th = int(template_raw.shape[0] * scale)
    if tw < 5 or th < 5:
        return None

    template = cv2.resize(template_raw, (tw, th), cv2.INTER_AREA)
    roi = calc_roi(region, BUTTON_REGIONS[button_name])
    screenshot = get_window_screenshot(roi)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)

    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    print(f"🔎 {button_name} 匹配度: {max_val:.3f}")

    if max_val < 0.5:
        return None

    x = roi["left"] + max_loc[0]
    y = roi["top"] + max_loc[1]
    return (x, y), (tw, th)

#点击
def click_button(location):
    (x, y), (w, h) = location
    cx = x + w // 2
    cy = y + h // 2
    pydirectinput.moveTo(cx, cy)
    time.sleep(0.1)
    pydirectinput.click()
    print(f"🖱️ 点击坐标: ({cx}, {cy})  [按钮区域: x={x}, y={y}, w={w}, h={h}]")
    time.sleep(0.5)

#背包清理
def clean_backpack():
    print("🧹 清理背包")
    print("📂 尝试打开背包，每十秒自动重按下 T ")
    while True:
        pydirectinput.press("t")

        start_time = time.time()
        entered = False

        while time.time() - start_time < 10:
            loc = find_button_location("shaonv", region)
            if loc:
                print("✅ 已成功进入背包界面")
                entered = True
                break
            time.sleep(1)

        if entered:
            break  # 成功进入背包，跳出外层 while

    
    for name in ["AllSell", "All", "OK1", "OK2", "Back"]:
        loc = find_button_location(name, region)
        if loc:
            click_button(loc)
            time.sleep(1)

#############################################################################################
def main():
    print("！！！注意！！！！！！")
    print("请先设置窗口化，固定比例16：9")
    print("建议设置分辨率FHD。HD未测试，不确定能不能行")
    
    threshold_input = input("请输入感叹号匹配度阈值（默认值 0.85，直接按回车使用默认值）: ")
    threshold = float(threshold_input) if threshold_input else 0.85  # 默认为0.85
    
    print(f"感叹号检测阈值已设置为: {threshold}")
    print("如果在抛竿时直接进入qte阶段，并且持续抛竿，说明阈值过低")
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
                clean_backpack()
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
