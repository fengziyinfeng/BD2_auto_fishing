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
    return os.path.join(base_path,relative_path)

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

#加载UI模板
UI_TEMPLATES = {
    "AllSell": resource_path("TEMPLATES/AllSell.png"),
    "All": resource_path("TEMPLATES/All.png"),
    "OK1": resource_path("TEMPLATES/OK1.png"),
    "OK2": resource_path("TEMPLATES/OK2.png"),
    "Back": resource_path("TEMPLATES/Back.png"),
    "shaonv": resource_path("TEMPLATES/shaonv.png"),
    "change": resource_path("TEMPLATES/change.png"),
    "map1": resource_path("TEMPLATES/map1.png"),
    "map2": resource_path("TEMPLATES/map2.png"),
    "map3": resource_path("TEMPLATES/map3.png"),
    "map4": resource_path("TEMPLATES/map4.png"),
    "map5": resource_path("TEMPLATES/map5.png"),
    "Go": resource_path("TEMPLATES/Go.png"),
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
    
#获取游戏窗口中心坐标
def get_window_center():
    if region:
        # 计算窗口的中心坐标
        center_x = region['left'] + region['width'] // 2
        center_y = region['top'] + region['height'] // 2
        return {
        "name": "window_center",
        "x": center_x,
        "y": center_y,
        "w": center_x,
        "h": center_y,
        "score": 1
    }
    else:
        return None
    
#设置窗口中心
region_center = get_window_center()
if region_center is None:
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
    "change":  (0,0, 0.3, 0.3),
    "map1":  (0,0, 1, 1),
    "map2":  (0,0, 1, 1),
    "map3":  (0,0, 1, 1),
    "map4":  (0,0, 1, 1),
    "map5":  (0,0, 1, 1),
    "Go":  (0.75, 0.5, 1, 1),
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
#===================通用方法=========================
#查找UI位置
def match_UI(UI_name, region, threshold=0.5):
    if UI_name not in UI_TEMPLATES:
        print(f"❌ 模板文件未定义: {UI_name}")
        return None
    
    if UI_name not in BUTTON_REGIONS:
        print(f"❌ 查找区域未定义: {UI_name}")
        return None
    
    template_raw = cv2.imread(
        UI_TEMPLATES[UI_name],
        cv2.IMREAD_GRAYSCALE
    )
    
    if template_raw is None:
        print(f"❌ 模板缺失: {UI_name}")
        return None

    scale = region["width"] / 1920
    tw = int(template_raw.shape[1] * scale)
    th = int(template_raw.shape[0] * scale)

    if tw < 5 or th < 5:
        print(f"分辨率过低，导致缩放后的模板一边长小于5像素")
        return None
    template = cv2.resize(template_raw, (tw, th), cv2.INTER_AREA)
    roi = calc_roi(region, BUTTON_REGIONS[UI_name])
    screenshot = get_window_screenshot(roi)
    gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)

    res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    print(f"🔎 {UI_name} 匹配度: {max_val:.3f}")

    x = roi["left"] + max_loc[0]
    y = roi["top"] + max_loc[1]
    
    if max_val < threshold:
        max_val = 0

    return {
        "name": UI_name,
        "x": x,
        "y": y,
        "w": tw,
        "h": th,
        "score": max_val
    }

#计算中心点
def center_of(box):
    cx = box["x"] + box["w"] // 2
    cy = box["y"] + box["h"] // 2
    print("当前元素中心为 ({cx}, {cy})")
    return cx, cy

#点击
def click_UI(cx, cy):
    pydirectinput.moveTo(cx, cy)
    time.sleep(0.25)
    pydirectinput.click()
    print(f"🖱 点击 ({cx}, {cy}) ")

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
    print("⏳ 等待上钩...")
    start_time = time.time()
    global fail_num
    
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

