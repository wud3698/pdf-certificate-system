#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LibreOffice 守护进程管理器
避免每次转换都重新启动 LibreOffice，提高证书生成性能
"""

import os
import time
import subprocess
import threading
import socket
import tempfile
import atexit
from pathlib import Path


class LibreOfficeDaemon:
    def __init__(self):
        self.process = None
        self.port = None
        self.is_running = False
        self.lock = threading.Lock()
        self.start_time = None
        self.conversion_count = 0
        
        # 注册退出时清理
        atexit.register(self.stop)
    
    def _find_free_port(self):
        """找到一个可用的端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def start(self):
        """启动 LibreOffice 守护进程"""
        with self.lock:
            if self.is_running:
                print("📟 LibreOffice 守护进程已在运行")
                return True
            
            try:
                self.port = self._find_free_port()
                
                # 创建用户配置目录
                user_dir = os.path.expanduser('~/.config/libreoffice_daemon')
                os.makedirs(user_dir, exist_ok=True)
                
                # 启动 LibreOffice 守护进程
                cmd = [
                    'soffice',
                    '--headless',
                    '--invisible',
                    '--nodefault',
                    '--nolockcheck',
                    '--nologo',
                    '--norestore',
                    '--accept=socket,host=127.0.0.1,port={},urp;StarOffice.ServiceManager'.format(self.port),
                    f'--user-directory={user_dir}'
                ]
                
                print(f"🚀 启动 LibreOffice 守护进程，端口: {self.port}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['LC_ALL'] = 'C.UTF-8'
                env['LANG'] = 'C.UTF-8'
                env['SAL_USE_VCLPLUGIN'] = 'svp'
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                # 等待守护进程启动
                max_wait = 15  # 最多等待15秒
                for i in range(max_wait):
                    if self._test_connection():
                        self.is_running = True
                        self.start_time = time.time()
                        self.conversion_count = 0
                        print(f"✅ LibreOffice 守护进程启动成功 (耗时 {i+1} 秒)")
                        return True
                    time.sleep(1)
                
                # 启动失败，清理进程
                if self.process:
                    self.process.terminate()
                    self.process = None
                
                print("❌ LibreOffice 守护进程启动失败")
                return False
                
            except Exception as e:
                print(f"❌ 启动 LibreOffice 守护进程时出错: {e}")
                self.is_running = False
                return False
    
    def _test_connection(self):
        """测试与守护进程的连接"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', self.port))
                return result == 0
        except:
            return False
    
    def convert_to_pdf(self, input_file, output_dir=None):
        """使用守护进程转换文档为PDF"""
        if not self.is_running:
            print("⚠️ 守护进程未运行，尝试启动...")
            if not self.start():
                return self._fallback_convert(input_file, output_dir)
        
        try:
            input_path = Path(input_file).resolve()
            if output_dir is None:
                output_dir = input_path.parent
            else:
                output_dir = Path(output_dir).resolve()
            
            # 构建转换命令
            cmd = [
                'soffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(output_dir),
                str(input_path)
            ]
            
            print(f"🔄 使用守护进程转换: {input_path.name}")
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(output_dir)
            )
            
            if result.returncode == 0:
                self.conversion_count += 1
                pdf_file = output_dir / (input_path.stem + '.pdf')
                if pdf_file.exists():
                    print(f"✅ 转换成功: {pdf_file.name} (第 {self.conversion_count} 次转换)")
                    return True, str(pdf_file)
                else:
                    print(f"❌ PDF文件未生成: {pdf_file}")
                    return False, None
            else:
                print(f"❌ 转换失败: {result.stderr}")
                return False, None
                
        except subprocess.TimeoutExpired:
            print("❌ 转换超时")
            return False, None
        except Exception as e:
            print(f"❌ 转换过程中出错: {e}")
            return False, None
    
    def _fallback_convert(self, input_file, output_dir):
        """回退到传统转换方式"""
        print("🔄 使用传统方式转换...")
        try:
            input_path = Path(input_file).resolve()
            if output_dir is None:
                output_dir = input_path.parent
            else:
                output_dir = Path(output_dir).resolve()
            
            cmd = [
                'soffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(output_dir),
                str(input_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                pdf_file = output_dir / (input_path.stem + '.pdf')
                if pdf_file.exists():
                    print(f"✅ 传统方式转换成功: {pdf_file.name}")
                    return True, str(pdf_file)
            
            print(f"❌ 传统方式转换失败: {result.stderr}")
            return False, None
            
        except Exception as e:
            print(f"❌ 传统方式转换出错: {e}")
            return False, None
    
    def stop(self):
        """停止守护进程"""
        with self.lock:
            if self.process and self.is_running:
                try:
                    print("🛑 正在停止 LibreOffice 守护进程...")
                    self.process.terminate()
                    
                    # 等待进程结束
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        print("⚠️ 守护进程未正常结束，强制终止...")
                        self.process.kill()
                        self.process.wait()
                    
                    uptime = time.time() - self.start_time if self.start_time else 0
                    print(f"✅ LibreOffice 守护进程已停止")
                    print(f"📊 运行时间: {uptime:.1f}秒, 转换次数: {self.conversion_count}")
                    
                except Exception as e:
                    print(f"❌ 停止守护进程时出错: {e}")
                finally:
                    self.process = None
                    self.is_running = False
                    self.port = None
    
    def restart(self):
        """重启守护进程"""
        print("🔄 重启 LibreOffice 守护进程...")
        self.stop()
        time.sleep(2)
        return self.start()
    
    def get_status(self):
        """获取守护进程状态"""
        if not self.is_running:
            return {
                'running': False,
                'uptime': 0,
                'conversions': 0,
                'port': None
            }
        
        uptime = time.time() - self.start_time if self.start_time else 0
        return {
            'running': True,
            'uptime': uptime,
            'conversions': self.conversion_count,
            'port': self.port,
            'process_id': self.process.pid if self.process else None
        }


# 全局单例实例
_daemon_instance = None

def get_daemon():
    """获取全局守护进程实例"""
    global _daemon_instance
    if _daemon_instance is None:
        _daemon_instance = LibreOfficeDaemon()
    return _daemon_instance

def convert_document_to_pdf(input_file, output_dir=None):
    """便捷函数：转换文档为PDF"""
    daemon = get_daemon()
    return daemon.convert_to_pdf(input_file, output_dir)

def start_daemon():
    """便捷函数：启动守护进程"""
    daemon = get_daemon()
    return daemon.start()

def stop_daemon():
    """便捷函数：停止守护进程"""
    daemon = get_daemon()
    daemon.stop()

def get_daemon_status():
    """便捷函数：获取守护进程状态"""
    daemon = get_daemon()
    return daemon.get_status()


if __name__ == '__main__':
    # 测试代码
    daemon = LibreOfficeDaemon()
    
    if daemon.start():
        print("守护进程测试成功!")
        
        # 创建测试文档
        test_html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>测试</title></head>
<body><h1>LibreOffice守护进程测试</h1><p>这是一个测试文档</p></body></html>"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(test_html)
            test_file = f.name
        
        try:
            # 测试转换
            success, pdf_file = daemon.convert_to_pdf(test_file)
            if success:
                print(f"测试转换成功: {pdf_file}")
                # 清理测试文件
                os.unlink(pdf_file)
            else:
                print("测试转换失败")
        finally:
            os.unlink(test_file)
            daemon.stop()
    else:
        print("守护进程启动失败") 