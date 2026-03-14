import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class SetuArgs:
    tags: list[str]
    num: int
    r18_override: Optional[int] = None


@dataclass
class SukiArgs:
    tags: list[str]
    num: int
    level: Optional[str] = None
    taste: Optional[str] = None
    r18_override: Optional[int] = None


def parse_setu_args(args_str: str, r18_mode: bool) -> SetuArgs:
    tags = []
    num = 1
    r18_override = None
    
    if not args_str or not args_str.strip():
        return SetuArgs(tags=tags, num=num, r18_override=1 if r18_mode else None)
    
    parts = args_str.strip().split()
    
    for part in parts:
        if part.isdigit():
            num = min(max(1, int(part)), 20)
        else:
            tags.append(part)
    
    if r18_mode and r18_override is None:
        r18_override = 1
    
    return SetuArgs(tags=tags, num=num, r18_override=r18_override)


def parse_suki_args(args_str: str, r18_mode: bool) -> SukiArgs:
    tags = []
    num = 1
    level = None
    taste = None
    r18_override = None
    
    if not args_str or not args_str.strip():
        return SukiArgs(tags=tags, num=num, level=level, taste=taste, 
                       r18_override=1 if r18_mode else None)
    
    parts = args_str.strip().split()
    i = 0
    
    while i < len(parts):
        part = parts[i].lower()
        
        if part == 'level' and i + 1 < len(parts):
            level_val = parts[i + 1]
            if re.match(r'^\d+(-\d+)?$', level_val):
                if '-' in level_val:
                    start, end = level_val.split('-')
                    if start.isdigit() and end.isdigit() and int(start) <= int(end):
                        start_num, end_num = int(start), int(end)
                        if start_num <= 6 and end_num <= 6 and start_num >= 0 and end_num >= 0:
                            level = level_val
                else:
                    level_num = int(level_val)
                    if 0 <= level_num <= 6:
                        level = level_val
            i += 2
            continue
            
        if part == 'taste' and i + 1 < len(parts):
            taste_val = parts[i + 1]
            if re.match(r'^\d+(,\d+)*$', taste_val):
                taste_nums = [int(x) for x in taste_val.split(',')]
                if all(0 <= x <= 3 for x in taste_nums):
                    taste = taste_val
            i += 2
            continue
        
        if part.isdigit():
            num = min(max(1, int(part)), 5)
        else:
            tags.append(parts[i])
        
        i += 1
    
    if level:
        if '-' in level:
            level_nums = [int(x) for x in level.split('-')]
            if any(n >= 5 for n in level_nums):
                r18_override = 1
        else:
            if int(level) >= 5:
                r18_override = 1
    
    if r18_mode and r18_override is None:
        r18_override = 1
    
    return SukiArgs(tags=tags, num=num, level=level, taste=taste, 
                   r18_override=r18_override)


def format_image_info(image) -> str:
    info = f"""PID: {image.pid}
标题: {image.title}
作者: {image.author}
标签: {', '.join(image.tags[:10])}"""
    
    if image.level is not None:
        info += f"\nLevel: {image.level}"
    if image.taste is not None:
        taste_names = {0: "随机", 1: "萝莉", 2: "少女", 3: "御姐"}
        info += f"\n类型: {taste_names.get(image.taste, image.taste)}"
    
    return info
