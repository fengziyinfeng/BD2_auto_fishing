# 棕色尘埃2的python钓鱼脚本

## 介绍

基于图像识别进行QTE操作，只点击黄色区域，简单的QTE操作没问题，例如QTE条上有一些遮挡物，把黄色区域覆盖了，就容易失败

## 使用步骤

+ 测试环境：
+ Python 3.12.4
+ Pypi 24.0

### 1. 创建虚拟环境

打开空文件夹，并在空文件夹打开`powershell`，输入下面命令

```sh
# py -版本 -m venv 环境名字
py -3.12 -m venv auto_fishing
```
### 2. 进入虚拟环境

继续输入下面命令进入虚拟环境

```sh
# .\环境名字\Scripts\activate
.\auto_fishing\Scripts\activate
```

### 3. 安装必要的依赖

```sh
pip install -r requirements.txt
```

### 4. 运行脚本

运行脚本后，点击一下游戏里，注意游戏界面要全部展示出来，无其他窗口遮挡

```sh
python main.py
```
