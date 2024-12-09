import concurrent.futures
import subprocess
import sys
import time
import os
import random
import argparse
import logging
from typing import Dict, List, Optional
from pathlib import Path
from tqdm import tqdm
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProgressManager:
    def __init__(self, total_tasks: int):
        self.progress = tqdm(total=total_tasks,
                           desc="🚀 正在分析内存",
                           bar_format='{desc}: |{bar:30}| {percentage:3.0f}% [{n_fmt}/{total_fmt}] {elapsed}<{remaining}',
                           ncols=100,
                           position=0,
                           leave=True)
        self.completed_tasks = 0
        self.lock = threading.Lock()

    def update(self, task_name: str):
        with self.lock:
            self.completed_tasks += 1
            self.progress.set_description(f"🚀 {task_name}")
            self.progress.update(1)

    def close(self):
        self.progress.close()

class VolatilityAnalyzer:
    def __init__(self, volatility_path: str = "vol.exe"):
        self.volatility_path = volatility_path
        self.emoji_list = ['🎉', '🚀', '📝', '📁', '📋', '💭', '🦄', '🤗', '💖']
        self.timeout = 120  # 默认超时时间增加到120秒
        self.progress_manager = None

    def random_emoji(self) -> str:
        return random.choice(self.emoji_list)

    def get_remaining_tasks(self, output_path: Path, tasks: Dict) -> List[str]:
        return [task_name for task_name in tasks.keys() 
                if not (output_path / f"{task_name}.txt").exists()]

    def run_command(self, command: List[str], task_name: str, output_path: Path, tasks: Dict) -> None:
        try:
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                shell=True
            )
            
            try:
                output = result.stdout.decode("UTF-8", errors="ignore")
            except UnicodeDecodeError:
                output = result.stdout.decode("ISO-8859-1", errors="ignore")

            if output:
                output_file = output_path / f"{task_name}.txt"
                output_file.write_text(output, encoding='utf-8')
                if self.progress_manager:
                    self.progress_manager.update(task_name)
            else:
                logger.warning(f"[-] 任务无输出: {task_name}")
                if self.progress_manager:
                    self.progress_manager.update(f"{task_name} (无输出)")

        except subprocess.TimeoutExpired:
            logger.error(f"[-] {task_name} 在 {self.timeout} 秒后超时")
            if self.progress_manager:
                self.progress_manager.update(f"{task_name} (超时)")
        except Exception as e:
            logger.error(f"[-] {task_name} 执行出错: {str(e)}")
            if self.progress_manager:
                self.progress_manager.update(f"{task_name} (错误)")

    def generate_markdown(self, tasks: Dict, output_path: Path, 
                        tasklist: List[str], tasklist_help: List[str], 
                        task_filescanlist: List[str], task_filescanlist_help: List[str]) -> None:
        try:
            logger.info("📝 正在生成分析报告...")
            markdown = []
            with tqdm(total=len(tasks), desc="📝 处理结果",
                     bar_format='{desc}: |{bar:30}| {percentage:3.0f}% [{n_fmt}/{total_fmt}]',
                     ncols=80,
                     position=0,
                     leave=True) as pbar:
                for task_name in tasks.keys():
                    try:
                        if "filescan" in task_name:
                            scan_type = task_name.split('(')[1].split(')')[0]
                            index = task_filescanlist.index(scan_type)
                            help_text = task_filescanlist_help[index]
                        else:
                            index = tasklist.index(task_name)
                            help_text = tasklist_help[index]
                        
                        markdown.append(f"# {task_name}\n## {help_text}")
                        
                        task_file = output_path / f"{task_name}.txt"
                        if task_file.exists():
                            content = task_file.read_text(encoding='utf-8')
                            markdown.append(f"```\n{content}\n```\n")
                        else:
                            markdown.append("*暂无数据*\n")
                        pbar.update(1)
                    except Exception as e:
                        logger.error(f"处理 {task_name} 时出错: {str(e)}")
                    
            summary_file = output_path / "summary.md"
            summary_file.write_text('\n'.join(markdown), encoding='utf-8')
            logger.info(f"[+] 分析报告已生成: {summary_file}")
            
        except Exception as e:
            logger.error(f"[-] 生成报告时出错: {str(e)}")

    def analyze_memory_dump(self, memorydump_path: str, profile: Optional[str] = None, 
                          dumpfiles: bool = False, dumpfiles_location: Optional[str] = None) -> None:
        start_time = time.time()
        
        # 创建输出目录
        output_path = Path(os.path.dirname(memorydump_path)) / 'output'
        output_path.mkdir(exist_ok=True)
        
        if dumpfiles and profile and dumpfiles_location:
            logger.info("[*]🥰 正在执行文件导出")
            with tqdm(total=1, desc="📥 正在导出文件",
                     bar_format='{desc}: |{bar:30}| {percentage:3.0f}%',
                     ncols=80,
                     position=0,
                     leave=True) as pbar:
                command = [
                    self.volatility_path, "-f", memorydump_path,
                    f"--profile={profile}", "dumpfiles",
                    "-Q", dumpfiles_location, "-D", './'
                ]
                try:
                    result = subprocess.run(command, stdout=subprocess.PIPE)
                    output = result.stdout.decode("cp1252", errors="ignore")
                    print(output)
                    logger.info("[+] 🏆️ 文件导出完成!")
                    pbar.update(1)
                    return
                except Exception as e:
                    logger.error(f"[-] 文件导出失败: {str(e)}")
                    return

        # 获取 profile
        if not profile:
            logger.info("[*] 🥰 未检测到 Profile，正在自动检测")
            with tqdm(total=1, desc="🔍 检测系统版本",
                     bar_format='{desc}: |{bar:30}| {percentage:3.0f}%',
                     ncols=80,
                     position=0,
                     leave=True) as pbar:
                try:
                    command = [self.volatility_path, "-f", memorydump_path, "imageinfo"]
                    result = subprocess.run(command, stdout=subprocess.PIPE)
                    output = result.stdout.decode("cp1252", errors="ignore")
                    
                    for line in output.split("\n"):
                        if "Suggested Profile(s)" in line:
                            profile = line.split(":")[1].strip().split(",")[0].strip()
                            logger.info(f"[+] 🥰 已选择 Profile: {profile}")
                            break
                    pbar.update(1)
                except Exception as e:
                    logger.error(f"[-] Profile 检测失败: {str(e)}")
                    return
        
        # 读取任务配置
        try:
            with open("tasklist.cfg", 'r', encoding='utf-8') as f:
                config_lines = f.readlines()
            tasklist = [line.split('-')[0] for line in config_lines]
            tasklist_help = [line.split('-')[1] for line in config_lines]
        except Exception as e:
            logger.error(f"[-] 读取任务配置失败: {str(e)}")
            return

        # 文件扫描任务
        task_filescanlist = ["Desktop", "Downloads", ".zip", "flag", 'evtx']
        task_filescanlist_help = ["桌面", "下载", "压缩包", "flag", '日志']
        
        # 生成任务
        tasks = {}
        total_tasks = len(tasklist) + len(task_filescanlist)
        logger.info(f"[*] 🥰 正在生成任务列表，共 {total_tasks} 个任务")
        
        for task in tasklist:
            tasks[task] = [f"--profile={profile}", "-f", memorydump_path, task]
        for task_filescan in task_filescanlist:
            tasks[f"filescan({task_filescan})"] = [
                f"--profile={profile}", "-f", memorydump_path,
                "filescan", "|", "findstr", task_filescan
            ]

        # 初始化进度管理器
        self.progress_manager = ProgressManager(total_tasks)

        # 执行任务
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(
                    self.run_command,
                    [self.volatility_path] + command,
                    task_name,
                    output_path,
                    tasks
                ): task_name for task_name, command in tasks.items()
            }
            concurrent.futures.wait(futures)

        # 关闭进度条
        if self.progress_manager:
            self.progress_manager.close()

        logger.info("[+] 🏆️ 所有任务已完成!")
        
        # 生成报告
        execution_time = time.time() - start_time
        logger.info(f"[+] 🕡️ 总用时: {execution_time:.2f} 秒")
        logger.info("[*] 🎀 正在创建分析报告")
        
        self.generate_markdown(
            tasks, output_path, tasklist, tasklist_help,
            task_filescanlist, task_filescanlist_help
        )
        logger.info("[+] 🏆️ 分析报告已生成完成")

def main():
    parser = argparse.ArgumentParser(description='Volatility Pro - 内存取证分析工具')
    parser.add_argument('memorydump_path', help='内存镜像文件路径')
    parser.add_argument('--profile', help='Volatility profile 配置')
    parser.add_argument('--dumpfiles', action='store_true', help='执行文件导出')
    parser.add_argument('--dumpfiles-location', help='要导出的文件内存位置')
    parser.add_argument('--timeout', type=int, default=120, help='每个任务的超时时间（秒）')
    parser.add_argument('--volatility-path', default='vol.exe', help='Volatility 程序路径')
    
    args = parser.parse_args()
    
    analyzer = VolatilityAnalyzer(volatility_path=args.volatility_path)
    analyzer.timeout = args.timeout
    
    try:
        analyzer.analyze_memory_dump(
            args.memorydump_path,
            profile=args.profile,
            dumpfiles=args.dumpfiles,
            dumpfiles_location=args.dumpfiles_location
        )
    except KeyboardInterrupt:
        logger.info("\n[*] 分析已被用户中断")
    except Exception as e:
        logger.error(f"[-] 严重错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
