from PySide6 import QtWidgets
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFileDialog, QMessageBox, QProgressBar
import requests
import os
import configparser  # 导入 configparser 模块
import base64
import json

# 创建配置解析器
config = configparser.ConfigParser()
config_file = 'config.ini'  # 配置文件名

# 如果配置文件存在，读取保存的文件夹路径
if os.path.exists(config_file):
    config.read(config_file)
else:
    # 如果配置文件不存在，则初始化
    config['settings'] = {
        'mod_folder': ''
    }

# 创建窗口
app = QtWidgets.QApplication([])
window = QtWidgets.QWidget()
window.setWindowTitle("安装程序")
window.resize(500, 300)

# 标签文字
label_welcome = QtWidgets.QLabel("欢迎使用山海服务器mod安装程序！", window)
label_welcome.move(20, 20)

label_choose = QtWidgets.QLabel("请选择您的mods文件夹", window)
label_choose.move(20, 60)

# 设置字体
font_sizes = {
    'welcome': 20,
    'choose': 16,
    'choose_path': 14,
    'install_button': 16
}

label_welcome.setFont(QFont("Arial", font_sizes['welcome']))
label_choose.setFont(QFont("Arial", font_sizes['choose']))

# 设置按钮
button_install = QtWidgets.QPushButton("安装", window)
button_install.move(270, 240)
button_install.resize(100, 30)
button_install.setFont(QFont("Arial", font_sizes['install_button']))

# 设置文件选择器路径显示框
label_choose_path = QtWidgets.QLabel(config['settings']['mod_folder'], window)  # 使用配置文件中的路径
label_choose_path.move(20, 100)
label_choose_path.resize(460, 50)
label_choose_path.setWordWrap(True)  # 开启自动换行
label_choose_path.setFont(QFont("Arial", font_sizes['choose_path']))

# 添加进度条
progress_bar = QProgressBar(window)
progress_bar.setGeometry(20, 160, 460, 30)
progress_bar.setValue(0)  # 初始值为0
progress_bar.setVisible(False)  # 初始隐藏

# 文件选择器
def choose_file():
    """选择文件夹并验证是否包含mod文件夹"""
    try:
        file_path = QFileDialog.getExistingDirectory(window, "选择文件夹")
        if file_path:
            if 'mod' in file_path:
                label_choose.setText("您选择的文件夹为：")
                label_choose_path.setText(file_path)

                # 保存选择的文件夹路径到配置文件
                config['settings']['mod_folder'] = file_path
                with open(config_file, 'w') as configfile:
                    config.write(configfile)
            else:
                QMessageBox.warning(window, "警告", "文件夹中没有找到mod文件夹，请重新选择！")
        else:
            label_choose.setText("未选择文件")
    except Exception as e:
        QMessageBox.critical(window, "错误", f"选择文件夹时发生错误: {e}")

# 绑定选择按钮的点击事件
button_choose = QtWidgets.QPushButton("选择", window)
button_choose.move(270, 60)
button_choose.resize(100, 30)
button_choose.clicked.connect(choose_file)

# 安装mod
GITHUB_REPO_OWNER = 'chenxingpengs'
GITHUB_REPO_NAME = 'shanhai-server'

def get_mod_list():
    """从GitHub获取mod列表"""
    url = f'https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/contents/mod_list.json'
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        mod_data = response.json()

        # 解码 content 字段
        if 'content' in mod_data:
            json_content = base64.b64decode(mod_data['content']).decode('utf-8')
            print("解码后的内容:", json_content)  # 打印解码后的内容
            
            mod_list = json.loads(json_content)  # 尝试解析 JSON
            
            if 'mods' in mod_list:  # 验证是否包含 mods 字段
                return mod_list['mods']  # 返回 mod 列表
            else:
                QMessageBox.warning(window, "警告", "获取的 JSON 数据格式不正确。")
                return []  # 返回空列表
        else:
            QMessageBox.warning(window, "警告", "没有找到 content 字段。")
            return []
    except requests.RequestException as e:
        QMessageBox.critical(window, "错误", f"无法获取 mod 列表: {e}")
        return []
    except json.JSONDecodeError as e:  # 捕获 JSON 解码错误
        QMessageBox.critical(window, "错误", f"解析mod列表时发生错误: {e}")
        return []
    except Exception as e:
        QMessageBox.critical(window, "错误", f"发生其他错误: {e}")
        return []


# 下载文件的函数
def download_file(url, folder_path):
    """从指定的 URL 下载文件到指定的文件夹"""
    local_filename = os.path.join(folder_path, url.split("/")[-1])  # 获取文件的名称
    with requests.get(url, stream=True) as r:
        r.raise_for_status()  # 如果请求失败，抛出异常
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):  # 分块写入文件
                f.write(chunk)
    return local_filename

# 安装mod的函数
def install_mod():
    """安装获取的mod并提供反馈信息"""
    folder_path = label_choose_path.text()  # 获取选择的文件夹路径
    if not os.path.exists(folder_path):
        QMessageBox.warning(window, "错误", "请选择一个合法的 mods 文件夹!")
        return

    try:
        mods = get_mod_list()
        if not mods:
            QMessageBox.critical(window, "错误", "未找到任何 mod.")
            return

        # 显示进度条并准备开始安装
        progress_bar.setVisible(True)
        progress_bar.setValue(0)  # 重置进度条
        total_mods = len(mods)

        installed_mods = []
        to_download_mods = []

        for mod in mods:
            # 确保 mod 数据符合预期格式
            if 'name' not in mod or 'download_url' not in mod:
                continue  # 跳过无效条目

            name = mod['name']
            download_url = mod['download_url']
            local_filename = os.path.join(folder_path, name)  # 本地文件路径
            
            if os.path.exists(local_filename):
                installed_mods.append(name)  # 添加至已安装的列表
            else:
                to_download_mods.append(name)  # 添加至需下载的列表
                print(f"Downloading {name} from {download_url}")
                # 下载文件
                download_file(download_url, folder_path)
                installed_mods.append(name)  # 下载后确认安装

            # 更新进度条
            progress_percentage = (len(installed_mods) + len(to_download_mods)) / total_mods * 100
            progress_bar.setValue(progress_percentage)

        # 根据已安装和需下载的MOD发出反馈
        installed_msg = ', '.join(installed_mods) if installed_mods else '无'
        download_msg = ', '.join(to_download_mods) if to_download_mods else '无'

        if installed_msg == '无' and download_msg == '无':
            QMessageBox.information(window, "结果", "未找到任何 MOD。")
        else:
            QMessageBox.information(window, "安装结果", f"已安装: {installed_msg}。\n需下载: {download_msg}。")

        progress_bar.setVisible(False)  # 隐藏进度条

    except Exception as e:
        QMessageBox.critical(window, "错误", f"安装mod时发生错误: {e}")
        progress_bar.setVisible(False)  # 隐藏进度条



# 绑定安装按钮的点击事件
button_install.clicked.connect(install_mod)

window.show()
app.exec()