#背包清理
def clean_backpack():
    time.sleep(1)
    print("🧹 清理背包")
    print("📂 尝试打开背包：每 5 秒按一次 T，最多 3 次")

    for attempt in range(1, 4):
        print(f"🔁 第 {attempt} 次尝试打开背包")
        pydirectinput.press("t")

        start = time.time()
        while time.time() - start < 5:
            if match_UI("shaonv", region)["score"] != 0:
                print("✅ 已成功进入背包界面")
                break
            time.sleep(0.5)
        else:
            continue

        for name in ["AllSell", "All", "OK1", "OK2", "Back"]:
            box = match_UI(name, region)
            cx, cy = center_of(box)
            if box["score"] != 0:
                print(f"正在处理{name}，匹配度：{box['score']:.3f}")
                click_UI(cx, cy)
                time.sleep(1)

        print("🔄 背包清理完成")
        return

    print("❌ 多次尝试仍未进入背包，跳过本次清理")

#===========================地图切换=============================
#点击更换按钮
def click_change():
    # 检查 change 按钮并点击
    def click_if_found(button_name):
        region = get_window_region(GAME_TITLE)
        box = match_UI(button_name, region)
        if box["score"] != 0:
            cx, cy = center_of(box)
            click_UI(cx, cy)  # 点击按钮
            print(f"✅ 按钮 '{button_name}' 被点击")
            return True
        return False

    # 初次检测并点击 'change' 按钮
    while True:
        if click_if_found("change"):
            print("⏳ 等待10秒")
            time.sleep(10)  # 等待10秒以确保不是在切换白天黑夜
            break
        else:
            time.sleep(0.5)
    
    # 第二次检测并点击
    if click_if_found("change"):
        print("⏳ 等待5秒")
        time.sleep(5)  # 等待5秒

    # 第三次检测，如果按钮依然存在，认为点击失败
    if match_UI("change", get_window_region(GAME_TITLE))["score"] != 0:
        print("❌ 仍检测到 'change' 按钮，切换失败")
        return False
    else:
        print("✅ 没有检测到 'change' 按钮，已成功切换")
        return True

#移动地图
def drag_map_to_right():

    # 从 region_center 中获取中心坐标
    center_x = region_center['x']
    center_y = region_center['y']
    width = region['width']  # 窗口宽度
    drag_to_x = center_x + int(0.4 * width)  # 目标位置是窗口中心向右40%

    # 移动到窗口中心并按下左键
    pydirectinput.moveTo(center_x, center_y)
    time.sleep(0.5)
    pydirectinput.mouseDown()
    time.sleep(0.5)

    # 向右拖动40%的窗口宽度
    pydirectinput.moveTo(drag_to_x, center_y)
    pydirectinput.moveTo(drag_to_x, center_y, duration=0.5)  # 0.5秒拖动到目标位置
    time.sleep(0.5)

    # 松开左键
    pydirectinput.mouseUp()
    time.sleep(1)
    print("拖动地图")

#对地图按钮进行匹配，返回匹配值最低的一个
#所在地图图标会被放大，导致匹配度低
def get_lowest_match_map(region):
    min_match = float("inf")
    lowest_map = None
    
    for map_name in ["map1", "map2", "map3","map4","map5"]:
        box = match_UI(map_name, region)
        name, match_val = box["name"],box["score"]
        if match_val < min_match:
            min_match = match_val
            lowest_map = name
    
    print(f"最低匹配度的图标是: {lowest_map}, 匹配度: {min_match:.3f}")
    print(f"判定当前所在地图为{lowest_map}")
    return lowest_map, min_match

