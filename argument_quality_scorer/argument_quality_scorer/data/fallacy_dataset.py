"""
逻辑谬误数据集接口

用于下载和预处理 tmakesense/logical-fallacy 数据集（dataset-fixed）。
为未来微调谬误分类器做准备。

数据来源: https://github.com/tmakesense/logical-fallacy
"""

import json
import os
from pathlib import Path
from typing import Optional, Generator
import httpx


class FallacyDataset:
    """
    逻辑谬误数据集
    
    提供数据下载、缓存、预处理功能。
    """
    
    # GitHub raw 文件 URL
    DATASET_URLS = {
        "train": "https://raw.githubusercontent.com/tmakesense/logical-fallacy/main/dataset-fixed/train.jsonl",
        "dev": "https://raw.githubusercontent.com/tmakesense/logical-fallacy/main/dataset-fixed/dev.jsonl",
        "test": "https://raw.githubusercontent.com/tmakesense/logical-fallacy/main/dataset-fixed/test.jsonl",
    }
    
    # 谬误类型映射（英文到中文）
    FALLACY_TYPES = {
        "ad hominem": "人身攻击",
        "appeal to authority": "诉诸权威",
        "appeal to emotion": "诉诸情感",
        "appeal to nature": "诉诸自然",
        "appeal to tradition": "诉诸传统",
        "circular reasoning": "循环论证",
        "false cause": "虚假因果",
        "false dilemma": "假二元对立",
        "hasty generalization": "以偏概全",
        "slippery slope": "滑坡谬误",
        "straw man": "稻草人谬误",
        "red herring": "转移话题",
        "equivocation": "模棱两可",
        "loaded question": "诱导性问题",
    }
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        初始化数据集接口
        
        Args:
            cache_dir: 缓存目录，默认为 ~/.cache/aqs/fallacy_data
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".cache" / "aqs" / "fallacy_data"
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def download(self, split: str = "train", force: bool = False) -> Path:
        """
        下载数据集
        
        Args:
            split: 数据集分割 - train/dev/test
            force: 是否强制重新下载
        
        Returns:
            下载的文件路径
        """
        if split not in self.DATASET_URLS:
            raise ValueError(f"无效的 split: {split}，可选: {list(self.DATASET_URLS.keys())}")
        
        cache_file = self.cache_dir / f"{split}.jsonl"
        
        # 检查缓存
        if cache_file.exists() and not force:
            print(f"使用缓存: {cache_file}")
            return cache_file
        
        # 下载
        url = self.DATASET_URLS[split]
        print(f"正在下载 {split} 数据集...")
        
        try:
            with httpx.Client(timeout=60) as client:
                response = client.get(url)
                response.raise_for_status()
                
                cache_file.write_text(response.text, encoding='utf-8')
                print(f"已保存到: {cache_file}")
                
                return cache_file
        except Exception as e:
            print(f"下载失败: {e}")
            raise
    
    def download_all(self, force: bool = False) -> dict[str, Path]:
        """下载所有数据集分割"""
        paths = {}
        for split in self.DATASET_URLS:
            try:
                paths[split] = self.download(split, force)
            except Exception as e:
                print(f"警告: {split} 下载失败 - {e}")
        return paths
    
    def load(self, split: str = "train") -> Generator[dict, None, None]:
        """
        加载数据集
        
        Yields:
            数据条目字典
        """
        cache_file = self.cache_dir / f"{split}.jsonl"
        
        if not cache_file.exists():
            # 尝试下载
            self.download(split)
        
        with open(cache_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    
    def get_statistics(self, split: str = "train") -> dict:
        """
        获取数据集统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "total": 0,
            "fallacy_types": {},
            "avg_length": 0,
        }
        
        total_length = 0
        for item in self.load(split):
            stats["total"] += 1
            
            fallacy = item.get("label", "unknown")
            stats["fallacy_types"][fallacy] = stats["fallacy_types"].get(fallacy, 0) + 1
            
            text = item.get("text", "")
            total_length += len(text)
        
        if stats["total"] > 0:
            stats["avg_length"] = round(total_length / stats["total"], 1)
        
        return stats
    
    def preprocess_for_training(
        self, 
        split: str = "train",
        output_file: Optional[Path] = None
    ) -> list[dict]:
        """
        预处理数据集用于训练
        
        将数据转换为统一格式:
        {
            "text": "...",
            "label": "...",
            "label_cn": "...",
        }
        
        Args:
            split: 数据集分割
            output_file: 输出文件路径（可选）
        
        Returns:
            预处理后的数据列表
        """
        processed = []
        
        for item in self.load(split):
            text = item.get("text", "")
            label = item.get("label", "unknown").lower()
            label_cn = self.FALLACY_TYPES.get(label, label)
            
            processed.append({
                "text": text,
                "label": label,
                "label_cn": label_cn,
            })
        
        if output_file:
            output_file = Path(output_file)
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in processed:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"已保存预处理数据到: {output_file}")
        
        return processed


# CLI 脚本
def main():
    """数据集下载脚本入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="逻辑谬误数据集下载工具")
    parser.add_argument("--split", default="all", help="数据集分割 (train/dev/test/all)")
    parser.add_argument("--force", action="store_true", help="强制重新下载")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--preprocess", action="store_true", help="预处理数据")
    parser.add_argument("--output", help="预处理输出目录")
    
    args = parser.parse_args()
    
    dataset = FallacyDataset()
    
    if args.split == "all":
        dataset.download_all(force=args.force)
    else:
        dataset.download(args.split, force=args.force)
    
    if args.stats:
        for split in ["train", "dev", "test"]:
            try:
                stats = dataset.get_statistics(split)
                print(f"\n{split} 统计:")
                print(f"  总数: {stats['total']}")
                print(f"  平均长度: {stats['avg_length']} 字符")
                print(f"  谬误类型分布: {stats['fallacy_types']}")
            except Exception:
                pass
    
    if args.preprocess:
        output_dir = Path(args.output) if args.output else dataset.cache_dir / "processed"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for split in ["train", "dev", "test"]:
            try:
                dataset.preprocess_for_training(
                    split, 
                    output_dir / f"{split}_processed.jsonl"
                )
            except Exception as e:
                print(f"警告: {split} 预处理失败 - {e}")


if __name__ == "__main__":
    main()
