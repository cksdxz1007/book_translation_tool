#!/usr/bin/env python3
"""
BabelDOC 升级实施脚本

此脚本用于自动化执行BabelDOC从0.5.4升级到0.5.16的过程，
包括版本升级、配置更新、代码优化和测试验证。

使用方法:
    python upgrade_babeldoc.py --dry-run    # 预演模式，不实际执行
    python upgrade_babeldoc.py --execute     # 执行升级
    python upgrade_babeldoc.py --rollback    # 回滚到旧版本
"""

import os
import sys
import subprocess
import shutil
import time
import argparse
from pathlib import Path
from datetime import datetime

class BabelDOCUpgrader:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.backup_dir = Path("backup_babeldoc_upgrade")
        self.log_file = Path("babeldoc_upgrade.log")
        self.start_time = datetime.now()

    def log(self, message, level="INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"

        print(log_message)

        # 写入日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    def run_command(self, command, description=""):
        """执行命令并记录结果"""
        self.log(f"执行命令: {description}")
        self.log(f"命令详情: {' '.join(command)}")

        if self.dry_run:
            self.log("预演模式 - 跳过实际执行", "DRY_RUN")
            return True, "dry_run"

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"命令执行成功: {result.stdout.strip()}")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            self.log(f"命令执行失败: {e.stderr}", "ERROR")
            return False, e.stderr

    def check_environment(self):
        """检查环境准备情况"""
        self.log("开始环境检查...")

        # 检查Python环境
        python_path = shutil.which("python")
        if not python_path:
            self.log("未找到Python解释器", "ERROR")
            return False

        self.log(f"Python路径: {python_path}")

        # 检查当前BabelDOC版本
        success, output = self.run_command(
            ["babeldoc", "--version"],
            "检查当前BabelDOC版本"
        )

        if success:
            current_version = output.strip()
            self.log(f"当前BabelDOC版本: {current_version}")

            if "0.5.16" in current_version:
                self.log("BabelDOC已经是最新版本，无需升级", "WARNING")
                return False
        else:
            self.log("BabelDOC未安装或命令不可用", "WARNING")

        # 检查必要文件
        required_files = [
            "pdf_translator_babeldoc.py",
            "babeldoc.toml",
            "requirements.txt"
        ]

        for file in required_files:
            if not Path(file).exists():
                self.log(f"必要文件缺失: {file}", "ERROR")
                return False

        self.log("环境检查完成")
        return True

    def create_backup(self):
        """创建备份"""
        self.log("开始创建备份...")

        if not self.backup_dir.exists():
            if not self.dry_run:
                self.backup_dir.mkdir(exist_ok=True)

        backup_files = [
            "pdf_translator_babeldoc.py",
            "babeldoc.toml",
            "BABELDOC_INTEGRATION.md"
        ]

        for file in backup_files:
            source = Path(file)
            if source.exists():
                backup_path = self.backup_dir / f"{file}.backup"

                if not self.dry_run:
                    shutil.copy2(source, backup_path)

                self.log(f"备份文件: {file} -> {backup_path}")

        self.log("备份创建完成")
        return True

    def upgrade_babeldoc(self):
        """升级BabelDOC版本"""
        self.log("开始升级BabelDOC...")

        # 使用uv升级
        success, output = self.run_command(
            ["uv", "tool", "install", "--python", "3.12", "BabelDOC"],
            "使用uv升级BabelDOC"
        )

        if not success:
            # 尝试使用pip升级
            self.log("uv升级失败，尝试使用pip...", "WARNING")
            success, output = self.run_command(
                ["pip", "install", "--upgrade", "BabelDOC==0.5.16"],
                "使用pip升级BabelDOC"
            )

        if success:
            # 验证升级结果
            success, output = self.run_command(
                ["babeldoc", "--version"],
                "验证BabelDOC版本"
            )

            if success and "0.5.16" in output:
                self.log("BabelDOC升级成功")
                return True
            else:
                self.log("BabelDOC版本验证失败", "ERROR")
                return False
        else:
            self.log("BabelDOC升级失败", "ERROR")
            return False

    def update_configuration(self):
        """更新配置文件"""
        self.log("开始更新配置文件...")

        # 更新babeldoc.toml
        config_file = Path("babeldoc.toml")
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 添加或更新配置项
            updates = {
                "auto-enable-ocr-workaround = false": "auto-enable-ocr-workaround = true",
                "# pool-max-workers": "pool-max-workers = 8",
                "pool-max-workers =": "pool-max-workers = 8"
            }

            for old, new in updates.items():
                if old in content:
                    content = content.replace(old, new)
                elif new not in content:
                    # 在[babeldoc]部分后添加新配置
                    if "[babeldoc]" in content:
                        insert_pos = content.find("[babeldoc]") + len("[babeldoc]")
                        content = content[:insert_pos] + f"\n{new}" + content[insert_pos:]

            if not self.dry_run:
                with open(config_file, "w", encoding="utf-8") as f:
                    f.write(content)

            self.log("babeldoc.toml配置更新完成")

        # 更新Python代码
        code_file = Path("pdf_translator_babeldoc.py")
        if code_file.exists():
            with open(code_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 更新命令参数
            old_cmd_section = """cmd = [
                "babeldoc",
                "--files", pdf_path,
                "--output", output_dir,
                "--lang-out", target_language,
                "--openai",
                "--openai-model", model_name,
                "--openai-base-url", base_url,
                "--openai-api-key", api_key,
                "--watermark-output-mode", "no_watermark",
                "--report-interval", "2.0",
                "--skip-scanned-detection",  # 跳过扫描检测以加速
                "--enhance-compatibility"    # 增强兼容性
            ]"""

            new_cmd_section = """cmd = [
                "babeldoc",
                "--files", pdf_path,
                "--output", output_dir,
                "--lang-out", target_language,
                "--openai",
                "--openai-model", model_name,
                "--openai-base-url", base_url,
                "--openai-api-key", api_key,
                "--watermark-output-mode", "no_watermark",
                "--report-interval", "1.0",  # 更频繁的进度报告
                "--auto-enable-ocr-workaround",  # 自动处理扫描文档
                "--pool-max-workers", "8",  # 增加工作线程数
                "--qps", "4",  # 明确设置QPS限制
                "--no-auto-extract-glossary"  # 禁用自动术语提取以提高性能
            ]"""

            if old_cmd_section in content:
                content = content.replace(old_cmd_section, new_cmd_section)

                if not self.dry_run:
                    with open(code_file, "w", encoding="utf-8") as f:
                        f.write(content)

                self.log("Python代码更新完成")
            else:
                self.log("未找到需要更新的命令部分，可能已更新或格式不同", "WARNING")

        self.log("配置更新完成")
        return True

    def run_tests(self):
        """运行测试验证"""
        self.log("开始运行测试验证...")

        tests = [
            (["babeldoc", "--help"], "测试BabelDOC基础功能"),
            (["python", "-c", "import babeldoc; print('BabelDOC导入成功')"], "测试Python导入"),
        ]

        all_passed = True

        for command, description in tests:
            success, output = self.run_command(command, description)
            if not success:
                all_passed = False
                self.log(f"测试失败: {description}", "ERROR")

        if all_passed:
            self.log("所有测试验证通过")
        else:
            self.log("部分测试验证失败", "WARNING")

        return all_passed

    def rollback(self):
        """回滚到备份版本"""
        self.log("开始回滚操作...")

        if not self.backup_dir.exists():
            self.log("备份目录不存在，无法回滚", "ERROR")
            return False

        # 恢复备份文件
        backup_files = [
            "pdf_translator_babeldoc.py",
            "babeldoc.toml",
            "BABELDOC_INTEGRATION.md"
        ]

        for file in backup_files:
            backup_path = self.backup_dir / f"{file}.backup"
            if backup_path.exists():
                if not self.dry_run:
                    shutil.copy2(backup_path, file)
                self.log(f"恢复文件: {file}")

        # 降级BabelDOC版本
        success, output = self.run_command(
            ["uv", "tool", "install", "--python", "3.12", "BabelDOC==0.5.4"],
            "降级BabelDOC版本"
        )

        if not success:
            success, output = self.run_command(
                ["pip", "install", "BabelDOC==0.5.4"],
                "使用pip降级BabelDOC版本"
            )

        if success:
            self.log("回滚操作完成")
            return True
        else:
            self.log("回滚操作失败", "ERROR")
            return False

    def cleanup(self):
        """清理临时文件"""
        self.log("开始清理操作...")

        if self.backup_dir.exists() and not self.dry_run:
            # 保留备份文件，仅记录
            self.log(f"备份文件保留在: {self.backup_dir}")

        self.log("清理操作完成")

    def generate_report(self):
        """生成升级报告"""
        end_time = datetime.now()
        duration = end_time - self.start_time

        report = f"""
BabelDOC 升级报告
==================

升级时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {duration}
运行模式: {'预演模式' if self.dry_run else '实际执行'}

操作日志:
--------
"""

        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                report += f.read()

        report_path = Path("babeldoc_upgrade_report.txt")
        if not self.dry_run:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

        self.log(f"升级报告已生成: {report_path}")
        print(report)

def main():
    parser = argparse.ArgumentParser(description="BabelDOC升级脚本")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预演模式，不实际执行升级操作"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="执行升级操作"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚到旧版本"
    )

    args = parser.parse_args()

    if not any([args.dry_run, args.execute, args.rollback]):
        parser.print_help()
        return

    upgrader = BabelDOCUpgrader(dry_run=args.dry_run)

    try:
        if args.rollback:
            # 执行回滚
            upgrader.rollback()
        else:
            # 执行升级流程
            if not upgrader.check_environment():
                upgrader.log("环境检查失败，终止升级", "ERROR")
                return

            if not upgrader.create_backup():
                upgrader.log("备份创建失败，终止升级", "ERROR")
                return

            if not upgrader.upgrade_babeldoc():
                upgrader.log("BabelDOC升级失败，终止升级", "ERROR")
                return

            if not upgrader.update_configuration():
                upgrader.log("配置更新失败", "WARNING")

            if not upgrader.run_tests():
                upgrader.log("测试验证失败", "WARNING")

            upgrader.cleanup()

        upgrader.generate_report()

    except Exception as e:
        upgrader.log(f"升级过程中发生异常: {e}", "ERROR")
        upgrader.generate_report()
        sys.exit(1)

if __name__ == "__main__":
    main()