#切换地图操作
def change_map(map_index):
    map_name = f"map{map_index}"
    time.sleep(1)
    next_map = "map1"

    #点击更换按钮
    if not click_change():
        return

    #移动地图
    drag_map_to_right()
    
    region = get_window_region(GAME_TITLE)
    lowest_map, min_match = get_lowest_match_map(region)
    
    #匹配度最低的判定为当前所在地图
    if lowest_map == "map1":
        #当前所在地图为1就去2
        print("切换至其他地图")
        for  name in ["map2", "Go", "OK2"]:
            region = get_window_region(GAME_TITLE)
            box = match_UI(name, region)
            cx, cy = center_of(box)
            if box["score"] != 0:
                click_UI(cx, cy)
                time.sleep(1)
        print("⏳ 等待切换地图15秒")
        time.sleep(15)
        #切换至图1
        print("切换至预设地图")
        if not click_change():
            return
        for  name in [map_name, "Go", "OK2"]:
            region = get_window_region(GAME_TITLE)
            box = match_UI(name, region)
            cx, cy = center_of(box)
            if box["score"] != 0:
                click_UI(cx, cy)
                time.sleep(1)
        print("⏳ 等待切换地图15秒")
        time.sleep(15)
    else:
        #当前所在地图不是1就去1
        print("切换至其他地图")
        for  name in ["map1", "Go", "OK2"]:
            region = get_window_region(GAME_TITLE)
            box = match_UI(name, region)
            cx, cy = center_of(box)
            if box["score"] != 0:
                click_UI(cx, cy)
                time.sleep(1)
        print("⏳ 等待切换地图15秒")
        time.sleep(15)
        #切换至想去的地图
        if not click_change():
            return
        print("切换至预设地图")
        for  name in [map_name, "Go", "OK2"]:
            region = get_window_region(GAME_TITLE)
            box = match_UI(name, region)
            cx, cy = center_of(box)
            if box["score"] != 0:
                click_UI(cx, cy)
                time.sleep(1)
        print("⏳ 等待切换地图15秒")
        time.sleep(15)
     
#############################################################################################
def main():
    print("！！！注意！！！！！！")
    print("请先设置窗口化，固定比例16：9")
    print("建议设置分辨率FHD。HD未测试，不确定能不能行")
    
    threshold_input = input("请输入感叹号匹配度阈值（默认值 0.85，直接按回车使用默认值）: ")
    try:
        threshold = float(threshold_input) if threshold_input else 0.85
    except ValueError:
        print("⚠️ 输入非法，已自动使用默认阈值 0.85")
        threshold = 0.85
    print(f"感叹号检测阈值已设置为: {threshold}")
    print("如果在抛竿后直接进入qte阶段，并且持续抛竿，说明阈值过低")
    
    map_input = input("请输入每5小时30分钟自动切换的地图序号（默认值 1，直接按回车使用默认值）: ")
    print("如果开始就在图1，则会切换到图2，紧接着切换回来")
    print("地图序号：1.烟波湖 2.浅岸 3.寒霜海峡 4.深渊巨口 5.亚特兰蒂斯")
    try:
        map_index = int(map_input) if map_input else 1
    except ValueError:
        print("⚠️ 输入非法，已自动使用默认地图 1")
        map_index = 1
    if map_index > 5:
        print("⚠️ 输入值未兼容，已自动使用默认地图 1")
        map_index = 1
    print(f"🗺 当前选择地图: {map_index}")
    
    print("请3秒内手动切换至游戏窗口，脚本将会启动")
    start_time = time.time()
    time.sleep(3)
#########################
#测试
    #change_map(map_index)
    #clean_backpack()
##########################
    global fail_num
    
    print("\n🚀 启动自动钓鱼\n")
    time.sleep(0.5)

    with mss.mss() as sct:
        cycle = 0
        while True:
            cycle += 1
            print("====================================================================")
            print(f"🔁 第 {cycle} 轮钓鱼开始")

            #累积运行5小时30分钟（19800秒）会切换地图
            elapsed_time = time.time() - start_time
            if elapsed_time >= 19800:
                change_map(map_index)
                start_time = time.time()
                
            #累计三次识别感叹号失败会清理背包
            if fail_num >= 3:
                clean_backpack()
                fail_num = 0
                continue
            
            #钓鱼操作
            cast_rod()
            if wait_for_bite(sct,threshold):
                fail_num = 0
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
