#!/usr/bin/env python3
"""
启动简单的MQTT代理用于测试
"""

import subprocess
import sys
import time

def install_mosquitto():
    """安装Mosquitto MQTT代理"""
    print("🔧 检查Mosquitto MQTT代理...")
    
    try:
        # 检查是否已安装
        result = subprocess.run(["mosquitto", "--help"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Mosquitto已安装")
            return True
    except FileNotFoundError:
        pass
    
    print("📦 需要安装Mosquitto...")
    
    # 尝试使用Homebrew安装
    try:
        print("🍺 使用Homebrew安装Mosquitto...")
        subprocess.run(["brew", "install", "mosquitto"], check=True)
        print("✅ Mosquitto安装成功")
        return True
    except subprocess.CalledProcessError:
        print("❌ Homebrew安装失败")
        return False
    except FileNotFoundError:
        print("❌ 未找到Homebrew")
        return False

def start_mosquitto():
    """启动Mosquitto代理"""
    print("🚀 启动Mosquitto MQTT代理...")
    
    try:
        # 启动Mosquitto在端口5001
        process = subprocess.Popen([
            "mosquitto", 
            "-p", "5001",
            "-v"  # 详细输出
        ])
        
        print("✅ Mosquitto已启动在端口5001")
        print("📋 进程ID:", process.pid)
        print("⏹️  按 Ctrl+C 停止")
        
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n⏹️  停止Mosquitto...")
            process.terminate()
            process.wait()
            print("✅ Mosquitto已停止")
            
    except FileNotFoundError:
        print("❌ 未找到Mosquitto")
        return False
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return False

def main():
    """主函数"""
    print("🌱 MQTT代理启动器")
    print("=" * 30)
    
    if install_mosquitto():
        start_mosquitto()
    else:
        print("❌ 无法安装或启动Mosquitto")
        print("💡 请手动安装Mosquitto:")
        print("   brew install mosquitto")

if __name__ == "__main__":
    main() 