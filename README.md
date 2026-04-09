# 🌻 Plants vs Zombies - Commercial Edition

> 基于 Python/Pygame 的商业级植物大战僵尸完整实现

## 📋 项目管理

- **Project Board**: [GitHub Projects](https://github.com/users/Kiris-z/projects/2)
- **技术栈**: Python 3.10+ / Pygame 2.x
- **架构**: ECS-lite + State Machine + Scene Manager

## 🎯 开发路线图

| 阶段 | 周期 | 内容 | 状态 |
|------|------|------|------|
| M1: 核心引擎 | Sprint 1-2 | 引擎框架、资源管理、网格系统、UI | 🔨 进行中 |
| M2: 基础玩法 | Sprint 3-4 | 植物/僵尸、战斗系统、经济、AI | ⏳ 待开始 |
| M3: 关卡系统 | Sprint 5-6 | 完整关卡 1-1~1-10、波次设计、难度曲线 | ⏳ 待开始 |
| M4: 高级特性 | Sprint 7-8 | 夜间关卡、特殊僵尸、成就、存档 | ⏳ 待开始 |
| M5: 打磨发布 | Sprint 9-10 | 优化、平衡、Bug修复、打包 | ⏳ 待开始 |

## 🌱 已有资源

- **植物**: 17种 (Peashooter, SunFlower, WallNut, SnowPea, CherryBomb, RepeaterPea, Chomper, PotatoMine, Spikeweed, Squash, Threepeater, Jalapeno, PuffShroom, SunShroom, IceShroom, HypnoShroom, ScaredyShroom)
- **僵尸**: 5种 (Normal, Conehead, Buckethead, Flag, Newspaper)
- **子弹**: 4种 + 爆炸特效
- **UI**: 主菜单、关卡选择、卡牌、背景

## 🏃 运行

```bash
pip install pygame
python main.py
```

## 📐 架构

```
src/
├── engine/          # 游戏引擎核心
│   ├── game.py      # 主循环 + 状态机
│   ├── scene.py     # 场景管理器
│   ├── resource.py  # 资源管理器
│   └── sprite.py    # 精灵动画系统
├── entities/        # 游戏实体
│   ├── plant.py     # 植物基类 + 各植物
│   ├── zombie.py    # 僵尸基类 + 各僵尸
│   └── bullet.py    # 子弹系统
├── systems/         # 游戏系统
│   ├── combat.py    # 战斗/碰撞
│   ├── economy.py   # 阳光经济
│   ├── wave.py      # 波次生成
│   └── grid.py      # 网格管理
├── scenes/          # 场景
│   ├── menu.py      # 主菜单
│   ├── level_select.py
│   └── gameplay.py  # 游戏主场景
├── data/            # 关卡数据
│   └── levels/      # JSON 关卡定义
└── config.py        # 全局配置
```

## 👥 开发团队 (AI Agents)

| 角色 | 职责 |
|------|------|
| 🎯 项目经理 | 排期、Issue管理、进度追踪、评审 |
| 🔧 引擎工程师 | 核心框架、渲染管线、性能优化 |
| 🎮 玩法工程师 | 植物/僵尸行为、战斗系统、经济平衡 |
| 🗺️ 关卡设计师 | 关卡波次设计、难度曲线、玩法创新 |
| 🧪 QA工程师 | 自动化测试、手动验收、Bug报告 |
