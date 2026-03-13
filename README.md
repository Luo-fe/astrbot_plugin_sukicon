# Sukicon - AstrBot 图像 API 插件

一个功能完整的 AstrBot 插件，集成 Lolicon API 和 Suki Loli API，实现图像资源获取功能。

## ✨ 功能特性

- 🔄 **API 切换**: 在 Lolicon 和 Suki API 之间无缝切换
- 🔞 **R18 模式**: 支持一键切换 R18 模式
- 🏷️ **多标签搜索**: 支持多标签 OR 搜索
- 📊 **Suki 特有参数**: 支持 level（社保程度）和 taste（图片类型）参数
- 💾 **本地存储**: 自动保存图片和标签信息到本地
- 📝 **日志记录**: 完整的 API 调用日志
- 📖 **手册系统**: 内置详细的使用手册
- 🎭 **趣味回复**: 可配置的趣味回复，让交互更有趣
- 🚫 **图片去重**: 自动过滤已发送过的图片，避免重复

## 📦 安装

### 方法一：直接下载
1. 下载本仓库的 ZIP 文件
2. 解压后将 `astrbot_plugin_sukicon` 文件夹放入 AstrBot 的 `data/plugins/` 目录下
3. 重启 AstrBot

### 方法二：Git Clone
```bash
cd AstrBot/data/plugins/
git clone https://github.com/Luo-fe/astrbot_plugin_sukicon.git
```

## ⚙️ 配置

在 AstrBot 插件设置中可配置以下选项：

### 基础配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `default_api` | 默认 API | `lolicon` |
| `r18_mode` | R18 模式 | `false` |
| `cooldown_seconds` | 冷却时间（秒） | `10` |
| `enable_local_storage` | 启用本地存储 | `true` |
| `enable_deduplication` | 启用图片去重 | `true` |
| `dedup_history_size` | 去重历史记录数量 | `100` |

### 存储路径

- 默认使用插件数据目录下的 `images/lolicon` 和 `images/suki`
- 可在配置中自定义存储路径

### 趣味回复配置

| 配置项 | 说明 |
|--------|------|
| `funny_replies.enabled` | 是否启用趣味回复 |
| `funny_replies.fetching` | 获取图片时的回复列表 |
| `funny_replies.success` | 成功获取图片的回复列表 |
| `funny_replies.no_result` | 没有找到图片的回复列表 |
| `funny_replies.network_error` | 网络错误时的回复列表 |
| `funny_replies.timeout` | 请求超时时的回复列表 |
| `funny_replies.cooldown` | 冷却中的回复列表 |
| `funny_replies.r18_on` | R18 模式开启的回复列表 |
| `funny_replies.r18_off` | R18 模式关闭的回复列表 |
| `funny_replies.api_switch` | API 切换的回复列表（支持 `{api}` 占位符） |

## 📖 使用说明

### 基础指令

| 指令 | 别名 | 说明 |
|------|------|------|
| `切换loli` | `切换api`, `switch` | 切换 API |
| `切换r18` | `r18开关` | 切换 R18 模式 |
| `当前状态` | `status` | 查看当前状态 |
| `涩涩手册` | `sssc` | 查看通用手册 |
| `lolicon手册` | `lolicon` | 查看 Lolicon 手册 |
| `suki手册` | `sukihelp` | 查看 Suki 手册 |

### Lolicon API 指令

```
色图 [标签] [数量]           # 获取图片（受R18模式影响）
色图r18 [标签] [数量]        # 强制获取 R18 图片
色图全年龄 [标签] [数量]     # 强制获取非 R18 图片
```

**示例**:
```
色图                    # 随机获取 1 张图片
色图 白丝               # 获取白丝标签图片
色图 白丝 黑丝          # 获取白丝或黑丝标签图片
色图 白丝 3             # 获取 3 张白丝标签图片
```

### Suki API 指令

```
suki [标签] [level 等级] [taste 类型] [数量]    # 获取图片
sukir18 [标签] [level 等级] [数量]              # 强制 R18
suki全年龄 [标签] [level 等级] [taste 类型] [数量]  # 强制非 R18
```

**Level 参数（社保程度）**:
- 0: 除了好看以外没什么特别之处
- 1: 好看，也有点涩
- 2: 涩
- 3: 很涩
- 4: R18擦边球
- 5: R18
- 6: R18+有氧模式

**Taste 参数（图片类型）**:
- 0: 随机
- 1: 萝莉
- 2: 少女
- 3: 御姐

**综合搜索示例**:
```
suki 拉菲 level 3 taste 1           # 拉菲 + level 3 + 萝莉
suki 白丝 黑丝 level 2-4 taste 1,2  # 白丝/黑丝 + level 2-4 + 萝莉/少女
suki level 5                        # level 5（自动设置 R18）
```

**注意**:
- Level 5-6 的图片在 Suki API 中数据较少
- Level 5-6 的图片大多没有 taste 分类，建议不指定 taste 参数

## 💾 图片存储

启用本地存储后，图片会自动保存到指定目录：

- **文件命名**: 按获取顺序命名（00001.jpg, 00002.jpg, ...）
- **标签文件**: 同名 txt 文件存储图片信息

**标签文件格式**:
```
PID: 12345678
标题: 作品标题
作者: 作者名
标签: 标签1, 标签2, 标签3
来源: Lolicon/Suki
获取时间: 2024-01-01 12:00:00
```

## 📁 文件结构

```
astrbot_plugin_sukicon/
├── main.py              # 插件主入口
├── config.py            # 配置管理
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置模式
├── apis/
│   ├── __init__.py
│   ├── base.py          # API 基类
│   ├── lolicon.py       # Lolicon API 实现
│   └── suki.py          # Suki API 实现
└── utils/
    ├── __init__.py
    ├── logger.py        # 日志工具
    ├── storage.py       # 图像存储工具
    └── helpers.py       # 辅助函数
```

## 🎭 趣味回复效果

启用趣味回复后，交互将更加生动：

**获取图片时**:
```
用户: 色图
机器人: 呼呼呼起飞啦！
机器人: [图片]
        别冲的到处都是。
        PID: 12345678
        标题: xxx
        ...
```

**没有找到图片时**:
```
用户: 色图 不存在的标签
机器人: 糟糕找不到学习资料了。
```

**图片去重提示**:
```
用户: suki taste 1
机器人: 这个条件下的图片都发过了，换个条件试试吧~
        提示：可以尝试不同的 level 或 taste 参数
```

## 🔧 API 参考

### Lolicon API v2
- 端点: `https://api.lolicon.app/setu/v2`
- 文档: [Lolicon API 文档](https://api.lolicon.app/)

### Suki API v1
- 端点: `https://lolisuki.cn/api/setu/v1`
- 文档: [Suki API 文档](https://lolisuki.cn/)

## 📜 许可证

MIT License

## 🙏 致谢

- [Lolicon API](https://api.lolicon.app/) - 提供图像 API 服务
- [Suki API](https://lolisuki.cn/) - 提供图像 API 服务
- [AstrBot](https://github.com/Soulter/AstrBot) - AstrBot 框架
