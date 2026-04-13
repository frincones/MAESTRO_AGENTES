# claude-code-sourcemap

[![linux.do](https://img.shields.io/badge/linux.do-huo0-blue?logo=linux&logoColor=white)](https://linux.do)

> [!WARNING]
> 本仓库不是 Anthropic 官方仓库，而是一个面向中文读者的研究与备份仓库。
>  
> 仓库内容基于公开 npm 包与 source map 还原整理，仅供技术研究、学习与归档使用，不代表 Anthropic 内部原始开发仓库结构。
>  
> 本仓库同时作为备份镜像存在，目的之一是防止原始整理仓库在被 Anthropic 删除、下架或限制访问后，相关研究资料一并消失。

## 说明

这个仓库整理的是从 `@anthropic-ai/claude-code` 发布包中提取出的 source map 信息，并据此还原出的 TypeScript 源码快照。

- 还原目标版本：`2.1.88`
- 还原方式：提取 `cli.js.map` 中的 `sourcesContent`
- 当前仓库定位：中文说明版 + 研究归档版 + 备份镜像

## 原始整理项目

本仓库基于原始整理项目同步而来。

- 原始整理作者：`ChinaSiro`
- Linux.do 用户：`huo0`
- 原项目地址：https://github.com/ChinaSiro/claude-code-sourcemap

这里特别保留 `Linux.do` 标识，用于注明这份还原整理源码的原始发布者与社区身份。

## 来源

- npm 包：[@anthropic-ai/claude-code](https://www.npmjs.com/package/@anthropic-ai/claude-code)
- 包内关键文件：`package/cli.js.map`
- 仓库内附带原始归档包：`claude-code-2.1.88.tgz`
- 还原脚本：`extract-sources.js`

## 仓库结构

```text
.
├─ package/                     # npm 包解包后的原始内容
│  ├─ cli.js
│  ├─ cli.js.map
│  ├─ package.json
│  └─ vendor/
├─ restored-src/                # 根据 source map 还原出的源码树
│  ├─ src/
│  │  ├─ main.tsx               # CLI 主入口
│  │  ├─ tools/                 # 工具实现（Bash、Read/Edit、MCP、Agent 等）
│  │  ├─ commands/              # 命令系统
│  │  ├─ services/              # API、MCP、分析与支撑服务
│  │  ├─ coordinator/           # 多 Agent / 协调模式
│  │  ├─ assistant/             # Assistant / KAIROS 相关实现
│  │  ├─ remote/                # 远程会话相关实现
│  │  ├─ plugins/               # 插件系统
│  │  ├─ skills/                # 技能系统
│  │  ├─ voice/                 # 语音相关能力
│  │  └─ utils/                 # 各类基础设施与工具函数
│  └─ node_modules/             # 还原过程中保留的依赖内容
├─ extract-sources.js           # 从 source map 提取源码的脚本
└─ README.md
```

## 这份仓库里有什么

和早期的一些“壳子仓库”不同，这个仓库里已经包含大量核心实现，还原后的 `restored-src/src` 中可以看到：

- CLI 入口与主循环
- 工具系统与权限控制
- 子 Agent / 协调模式 / 团队模式
- 任务系统
- MCP 集成
- 插件系统
- 技能系统
- 远程会话能力
- 多种 UI / TUI 相关模块

但需要注意：这依然是基于 source map 还原出来的研究版本，不应简单等同于 Anthropic 内部真实仓库的原始提交形态。

## 使用方式

如果你只是想研究来源，可以直接看：

- `package/cli.js.map`
- `extract-sources.js`
- `restored-src/src/`

如果你想确认这份源码是怎么提取出来的，可以从 `extract-sources.js` 开始阅读。

## 声明

- Claude Code 相关源码版权归 [Anthropic](https://www.anthropic.com) 所有。
- 本仓库不声称拥有原始源码的版权，也不声称与 Anthropic 存在任何官方关系。
- 本仓库仅用于技术研究、学习、分析与归档备份，请勿直接用于存在法律风险的用途。
- 如原作者 `ChinaSiro` 或相关权利方对署名、链接或内容展示方式有异议，可按需调整。
