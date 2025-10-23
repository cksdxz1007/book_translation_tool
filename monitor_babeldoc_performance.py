#!/usr/bin/env python3
"""
BabelDOC 性能监控脚本

此脚本用于监控BabelDOC升级后的性能表现，
包括翻译速度、内存使用和错误率等指标。
"""

import os
import sys
import time
import psutil
import subprocess
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class BabelDOCPerformanceMonitor:
    """BabelDOC性能监控器"""

    def __init__(self, output_dir="performance_logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.metrics = {
            'translation_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'error_count': 0,
            'success_count': 0,
            'file_sizes': []
        }

        self.start_time = datetime.now()

    def get_system_metrics(self):
        """获取系统指标"""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)

        return {
            'memory_used_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'cpu_percent': cpu,
            'timestamp': datetime.now().isoformat()
        }

    def measure_translation_performance(self, pdf_path, target_language="zh"):
        """测量翻译性能"""
        if not Path(pdf_path).exists():
            print(f"错误: 文件不存在 {pdf_path}")
            return None

        file_size = Path(pdf_path).stat().st_size / (1024**2)  # MB

        # 构建翻译命令
        cmd = [
            "babeldoc",
            "--files", pdf_path,
            "--output", str(self.output_dir / "results"),
            "--lang-out", target_language,
            "--openai",
            "--openai-model", "deepseek-chat",
            "--openai-base-url", "https://api.deepseek.com/v1",
            "--openai-api-key", os.getenv("DEEPSEEK_API_KEY", "test"),
            "--watermark-output-mode", "no_watermark",
            "--report-interval", "1.0",
            "--auto-enable-ocr-workaround",
            "--pool-max-workers", "8",
            "--qps", "4",
            "--no-auto-extract-glossary"
        ]

        print(f"测试文件: {pdf_path} ({file_size:.1f} MB)")

        # 记录开始时间
        start_time = time.time()
        start_metrics = self.get_system_metrics()

        try:
            # 执行翻译
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            # 记录结束时间
            end_time = time.time()
            end_metrics = self.get_system_metrics()

            translation_time = end_time - start_time

            if result.returncode == 0:
                # 成功翻译
                self.metrics['success_count'] += 1
                self.metrics['translation_times'].append(translation_time)
                self.metrics['file_sizes'].append(file_size)

                # 计算平均内存和CPU使用
                avg_memory = (start_metrics['memory_used_percent'] + end_metrics['memory_used_percent']) / 2
                avg_cpu = (start_metrics['cpu_percent'] + end_metrics['cpu_percent']) / 2

                self.metrics['memory_usage'].append(avg_memory)
                self.metrics['cpu_usage'].append(avg_cpu)

                performance_data = {
                    'file': pdf_path,
                    'file_size_mb': file_size,
                    'translation_time_seconds': translation_time,
                    'speed_mb_per_second': file_size / translation_time if translation_time > 0 else 0,
                    'avg_memory_percent': avg_memory,
                    'avg_cpu_percent': avg_cpu,
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }

                print(f"✓ 翻译成功 - 耗时: {translation_time:.1f}秒, "
                      f"速度: {file_size/translation_time:.2f} MB/秒")

                return performance_data

            else:
                # 翻译失败
                self.metrics['error_count'] += 1

                error_data = {
                    'file': pdf_path,
                    'file_size_mb': file_size,
                    'translation_time_seconds': translation_time,
                    'error_message': result.stderr,
                    'status': 'error',
                    'timestamp': datetime.now().isoformat()
                }

                print(f"✗ 翻译失败 - 错误: {result.stderr[:100]}...")
                return error_data

        except subprocess.TimeoutExpired:
            # 超时
            self.metrics['error_count'] += 1

            timeout_data = {
                'file': pdf_path,
                'file_size_mb': file_size,
                'translation_time_seconds': 300,
                'error_message': 'Translation timeout (300 seconds)',
                'status': 'timeout',
                'timestamp': datetime.now().isoformat()
            }

            print("✗ 翻译超时")
            return timeout_data

        except Exception as e:
            # 其他异常
            self.metrics['error_count'] += 1

            exception_data = {
                'file': pdf_path,
                'file_size_mb': file_size,
                'translation_time_seconds': time.time() - start_time,
                'error_message': str(e),
                'status': 'exception',
                'timestamp': datetime.now().isoformat()
            }

            print(f"✗ 翻译异常: {e}")
            return exception_data

    def run_performance_suite(self, test_files, iterations=1):
        """运行性能测试套件"""
        print("=" * 60)
        print("BabelDOC 性能测试套件")
        print("=" * 60)

        results = []

        for iteration in range(iterations):
            print(f"\n--- 迭代 {iteration + 1}/{iterations} ---")

            for test_file in test_files:
                if Path(test_file).exists():
                    result = self.measure_translation_performance(test_file)
                    if result:
                        results.append(result)

                    # 短暂休息避免过热
                    time.sleep(2)
                else:
                    print(f"跳过不存在的文件: {test_file}")

        return results

    def calculate_statistics(self):
        """计算性能统计"""
        stats = {}

        if self.metrics['translation_times']:
            times = self.metrics['translation_times']
            stats['translation_time'] = {
                'min': min(times),
                'max': max(times),
                'avg': sum(times) / len(times),
                'count': len(times)
            }

        if self.metrics['file_sizes']:
            sizes = self.metrics['file_sizes']
            stats['file_size'] = {
                'min_mb': min(sizes),
                'max_mb': max(sizes),
                'avg_mb': sum(sizes) / len(sizes)
            }

        if self.metrics['memory_usage']:
            memory = self.metrics['memory_usage']
            stats['memory_usage'] = {
                'min_percent': min(memory),
                'max_percent': max(memory),
                'avg_percent': sum(memory) / len(memory)
            }

        if self.metrics['cpu_usage']:
            cpu = self.metrics['cpu_usage']
            stats['cpu_usage'] = {
                'min_percent': min(cpu),
                'max_percent': max(cpu),
                'avg_percent': sum(cpu) / len(cpu)
            }

        stats['success_rate'] = (
            self.metrics['success_count'] /
            (self.metrics['success_count'] + self.metrics['error_count'])
            if (self.metrics['success_count'] + self.metrics['error_count']) > 0 else 0
        )

        stats['total_tests'] = self.metrics['success_count'] + self.metrics['error_count']

        return stats

    def generate_report(self, results):
        """生成性能报告"""
        stats = self.calculate_statistics()

        report = {
            'monitor_start_time': self.start_time.isoformat(),
            'monitor_end_time': datetime.now().isoformat(),
            'babeldoc_version': self.get_babeldoc_version(),
            'system_info': self.get_system_info(),
            'performance_statistics': stats,
            'detailed_results': results,
            'metrics_summary': self.metrics
        }

        # 保存报告
        report_file = self.output_dir / f"performance_report_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 打印摘要
        self.print_summary(stats, report_file)

        return report_file

    def get_babeldoc_version(self):
        """获取BabelDOC版本"""
        try:
            result = subprocess.run(
                ["babeldoc", "--version"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"

    def get_system_info(self):
        """获取系统信息"""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': psutil.cpu_count(),
            'total_memory_gb': psutil.virtual_memory().total / (1024**3),
            'disk_usage': {}
        }

    def print_summary(self, stats, report_file):
        """打印性能摘要"""
        print("\n" + "=" * 60)
        print("性能测试摘要")
        print("=" * 60)

        print(f"总测试次数: {stats.get('total_tests', 0)}")
        print(f"成功次数: {self.metrics['success_count']}")
        print(f"失败次数: {self.metrics['error_count']}")
        print(f"成功率: {stats.get('success_rate', 0) * 100:.1f}%")

        if 'translation_time' in stats:
            tt = stats['translation_time']
            print(f"\n翻译时间统计 (秒):")
            print(f"  最短: {tt['min']:.1f}")
            print(f"  最长: {tt['max']:.1f}")
            print(f"  平均: {tt['avg']:.1f}")

        if 'file_size' in stats:
            fs = stats['file_size']
            print(f"\n文件大小统计 (MB):")
            print(f"  最小: {fs['min_mb']:.1f}")
            print(f"  最大: {fs['max_mb']:.1f}")
            print(f"  平均: {fs['avg_mb']:.1f}")

        if 'memory_usage' in stats:
            mem = stats['memory_usage']
            print(f"\n内存使用统计 (%):")
            print(f"  最低: {mem['min_percent']:.1f}")
            print(f"  最高: {mem['max_percent']:.1f}")
            print(f"  平均: {mem['avg_percent']:.1f}")

        print(f"\n详细报告保存至: {report_file}")


def main():
    """主函数"""
    # 测试文件列表（根据实际情况修改）
    test_files = [
        "test_documents/small.pdf",      # 小文件 (1-5页)
        "test_documents/medium.pdf",     # 中等文件 (10-20页)
        "test_documents/large.pdf",      # 大文件 (50+页)
    ]

    # 过滤存在的文件
    existing_files = [f for f in test_files if Path(f).exists()]

    if not existing_files:
        print("警告: 未找到测试文件，创建示例文件...")
        # 这里可以添加创建示例测试文件的代码
        print("请手动创建测试文件或修改test_files列表")
        return

    # 创建监控器
    monitor = BabelDOCPerformanceMonitor()

    # 运行性能测试
    results = monitor.run_performance_suite(
        test_files=existing_files,
        iterations=2  # 每个文件测试2次
    )

    # 生成报告
    report_file = monitor.generate_report(results)

    print(f"\n🎯 性能监控完成!")
    print(f"报告文件: {report_file}")


if __name__ == "__main__":
    # 检查psutil依赖
    try:
        import psutil
    except ImportError:
        print("错误: 需要安装psutil库")
        print("安装命令: pip install psutil")
        sys.exit(1)

    main()