import time
import requests
import subprocess
import socket
import paramiko # 引入SSH库
from datetime import datetime
import io
import os

# ================= 配置区域 =================
# 1. 校园网登录配置
LOGIN_BASE_URL = "http://192.168.200.2:801/eportal/"
ACCOUNT = ",1,#####@unicom"
PASSWORD = "在这里填入你的校园网密码"  # 【请修改】填回你的校园网密码
TEST_IP = "223.5.5.5"

# 2. 远程服务器配置 (接收IP的服务器)
REMOTE_HOST = ""
REMOTE_PORT = ""
REMOTE_USER = ""
REMOTE_PASS = ""  # 【请修改】填回你的服务器密码
REMOTE_PATH = "/home/fork/_ip.txt" 
# ===========================================

def log(content):
    """
    日志输出功能：
    1. 打印到控制台 (调试用)
    2. 追加写入到 log.txt 文件 (后台运行时查看用)
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"[{timestamp}] {content}"
    
    # 打印到屏幕
    print(message)
    
    # 写入文件 (使用 utf-8 编码防止中文乱码)
    try:
        # 获取脚本所在目录，确保 log.txt 生成在正确的位置
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, "log.txt")
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        # 如果写文件失败（比如权限不够），只打印错误但不卡死程序
        print(f"写入日志文件失败: {e}")

def get_local_ip():
    """获取本机当前的内网 IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        log(f"获取本机 IP 失败: {e}")
        return ""

def check_internet():
    """检查网络连通性"""
    try:
        subprocess.check_call(
            ['ping', '-n', '1', '-w', '2000', TEST_IP], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL,
            creationflags=0x08000000 
        )
        return True
    except Exception:
        return False

def login():
    """执行校园网登录"""
    current_ip = get_local_ip()
    if not current_ip:
        log("错误：无法获取本机 IP，放弃本次登录。")
        return False

    log(f"准备登录，当前 IP: {current_ip}")
    
    # 构造登录参数
    params = {
        'c': 'Portal',
        'a': 'login',
        'callback': 'dr1003',
        'login_method': '1',
        'user_account': ACCOUNT,
        'user_password': PASSWORD,
        'wlan_user_ip': current_ip,
        'wlan_user_ipv6': '',
        'wlan_user_mac': '000000000000',
        'wlan_ac_ip': '',
        'wlan_ac_name': '',
        'jsVersion': '3.3.3',
        'v': '4354'
    }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(LOGIN_BASE_URL, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            log("登录请求已发送。")
            return True
        else:
            log(f"登录失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        log(f"登录出错: {e}")
        return False

def upload_ip_via_sftp():
    """通过 SFTP 将 IP 上传到远程服务器"""
    ip = get_local_ip()
    if not ip:
        return False
        
    log(f"正在通过 SFTP 上报 IP: {ip} 到 {REMOTE_HOST}...")
    
    try:
        # 1. 创建 SSH 传输通道
        transport = paramiko.Transport((REMOTE_HOST, REMOTE_PORT))
        transport.connect(username=REMOTE_USER, password=REMOTE_PASS)
        
        # 2. 创建 SFTP 客户端
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # 3. 准备文件内容
        file_content = f"Time: {datetime.now()}\nUser: ChenZhe\nIP: {ip}\n"
        file_obj = io.BytesIO(file_content.encode('utf-8'))
        
        # 4. 上传文件
        sftp.putfo(file_obj, REMOTE_PATH)
        
        # 5. 关闭连接
        sftp.close()
        transport.close()
        
        log(f"IP 文件已成功上传至: {REMOTE_PATH}")
        return True
        
    except Exception as e:
        log(f"SFTP 上传失败: {e}")
        return False

def main():
    log("=== 校园网自动保活 & IP上传脚本 ===")
    
    # 标记位
    has_reported = False 
    
    while True:
        # 1. 检查网络
        is_connected = check_internet()
        
        if not is_connected:
            log("网络断开，正在重连...")
            login()
            time.sleep(5)
            is_connected = check_internet()
            if is_connected:
                log("重连成功！")
                has_reported = False # 重连后需要重新上传
        else:
            log("网络正常。")

        # 2. 上传 IP (如果网络通且未上传过)
        if is_connected and not has_reported:
            if upload_ip_via_sftp():
                has_reported = True
            else:
                has_reported = False 

        # 3. 休眠 30 分钟
        time.sleep(1800)

if __name__ == "__main__":
    main()