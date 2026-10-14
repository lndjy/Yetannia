# 耶坦尼娅 Yetannia —《杀戮尖塔 2》角色 Mod

为《杀戮尖塔 2》加入《千年之旅：ELF》的角色 **耶坦尼娅**：**82 张卡**、关键词**「先知」**、
专属遗物、**中/日双语语音**（游戏内可切/可关），以及**逐帧动画**的战斗·营火·商人形象。

- 创意工坊（订阅即装）：<https://steamcommunity.com/sharedfiles/filedetails/?id=3819506337>
- 源码仓库：<https://github.com/lndjy/Yetannia>
- 开发文档 / 项目历史：[`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- 当前版本：**v1.0.0**（以 `Yetannia/Yetannia.json` 为准）

> ### ⚠️ 只支持 beta 分支 · BETA BRANCH ONLY
>
> 本 Mod 只在《杀戮尖塔 2》的 **beta 分支**上开发与测试；创意工坊条目本身也锁定了 beta
> （`workshop.json` 里 `minBranch` / `maxBranch` 都是 `public-beta`）。
> **正式分支（非 beta）不保证能加载**——可能出现角色不出现、卡图丢失、事件对话报错等问题。
> 请先在 Steam 里把游戏切到 beta 分支再使用。

## English summary

Yetannia is a fan-made character mod for *Slay the Spire 2* — **beta branch only**.
Requirements: the game's **beta branch**, game **≥ 0.107.0**, and **BaseLib ≥ 3.4.7**
(Steam Workshop). It adds the character Yetannia (70 HP), **82 cards**, the **Prophet**
keyword (triggers when a card moves from your draw pile to your discard pile — *not* when
discarded from hand), the starting relic **Prophet's Hair Ornament** (Scry 5) and its Orobas
replacement **Prophet's Crown** (Scry 10), **11 voiced moments** with an in-game
**Voice language = 中文 / 日本語 / Off** setting (Off silences only her lines and never touches
the base game's audio), **per-Ancient dialogue for nine Ancients**, and animated (frame-by-frame)
combat / campfire / merchant figures. The card list, install steps and build notes below are in
Chinese; this project reports problems on the Workshop page.

## 环境要求

| | 要求 | 为什么 |
|---|---|---|
| 游戏 | 《杀戮尖塔 2》**≥ 0.107.0**，且**必须是 beta 分支** | Mod 清单里 `min_game_version` 是 `0.107.0`；创意工坊条目锁定 `public-beta` |
| 前置 Mod | **BaseLib ≥ 3.4.7**（创意工坊订阅） | 没有它本 Mod 不会加载，日志里也不会有任何 `[Yetannia]` 字样 |
| 启动方式 | **必须从 Steam 启动游戏** | 直接双击 exe 启动会 Steam 初始化失败 |
| 安装之后 | 在游戏内 Mod 列表里**手动启用一次** | 游戏会把新装的 Mod 默认设成禁用，不启用永远不会加载 |

## 安装

### 方式一：创意工坊（推荐）

1. 订阅 **BaseLib**（创意工坊里搜 `BaseLib`，作者 **Alchyr**；也在
   [GitHub 发版](https://github.com/Alchyr/BaseLib-StS2/releases)）。**版本要 ≥ 3.4.7**——
   它是前置，版本不够本 Mod 不会加载。
2. 订阅 **[耶坦尼娅 Yetannia](https://steamcommunity.com/sharedfiles/filedetails/?id=3819506337)**。
3. 在 Steam 里把《杀戮尖塔 2》切到 **beta 分支**，然后**从 Steam 启动**游戏。
4. 进主菜单 → **Mod 列表**，确认 BaseLib 和 Yetannia 都是「启用」。
5. 重启游戏。选人界面就会出现「耶坦尼娅」，**角色不需要解锁**，装上就能选。

### 方式二：手动安装（压缩包 / 自己打包）

1. 先订阅 BaseLib（同上）。
2. 把压缩包里的 `Yetannia` 文件夹整个解压到：

   ```
   <Steam>\steamapps\common\Slay the Spire 2\mods\
   ```

   解压完的层级应该是：

   ```
   ...\Slay the Spire 2\mods\Yetannia\Yetannia.dll
   ...\Slay the Spire 2\mods\Yetannia\Yetannia.json
   ...\Slay the Spire 2\mods\Yetannia\Yetannia.pck
   ```

3. 从 Steam 启动游戏 → 在 Mod 列表里启用 Yetannia → 重启。

> **第 3 步别跳过。** 游戏会把「尚未在设置里启用」的 Mod 记为 `is_enabled: false` 并跳过加载，
> 日志里是 `Skipping loading mod Yetannia, it is set to disabled in settings`。
> 这也正是「Mod 突然不生效了」最常见的原因：先去 Mod 列表看一眼。

## 这个 Mod 加了什么

### 角色

- 生命上限 **70**。
- 初始牌组 **10 张：4×打击 + 4×防御 + 回避 + 试探**。
- 卡框紫色，能量球 / 地图头像 / 选人立绘都是自制资源。

### 82 张卡

| 维度 | 明细 |
|---|---|
| 合计 | **82 张**（另有 1 张已删除的存档记录，不列入下面的卡牌总览） |
| 按稀有度 | 基础 4 / 先古 2 / 白 18 / 蓝 32 / 金 24 / 状态 2 |
| 按类型 | 攻击 26 / 技能 37 / 能力 17 / 状态 2 |
| 联机专属 | **6 张**：先知的指引、归途终尽之景、身先士卒、先知的援助、回应愿景之心、天之恩典 |
| 单机 | **76 张**（82 − 6） |

- 那 6 张联机专属牌用的是游戏自带的 `CardMultiplayerConstraint.MultiplayerOnly`，
  所以**单人局里它们不会出现在任何牌池、奖励或商店**，不需要你手动回避。
  反过来，其余 76 张单机牌在联机下也能正常使用。
- **全部 82 张卡都有自己的卡面**（`images/card_portraits/<卡 id>.png`）：两张先古卡
  （合击 / 引领之光）是 608×856 的竖幅大图，其余 80 张是 500×380，没有一张还在用占位图。
- 82 张的完整清单见下面「[卡牌总览](#卡牌总览)」，那张表由源码生成，不会和代码脱节。

### 关键词：先知

> 当此牌**从抽牌堆进入弃牌堆**时，触发本牌的先知效果。
> **从手牌被弃置不会触发**——这是词条本来的要求。

- 带「重放」的牌被弃置触发时会触发同样次数；能力牌触发后和打出一样离开本场战斗
  （即「等效打出」，不会出现「效果发动了、牌还在，能再抽回来打一次」）。
- 先知效果里不询问玩家做选择（换堆不是玩家操作，没有真正的选择上下文）。

### 遗物

- 初始遗物 **先知发饰**：战斗开始时，**预见 5**。
- 欧洛巴斯（Orobas）路线的替换先古遗物 **先知头冠**：战斗开始时，**预见 10**。
- 其余遗物还有玛瑙的药水腰带、先知的手链，以及占位名的「未命名·预见」。

### 语音（11 处）+ 游戏内设置

- **11 处语音**：攻击、技能、受到致命伤、选人、开局、战斗开始、卡牌奖励、营火、商店、事件、遗物。
- 游戏设置里会多出一项 **语音语言**，可选 **中文 / 日语 / 关闭**（默认为日语）。
- **「关闭」只让耶坦尼娅不出声，不会动游戏原版的任何音效。**

### 九位先古之民的专属对话

涅奥 / 欧洛巴斯 / 佩尔 / 瓦库 / 坦克斯 / 特兹卡塔拉 / 诺奴佩普 / 达弗 / 建筑师 ——
九位先古各有一套按访问次数推进的专属对话。

### 美术

- **战斗形象、营火、商人三处都是「会动的角色」**：从模型渲染出来的**逐帧动画**，不是静态立绘。
- 选人立绘（含未解锁时的剪影）、遗物图标、卡面上的费用图标、左下角能量球与能量文字图标、
  地图头像都是自制资源，不沿用原版。

## 语音语言怎么设置

1. 主菜单 → **设置（Settings）** → 找到 **语音 Voice** 分组下的 **语音语言**。
2. 选择 **中文** / **日语** / **关闭**。
3. 「关闭」只影响耶坦尼娅的台词，**不影响原版音效**；随时可以再打开。

## 反馈问题

- 日志文件：`%APPDATA%\SlayTheSpire2\logs\godot.log`
  里面所有 `[Yetannia]` 开头的行都有用，尤其是几十行 `self-check`——它们会直接说明 Mod
  有没有加载成功、82 张卡有没有注册上、卡面有没有加载。
- 出问题的**卡名 + 当时场面**（几个敌人、手上有什么、之前触发过几次先知）。
- 如果是「预见」类卡牌卡住（牌停在屏幕中间不结算），请一并提供日志里的 `[scry]` 行。
- 反馈渠道：创意工坊留言 <https://steamcommunity.com/sharedfiles/filedetails/?id=3819506337>，
  或在 <https://github.com/lndjy/Yetannia/issues> 开 issue。

## 当前完成度与已知问题（说实话）

- **9 处名字还是占位名，但都不是卡名**：8 个能力名
  （未命名·从容 / 未命名·倍增 / 未命名·共感 / 未命名·净化 / 未命名·焚灭 / 未命名·续行 /
  未命名·观照 / 未命名·解放）和 1 个遗物名（未命名·预见）。
  **82 张卡的名字全部是正式名，卡名占位 0 个。**
- 全部 82 张卡都有自己的卡面；遗物图标、费用图标、能量球、能量文字图标、地图头像均已自制。
- 「预见」本身不是可悬停的关键词，只有「引领之光」挂了 `BaseLibTip.Scry` 的悬停提示。
- 联机（多人）逻辑是按原版实现与 API 契约写的，还没有真正跑过双人局实测。

## 从源码构建（开发者向）

这是一个**源码仓库**，不是只有成品。构建需要：

1. **.NET 9 SDK** —— `Yetannia/Yetannia.csproj` 是普通 `net9.0` 类库（刻意不用 `Godot.NET.Sdk`，
   因为 .NET 侧没有 Godot 场景和 C# 源码生成器）。
2. **Godot 4.5.1** —— 只用来导出美术包（`.tools/export-pck.ps1` 调用
   `.tools/godot/Godot_v4.5.1-stable_win64_console.exe`）。
3. **游戏本体（beta 分支）** —— 编译要引用游戏自己的程序集。`Yetannia/Sts2PathDiscovery.props`
   会自动在常见安装位置找 Slay the Spire 2，找不到时显式指定：

   ```
   dotnet build -p:Sts2Path="D:\path\to\Slay the Spire 2"
   ```

   它会引用 `data_sts2_windows_x86_64` 下的 `sts2.dll` / `GodotSharp.dll` / `0Harmony.dll`。
4. **BaseLib 3.4.7 的 NuGet 包**（`Alchyr.Sts2.BaseLib`，编译期只用到它的 API 面）。

两个脚本：

| 脚本 | 作用 |
|---|---|
| `.tools/export-pck.ps1` | 把 `.tools/pckproject/` 里的美术导入并导出成 `Yetannia/build/Yetannia.pck`。**改了任何美术之后必须重跑**，否则游戏里还是旧图 |
| `.tools/package-mod.ps1` | 构建 Release + 刷新卡牌表 + 暂存 + 打成可以直接解压进 `mods\` 的 zip |

`.tools/pckproject/` 是一个**只有美术、没有任何 C# 的 Godot 工程**（`project.godot` +
`images/` + `scenes/` + `materials/` + `audio/`）。它存在的意义就是当导出源：
`.dll` 由 .NET 构建，`.pck` 由这个工程导出，两边互不干扰。里面还有个坑值得知道：
`project.godot` 里设了 `export/convert_text_resources_to_binary=false`，否则 Godot 会把
`.tscn` 转成二进制 + `.remap`，导致运行时 `scene.ResourcePath` 与注册的
`res://Yetannia/scenes/...` 对不上，BaseLib 的场景转换会**静默失效**。

**从零克隆能做什么、不能做什么（如实说）：**

- 能：构建出 `Yetannia.dll`；用 `.tools/pckproject/` 里已入库的全部卡面 / 立绘 / 场景
  导出 `.pck`；打包成 zip。
- **不能一步到位：语音音频是刻意不入库的**（`.gitignore` 忽略
  `.tools/pckproject/Yetannia/audio/voice/` 和 `*.ogg`，因为语音素材来自原游戏、有版权顾虑）。
  所以**从源码构建出来的 Mod 是没有语音的**：设置里的「语音语言」还在，但不会出声，
  只会在日志里留下一行 `[voice] missing audio file, playing nothing: ...` 警告
  （这是设计好的降级路径，不报错、不会卡住游戏）。想要语音请用创意工坊版本或发行 zip。
- 便携工具链也不入库：`.tools/dotnet/`（.NET 9 SDK）、`.tools/godot/`（Godot 4.5.1）、
  `.tools/src/` 都被忽略，需要自己装。
- `Yetannia/nuget.config` 目前指向本项目构建环境里的本地 NuGet 代理
  （`.tools/nuget-proxy.js` 起在 `127.0.0.1:8899`）。换环境构建时要么起这个代理，
  要么把它改成 `https://api.nuget.org/v3/index.json`。
- `.tools/cards-xlsx.js` 会同时生成 `Yetannia-卡牌表.xlsx`（**该 xlsx 不入库**，按需本地生成）
  和 README 里那段卡表；`package-mod.ps1` 每次打包都会跑它，所以卡表不会掉队。

## 联机

- 6 张联机专属牌见上面「82 张卡」；它们靠游戏自带的 `CardMultiplayerConstraint` 自动从单人牌池里筛掉。
- ⚠️ **联机时所有玩家必须装同一套 Mod 且版本一致**：游戏会比对双方的 Mod 列表，
  不一致会直接拦下来；BaseLib 同理。
- 联机逻辑尚未经过双人局实测（见「当前完成度」）。

## 致谢与声明

- 角色、立绘与语音素材来自游戏 **《千年之旅：ELF》**（[角色页](https://wiki.biligame.com/elf/%E8%80%B6%E5%9D%A6%E5%B0%BC%E5%A8%85)）。
- 本 Mod 是**同人作品（fan work）**，与 MegaCrit（《杀戮尖塔 2》的开发商）以及
  《千年之旅：ELF》的官方均无关联；相关素材版权归各自权利人所有。
- **如有异议请联系我下架（takedown on request）。**
- 前置依赖 **BaseLib** 由 [Alchyr](https://github.com/Alchyr/BaseLib-StS2) 开发。

## 卡牌总览

> 本节表格**由 `.tools/cards-xlsx.js` 从源码生成**（`package-mod.ps1` 每次打包都会自动刷新），
> **请勿手改**——它是这份 README 里唯一由脚本维护的部分，改了下次打包就会被覆盖。
> 表格的列是：卡名 `类名` / 费用 / 类型 / 效果（`敲后：` 是升级后的变化）。
> 表下还会列出已删除的存档记录。想按稀有度/类型看统计，见上面「82 张卡」一节。

<!-- BEGIN CARD TABLE (generated by .tools/cards-xlsx.js - do not edit by hand) -->
**共 82 张。**

**基础（Basic），4 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 打击 `YetanniaStrike` | 1 | 攻击 | 造成 6 点伤害。<br>敲后：伤害 6→9。 |
| 防御 `YetanniaDefend` | 1 | 技能 | 获得 5 点格挡。<br>敲后：格挡 5→8。 |
| 回避 `ForesightWard` | 0 | 技能 | 获得 3 点格挡。 先知：获得 4 点格挡。<br>敲后：格挡 3→4；先知格挡 4→6。 |
| 试探 `OminousDecree` | 1 | 攻击 | 对所有敌人造成 6 点伤害，并给予所有敌人 1 层易伤和 1 层虚弱。 先知：没有额外描述，效果与打出相同。<br>敲后：费用 1→0；伤害与层数不变。 |

**先古（Ancient），2 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 合击 `OminousDecreeTranscendent` | 1 | 攻击 | 给予所有敌人 2 层易伤和 2 层虚弱，并造成 15 点伤害。 先知：效果与打出相同。<br>敲后：费用 1→0，伤害 15→20。 （走「古老之牙」路线时替换初始卡「试探」） |
| 引领之光 `DarvsProphecy` | 3 | 技能 | 固有。预见你的抽牌堆。消耗。<br>敲后：费用 3→2。 （来自达弗的「陈旧的书卷」） |

**白（Common），18 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 挥舞 `GlimpseFate` | 0 | 技能 | 预见 1。抽 1 张牌。<br>敲后：预见 1→2。 |
| 高举旗帜 `Divination` | 1 | 技能 | 预见 3。抽 2 张牌。<br>敲后：预见 3→4。 |
| 横扫 `PropheticCleave` | 1 | 攻击 | 对所有敌人造成 10 点伤害。 先知。<br>敲后：伤害 10→14。 |
| 后撤 `WardOfForesight` | 2 | 技能 | 获得 7 点格挡。 先知。<br>敲后：格挡 7→10。 |
| 先制 `CutThroughFate` | 1 | 攻击 | 造成 7 点伤害。预见 2。抽 1 张牌。<br>敲后：伤害 7→9，预见 2→3。 |
| 修顿 `ThirdEye` | 1 | 技能 | 获得 7 点格挡。预见 3。<br>敲后：格挡 7→9，预见 3→5。 |
| 预备 `RearrangedFate` | 0 | 技能 | 将任意数量的手牌放到抽牌堆顶。消耗、保留。<br>敲后：去掉消耗。 |
| 奋不顾身 `RecklessCharge` | 0 | 攻击 | 造成 11 点伤害。将一张眩晕加入你的弃牌堆。<br>敲后：伤害 11→15。 |
| 伺机而动 `WaitForTheMoment` | 2 | 攻击 | 造成 12 点伤害。如果你在本回合内预见过牌，获得 2 点能量。<br>敲后：伤害 12→16。 |
| 斩铁波 `IronWave` | 0 | 攻击 | 造成 4 点伤害，获得 3 点格挡。<br>敲后：伤害 4→5，格挡 3→5。 |
| 交叉防御 `TwinBulwark` | 1 | 技能 | 获得 5 点格挡，2 次。<br>敲后：格挡 5→7。 |
| 水色之舞 `CounterStrike` | 0 | 攻击 | 造成 11 点伤害。 只有当敌人的意图是攻击时才能打出。<br>敲后：伤害 11→15。 |
| 众志成城 `PatientBulwark` | 4 | 技能 | 获得 18 点格挡。 你每抽到一次这张牌，这张牌的耗能-1。<br>敲后：费用 4→3。 |
| 霜色华斩 `PatientStrike` | 4 | 攻击 | 造成 26 点伤害。 你每抽到一次这张牌，这张牌的耗能-1。<br>敲后：费用 4→3。 |
| 风中笑颜 `ReinforceStatus` | 1 | 攻击 | 造成 11 点伤害，将一张幻想纯爱加入你的手牌。<br>敲后：伤害 11→15。 |
| 火中白花 `SupplyStatus` | 1 | 技能 | 获得 10 点格挡，将一张纯爱幻想加入你的手牌。<br>敲后：格挡 10→13。 |
| 常备不懈 `ShuffleStatus` | 0 | 攻击 | 造成 7 点伤害，随机将一张纯爱幻想或幻想纯爱放入你的抽牌堆。<br>敲后：伤害 7→10。 |
| 天之恩典 `SharedRegen` | 0 | 技能 | 所有玩家获得 2 点再生。消耗。<br>敲后：再生 2→3。 ※ 联机专属。 |

**蓝（Uncommon），32 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 先知打击 `BuildingMomentum` | 1 | 攻击 | 造成 6 点伤害。你每拥有 1 张先知牌，此牌额外造成 2 点伤害。 先知。<br>敲后：伤害 6→9，每张增量 2→3。 |
| 白刃乱舞 `FlurryStrike` | 1 | 攻击 | 造成 3 点伤害 X 次。X 为本回合此前打出的牌数。<br>敲后：伤害 3→4。 |
| 按部就班 `BalancedInsight` | 3 | 能力 | 获得 1 点力量与 1 点敏捷。 先知。<br>敲后：力量 1→2，敏捷 1→2。 |
| 厚积薄发 `AccumulatedFate` | 1 | 攻击 | 对所有敌人造成 6 点伤害。本场战斗中每触发过一次先知效果，此牌伤害 +3。（卡面另显示本场已触发先知次数） 先知。<br>敲后：伤害 6→9，每次增量 +3→+4。 |
| 引蛇出洞 `UnplayedOmen` | 0 | 技能 | 不能被打出。 先知：抽 2 张牌。<br>敲后：抽牌 2→3。 |
| 蓄势待发 `LatentPower` | 0 | 技能 | 不能被打出。 先知：获得 1 点能量。<br>敲后：能量 1→2。 |
| 抉择 `PurifyingVision` | 1 | 技能 | 预见 2。消耗因此被弃置的牌。抽 2 张牌。<br>敲后：抽牌 2→3。 |
| 有条不紊 `Foresight` | 1 | 能力 | 在你的回合开始时（抽 5 张之前），预见 3。<br>敲后：预见 3→4。 |
| 步步为营 `Nirvana` | 1 | 能力 | 每当你预见时，获得 3 点格挡。<br>敲后：格挡 3→4。 |
| 回马枪 `Weave` | 0 | 攻击 | 造成 4 点伤害。每当你预见时，将此牌从弃牌堆移回你的手牌。<br>敲后：伤害 4→6。 |
| 运筹帷幄 `TestSkill` | 0 | 技能 | 将你的所有手牌置于抽牌堆顶，预见 8，然后抽取等量的牌。 消耗。<br>敲后：预见 8→10。 |
| 制敌机先 `SeizeTheInitiative` | 1 | 攻击 | 造成 9 点伤害。如果目标敌人的意图是攻击，给予其 2 层虚弱。<br>敲后：伤害 9→12。 |
| 奇袭 `Ambush` | 1 | 技能 | 给予 2 层易伤，获得 1 点力量。如果目标敌人的意图不是攻击，则获得的力量翻倍。<br>敲后：易伤 2→3，力量 1→2。 |
| 先见之明 `Prescience` | 0 | 技能 | 固有。预见 3，抽 2 张牌。消耗。<br>敲后：预见 3→4，抽牌 2→3。 |
| 韬光养晦 `BideTime` | 1 | 技能 | 在本回合保留你的手牌。将手牌中任意数量的牌置于抽牌堆顶。下回合获得 1 点能量。<br>敲后：下回合能量 1→2。 |
| 水色睿智 `DelayedEcho` | 0 | 技能 | 获得 2 点能量。本回合结束时，将这张牌的一张复制加入你的弃牌堆。 消耗。<br>敲后：能量 2→3。 |
| 藏器待时 `ScryMight` | 1 | 能力 | 打出后每累计预见 6 张牌，获得 1 点力量。<br>敲后：阈值 6→4。 |
| 后发先制 `ScryAgility` | 1 | 能力 | 打出后每累计预见 7 张牌，获得 1 点敏捷。<br>敲后：阈值 7→5。 |
| 挺身而出 `UnnamedTechnique` | 2 | 技能 | 获得 16 点格挡。给予自己 1 层虚弱。下回合获得 1 点能量。<br>敲后：下回合能量 1→2（格挡与虚弱不变）。 |
| 能量调和 `Equilibrium` | 1 | 技能 | 如果本回合你打出的先知牌数和非先知牌数相等，从抽牌堆检索先知牌和非先知牌各一张加入手牌。 （当前先知牌 a 张，非先知牌 b 张） 保留、消耗。<br>敲后：费用 1→0。 |
| 现场休整 `Reclaim` | 1 | 技能 | 将弃牌堆中至多 2 张牌放到抽牌堆顶。<br>敲后：获得保留。 |
| 严阵以待 `ForecastBulwark` | X | 技能 | 获得 7X 点格挡。下个回合开始时预见 X。<br>敲后：格挡 7X→9X。 |
| 命定的抗争 `GrowingStrike` | 2 | 攻击 | 造成 18 点伤害。虚无。 当这张牌被消耗时，本局游戏中它的伤害永久+2。<br>敲后：伤害 18→26。 |
| 银铃响起之时 `RisingMight` | 1 | 技能 | 获得 3 点临时力量。如果本回合已经打出超过 2 张攻击牌，改为永久获得，并且下回合额外抽 2 张牌。<br>敲后：力量 3→4。 |
| 临危不乱 `SteadyAgility` | 1 | 技能 | 获得 2 点临时敏捷。如果本回合未受到过伤害，改为永久获得，并且下回合额外获得 2 点能量。<br>敲后：敏捷 2→3。 |
| 趁势而动 `PurifyStatus` | 1 | 能力 | 每回合你抽到状态牌的前 1 次，将它消耗。<br>敲后：前 2 次。 |
| 破釜沉舟 `DetonateStatus` | 2 | 攻击 | 消耗你手中全部状态牌，造成 16 点伤害。<br>敲后：伤害 16→22。 |
| 少女幻想之忆 `TransmuteStatus` | 1 | 技能 | 将你抽牌堆、手牌、弃牌堆的所有状态牌随机变为纯爱幻想或幻想纯爱。消耗。<br>敲后：去掉消耗。 |
| 冰刃连斩 `ExhaustBlast` | 1 | 能力 | 每当你消耗一张牌，对所有敌人造成 3 点伤害。<br>敲后：伤害 3→4。 |
| 身先士卒 `SharedFocus` | 1 | 能力 | 所有玩家获得 1 点敏捷。<br>敲后：费用 1→0。 ※ 联机专属。 |
| 先知的援助 `GiftOfTime` | 3 | 技能 | 选择一名其他角色。该角色本回合结束时，获得一个额外回合。 结束你的回合。 消耗。<br>敲后：费用 3→2。 ※ 联机专属。 |
| 回应愿景之心 `SharedMight` | 1 | 能力 | 选择一名队友。本场战斗中，当你获得力量和敏捷时（不因此牌），其获得等量力量和敏捷。<br>敲后：固有。 ※ 联机专属。 |

**金（Rare），24 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 未雨绸缪 `PropheticStudy` | 2 | 能力 | 每当你预见时，抽 1 张牌。<br>敲后：费用 2→1。 |
| 积厚成势 `FatedVitality` | 1 | 技能 | 打出时，获得卡面上显示的数字点生命上限（基础 2）。 先知：只把卡面数字抬高 2（不给血上限），本场最多累计到 8。 消耗。<br>敲后：基础 2→3；先知增量 +2→+3，上限 8→12。 |
| 殚精竭虑 `CycleOfProphecy` | 0 | 能力 | 获得 2 点能量。预见 2。抽 2 张牌。 下个回合开始时，将一张眩晕加入你的弃牌堆。<br>敲后：能量 2→3，预见 2→3，抽牌 2→3。 |
| 背水一战 `GrandProphecy` | 2 | 技能 | 预见 6。消耗因此被弃置的牌，并触发它们的先知效果。抽取剩下的牌。<br>敲后：预见 6→8。 |
| 请君入瓮 `TestAttack` | 1 | 攻击 | 造成 12 点伤害。 先知：对随机目标打出此牌，然后此牌伤害翻倍。<br>敲后：伤害 12→16。 |
| 重整旗鼓 `Regroup` | 1 | 技能 | 消耗你抽牌堆、弃牌堆和手牌中的所有状态牌。<br>敲后：费用 1→0。 |
| 全力进攻 `AllOutAttack` | 1 | 技能 | 你手牌中所有牌的耗能降低 1 点，直到它被打出。<br>敲后：这张牌自己的费用 1→0。 |
| 冰刃轮舞 `ShuffleReplay` | 2 | 攻击 | 对所有敌人造成 5 点伤害，4 次。 本场战斗中你每洗牌一次，这张牌获得重放 1。<br>敲后：次数 4→5。 |
| 因果切断 `FatalInsight` | 2 | 攻击 | 造成 13 点伤害。如果击杀目标，永久升级你打出的上一张牌。 消耗。<br>敲后：伤害 13→16。 |
| 夹击之势 `EmpoweredVolley` | X | 攻击 | 重复 X 次：获得 1 点力量，对随机敌人造成 10 点伤害。<br>敲后：伤害 10→14。 |
| 星光破晓之刻 `Judgement` | 1 | 能力 | 拥有易伤的敌人受到的伤害增加 25%。拥有虚弱的敌人造成的伤害减少 15%。<br>敲后：固有。 |
| 纯爱药丸 `PureLovePill` | 1 | 技能 | 获得 10 点格挡，获得 1 层人工制品。消耗。<br>敲后：格挡 10→14。 |
| 纯爱形态 `PureLoveForm` | 2 | 能力 | 本场战斗中，当你从抽牌堆弃置非先知牌时，使其费用变为 0，直到你下次打出它。<br>敲后：费用 2→1。 |
| 长驱直入 `Settlement` | 1 | 攻击 | 对所有敌人造成 11 点伤害。敌人身上每有一种负面状态，伤害+4。<br>敲后：伤害 11→15，加成 4→5。 |
| 她眼中的世界 `Insight` | 2 | 能力 | 每回合第一次打出攻击牌时，获得 1 点能量；第一次打出技能牌时，抽 1 张牌；第一次打出能力牌时，预见 2。 虚无。<br>敲后：去掉虚无。 |
| 剑之所指 `FreeStatus` | 1 | 能力 | 你可以免费打出你的纯爱幻想和幻想纯爱。<br>敲后：固有。 |
| 心之所向 `DoubleStatus` | 1 | 能力 | 你的纯爱幻想和幻想纯爱造成的伤害、获得的格挡翻倍。<br>敲后：固有。 |
| 纵冰横霜 `MassStrikeStrike` | 1 | 攻击 | 造成 18 点伤害，将两张纯爱幻想加入你的手牌。<br>敲后：伤害 18→23。 |
| 凛冽冰轮 `MassDefendDefend` | 2 | 攻击 | 对全体敌人造成 21 点伤害，将两张幻想纯爱加入你的弃牌堆。<br>敲后：伤害 21→28。 |
| 凯旋之路 `StatusDraw` | 2 | 能力 | 当你消耗一张状态牌时，抽一张牌。<br>敲后：费用 2→1。 |
| 先知的指引 `GuidanceOfTheProphet` | 1 | 技能 | 从三张随机能力牌中选择一张加入手牌，本回合免费打出。 将此牌放入随机一名队友的弃牌堆。<br>敲后：那三张能力牌是已升级的。 ※ 联机专属。 |
| 归途终尽之景 `EmberBoon` | 1 | 技能 | 选择一名队友。本场战斗中，该角色每消耗一张牌，随机生成一张牌加入其手牌。此效果不可叠加。 消耗。<br>敲后：生成的是已升级的牌。 ※ 联机专属。 |
| 回溯 `Retrospect` | X | 技能 | 随机打出你弃牌堆的 X 张牌。<br>敲后：X → X+1。 ※ 写法对齐原版「倾泻」(Cascade)。 |
| 星痕化 `StarscarForm` | 2 | 技能 | 下个回合，获得 1 层无实体。消耗。<br>敲后：费用 2→1。 |

**状态（Status），2 张**

| 卡 | 费 | 类型 | 效果 |
|---|---|---|---|
| 纯爱幻想 `StrikeStrike` | 1 | 状态 | 当此牌被消耗时，对随机敌人造成 6 点伤害。消耗。 |
| 幻想纯爱 `DefendDefend` | 1 | 状态 | 当此牌被消耗时，获得 4 点格挡。消耗。 |

> 不列入上表的记录项（已删除，仅作存档）：试探打击（已删除）。
<!-- END CARD TABLE -->

## 开发文档与历史

- 面向开发者的构建、踩坑、内部机制笔记，以及**项目历史（原 README 的全文）**：
  [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。
  那份文件里的数字是写下当时的状态，不代表当前版本；当前数值以本文与代码为准。
- 卡表生成脚本：`.tools/cards-xlsx.js`；打包脚本：`.tools/package-mod.ps1`。
