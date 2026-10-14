#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruct the pre-edit README.md by reverse-applying the recorded edits, then diff both files."""
import io, os, hashlib, difflib

ROOT = r"D:\桌面\sts2mod"
out = io.StringIO()
def w(s=""): out.write(s + "\n")

# --- mod-readme.txt: the true "before" is QA's archived dump of the shipped README.txt ---
before_help_p = os.path.join(ROOT, ".tools", "qa", "rt47-dump-README.txt.txt")
after_help_p = os.path.join(ROOT, ".tools", "mod-readme.txt")
before_help = open(before_help_p, "rb").read()
after_help = open(after_help_p, "rb").read()
w("mod-readme.txt before: %d B %s  (source: .tools/qa/rt47-dump-README.txt.txt)" % (
    len(before_help), hashlib.sha256(before_help).hexdigest().upper()))
w("mod-readme.txt after : %d B %s" % (len(after_help), hashlib.sha256(after_help).hexdigest().upper()))

# --- README.md: reverse-apply the edits (new -> old), then prove the reconstruction by hash ---
cur = open(os.path.join(ROOT, "README.md"), "rb").read().decode("utf-8")
EDITS = []
def E(old, new):
    EDITS.append((old, new))

E(
"""Mod 内建的自检（`Code/ModSelfCheck.cs`）在 `ModelDb` 构建完成后核对注册结果，最近一次运行输出：""",
"""Mod 内建的自检（`Code/ModSelfCheck.cs`）在 `ModelDb` 构建完成后核对注册结果。

> \u26a0\ufe0f 下面是**早期版本**（39 张卡时期）的一次运行输出，**格式和数字都已过时**，留在这里只是
> 为了让自检的**格式**有个参照。当前实测到的是
> `self-check card pool : 82 card(s)`、`self-check relic pool : 5 relic(s)`、
> `self-check portrait ok : 82/82`、`self-check art : selectIcon=528x780 locked=132x195 hud=88x88`
> （QA 第 47 轮，见 `.tools/qa/QA-RETEST47.md` \u00a7\u2461）。卡数明细见下面「卡牌总览」一节。""")

E(
"""│     ├─ Cards\\                  卡牌基类（含先知触发、卡面分配）+ 51 张卡
│     ├─ Powers\\                 8 个能力
│     ├─ Keywords\\               先知关键词 + 本地化注入
│     └─ Relics\\                 遗物基类 + 先知发饰 / 先知头冠""",
"""│     ├─ Cards\\                  卡牌基类（含先知触发、卡面分配）+ 82 张卡
│     ├─ Powers\\                 能力（22 个具名能力 + 3 个支撑类）
│     ├─ Keywords\\               先知关键词 + 本地化注入
│     └─ Relics\\                 遗物基类 + 5 个遗物""")

E(
"""   │     ├─ images\\card_portraits\\test.png    白/蓝卡卡面
   │     ├─ images\\card_portraits\\test2.png   金卡卡面""",
"""   │     ├─ images\\card_portraits\\            82 张卡各一张卡面（+ test/test2/blank 兜底）""")

E(
"""> **当前策略：卡面用自制图（按稀有度分配），角色场景也用自制贴图。**
> 白/蓝卡用 `card_portraits/test.png`，金卡用 `card_portraits/test2.png`；
> 选人界面大图 / 战斗形象 / 休息处 / 商人 / 选人背景都用之前那套耶坦尼娅贴图（桌面壁纸抽帧）。
> 唯一还没换的是**卡图之外**的基础游戏占位（遗物图标 `burning_blood`、能量配色、
> 地图头像），见「占位与后续」。""",
"""> **当前策略：每张卡都有自己的卡面，角色形象是从模型渲染出来的逐帧动画。**
> 82 张卡各有一张 `card_portraits/<卡 id>.png`（两张先古卡是 608×856，其余 500×380）；
> `test.png` / `test2.png` / `blank.png` 只是「卡面无图」时的兜底，现在没有任何一张卡会用到它们。
> 选人立绘 / 顶栏头像 / 选人背景是自制贴图（桌面壁纸抽帧）；战斗形象 / 休息处 / 商人
> 是自制场景，播的是同一张模型图集 `images/creature/yetannia_atlas_0.png` 的逐帧动画。
> 遗物图标、费用 / 能量图标、地图头像现在也都是自制的，见「占位与后续」。""")

E(
"""| `card_portraits/test.png` | 500x380 | 白卡 / 蓝卡（以及基础、先古）的 `YetanniaCard.CustomPortraitPath` |
| `card_portraits/test2.png` | 500x380 | 金卡（`CardRarity.Rare`）的卡面 |

**卡面的正确比例是 250x190（≈1.316），不是随手定的**：游戏的卡牌场景
`scenes/cards/card.tscn` 里 `Portrait` 节点的偏移是 `-125..125` × `-168..22`，
并且 `stretch_mode = 5`（`KEEP_ASPECT_COVERED`）——也就是**等比放大到铺满、超出部分居中裁掉**。
所以源图只要不是 1.316，引擎就会自己裁；为了让 pck 小一点、也为了让「引擎里看到的」和
「我裁出来的」完全一致，导入前先按 1.316 居中裁剪再缩到 500x380：

```
test.png   752x992   -> 裁 752x572  @ (0,210)    -> 500x380
test2.png  1728x1080 -> 裁 1421x1080 @ (154,0)   -> 500x380
```

改图之后**必须重跑 `export-pck.ps1`**，否则游戏里还是旧的。""",
"""| `card_portraits/<卡 id>.png` | 500x380 | 每张卡自己的卡面（82 张各一张，`YetanniaCard.CustomPortraitPath`） |
| `card_portraits/darvs_prophecy.png`、`card_portraits/ominous_decree_transcendent.png` | 608x856 | 两张先古卡的竖幅卡面（槽位也更大） |
| `card_portraits/test.png`、`test2.png`、`blank.png` | 500x380 | 兜底占位图，当前没有任何卡用到 |

**普通卡面的正确比例是 250x190（≈1.316），不是随手定的**：游戏的卡牌场景
`scenes/cards/card.tscn` 里 `Portrait` 节点的偏移是 `-125..125` × `-168..22`，
并且 `stretch_mode = 5`（`KEEP_ASPECT_COVERED`）——也就是**等比放大到铺满、超出部分居中裁掉**。
所以源图只要不是 1.316，引擎就会自己裁；为了让 pck 小一点、也为了让「引擎里看到的」和
「我裁出来的」完全一致，导入前先按 1.316 居中裁剪再缩到 500x380：

```
每张普通卡面  <任意尺寸>  -> 按 ≈1.316 居中裁剪  -> 500x380
```

两张先古卡用的是**另一个槽位**（598x842，≈0.710），所以它们的图是 608x856 的竖幅，
和普通卡不是一套比例——这不是 bug。

改图之后**必须重跑 `export-pck.ps1`**，否则游戏里还是旧的。""")

E(
"""产出 `Yetannia-v<版本>-test.zip`（≈1.1 MB）。压缩包**顶层就是 `Yetannia/` 文件夹**，
所以「解压到 `...\\Slay the Spire 2\\mods\\`」正好得到 `mods\\Yetannia\\...`——
不会像常见的「解压出一层同名目录」那样多套一层。

包内文件：

| 文件 | 说明 |
|---|---|
| `Yetannia.json` | Mod 清单，游戏靠它发现 Mod |
| `Yetannia.dll` | 代码 |
| `Yetannia.pck` | 美术与场景 |
| `Yetannia.pdb` | 调试符号，留着崩溃日志才有行号（删掉也能玩） |
| `README.txt` | 安装说明，来自 `.tools/mod-readme.txt` |""",
"""产出 `Yetannia-v<版本>-test.zip`（当前 ≈20 MB；正式发布时用 `-Out Yetannia-v1.0.0.zip` 指定名字）。
压缩包**顶层就是 `Yetannia/` 文件夹**，
所以「解压到 `...\\Slay the Spire 2\\mods\\`」正好得到 `mods\\Yetannia\\...`——
不会像常见的「解压出一层同名目录」那样多套一层。

包内文件（**4 个，不含 `.pdb`**——Release 构建 `DebugType=none`，不再产生符号；
早期版本带过 `.pdb`，因为里面写死了构建机的源码绝对路径，已刻意移除）：

| 文件 | 说明 |
|---|---|
| `Yetannia.json` | Mod 清单，游戏靠它发现 Mod |
| `Yetannia.dll` | 代码 |
| `Yetannia.pck` | 美术与场景 |
| `README.txt` | 安装说明，来自 `.tools/mod-readme.txt` |""")

E(
"""  `Loading assembly DLL ...mods\\Yetannia\\Yetannia.dll` + `card pool : 39 card(s)` 正常）。""",
"""  `Loading assembly DLL ...mods\\Yetannia\\Yetannia.dll` + `card pool : 82 card(s)` 正常）。""")

E(
"""1. **选人立绘 / 顶栏头像 / 选人背景 / 战斗形象 / 火堆 / 商人 都已经是耶坦尼娅了**
   （贴图来自你的壁纸，见上面「美术」一节）。
2. **卡面是自制图**：白/蓝卡用 `card_portraits/test.png`，金卡用 `card_portraits/test2.png`，
   **基础与先古卡暂时跟白蓝卡共用**。想再分更细时改 `YetanniaCard.CustomPortraitPath` 即可。
3. **其余仍是基础游戏占位**：
   - 遗物图标借用 `burning_blood`（`YetanniaRelic.IconBaseName`）；
   - 能量图标用基础游戏配色，地图上的头像仍是铁甲战士。
4. 卡牌**名字**现在来自你的 `卡牌表1.0.xlsx`，改名字用 `.tools/rename-cards.js`（只改显示名），
   或者直接改 `Localization` 里的字符串。""",
"""1. **选人立绘 / 顶栏头像 / 选人背景 / 战斗形象 / 火堆 / 商人 都已经是耶坦尼娅了**
   （见上面「美术」一节）。
2. **卡面：82 张卡各有一张自制图**，放在 `images/card_portraits/` 下、按卡 id 命名
   （`YETANNIA-EMBER_BOON` → `ember_boon.png`），由 `YetanniaCard.CustomPortraitPath` 解析。
   两张先古卡（引领之光 / 合击）是 608×856 的竖幅，槽位与普通卡不同；其余是 500×380。
   `test.png` / `test2.png` / `blank.png` 只剩兜底作用，当前没有任何卡用到。
3. **遗物图标 / 费用图标 / 能量球 / 地图头像也已经换成自制资源**：
   - 5 个遗物各有 `images/relics/<name>.png`（64×64）和 `images/relics_big/<name>.png`（256×256），
     走 `YetanniaRelic.PackedIconPath` / `BigIconPath`，**不再借用 `burning_blood`**；
   - 费用图标 `images/ui/energy_yetannia.png`（大）/ `energy_yetannia_small.png`（小），
     走 `YetanniaCardPool.BigEnergyIconPath` / `TextEnergyIconPath`；
   - 左下角能量球 `scenes/energy_counter/yetannia_energy_counter.tscn`、
     地图头像 `images/ui/map_marker_yetannia.png`。
4. 卡牌**名字**现在来自你的 `卡牌表1.0.xlsx`，改名字用 `.tools/rename-cards.js`（只改显示名），
   或者直接改 `Localization` 里的字符串。""")

E(
"""12. **数值比例**：现在是攻击 31% / 技能 51% / 能力 18%，原版均值是 36/43/21。
    技能占比偏高、攻击偏低——你补卡时优先补攻击牌更容易贴回原版比例。
13. **先古卡（合击 / 引领之光）目前和白蓝卡共用 `test.png`**——你只说了「白卡蓝卡是 test，金卡是 test2」，
    先古没说。要让它们也用 `test2.png`（或者第三张图）说一声。""",
"""12. **数值比例**：现在是攻击 32% / 技能 45% / 能力 21%（另有 2 张状态牌），原版均值是 36/43/21。
    技能占比略偏高、攻击偏低——你补卡时优先补攻击牌更容易贴回原版比例。
    （口径：82 张全部计入，26 攻击 / 37 技能 / 17 能力 / 2 状态；上面第 545 行的原版基准表是按角色分的。）
13. ~~先古卡（合击 / 引领之光）和白蓝卡共用 `test.png`~~ → 已各有一张 608×856 的竖幅卡面
    （槽位 598×842，和普通卡的 500×380 / 250×190 不是一套比例）。""")

E(
"""**这个 Mod 现在支持联机，并新增 5 张联机专属牌。**""",
"""**这个 Mod 现在支持联机，共有 6 张联机专属牌。**""")

E(
"""### 新增的 5 张牌

| 牌 | 费 | 稀有度 | 类型 | 效果 |
|---|---|---|---|---|
| 先知的指引 `GuidanceOfTheProphet` | 1 | 金 | 技能 | 从 3 张随机能力牌中选 1 加入手牌并本回合免费打出（敲后那几个选项是已升级的）；然后**此牌**进入随机一名队友的弃牌堆 |
| 归途终尽之景 `EmberBoon` | 1 | 金 | 技能 | 指定一名队友；本场战斗中他每消耗一张牌，随机生成一张牌加入其手牌（敲后为已升级的）。不可叠加 |
| 身先士卒 `SharedFocus` | 1（敲后 0） | 蓝 | 能力 | 所有玩家获得 1 点敏捷 |
| 天之恩典 `SharedRegen` | 0 | 白 | 技能 | 所有玩家获得 2/3 点再生，消耗 |
| 先知的援助 `GiftOfTime` | 3（敲后 2） | 蓝 | 技能 | 指定一名队友：他本回合结束时获得一个额外回合；然后结束你的回合 |""",
"""### 联机专属的 6 张牌

| 牌 | 费 | 稀有度 | 类型 | 效果 |
|---|---|---|---|---|
| 先知的指引 `GuidanceOfTheProphet` | 1 | 金 | 技能 | 从 3 张随机能力牌中选 1 加入手牌并本回合免费打出（敲后那几个选项是已升级的）；然后**此牌**进入随机一名队友的弃牌堆 |
| 归途终尽之景 `EmberBoon` | 1 | 金 | 技能 | 指定一名队友；本场战斗中他每消耗一张牌，随机生成一张牌加入其手牌（敲后为已升级的）。不可叠加 |
| 身先士卒 `SharedFocus` | 1（敲后 0） | 蓝 | 能力 | 所有玩家获得 1 点敏捷 |
| 天之恩典 `SharedRegen` | 0 | 白 | 技能 | 所有玩家获得 2/3 点再生，消耗 |
| 先知的援助 `GiftOfTime` | 3（敲后 2） | 蓝 | 技能 | 指定一名队友：他本回合结束时获得一个额外回合；然后结束你的回合 |
| 回应愿景之心 `SharedMight` | 1（敲后 固有） | 蓝 | 能力 | 指定一名队友：本场战斗中当你获得力量 / 敏捷（不因此牌）时，他获得等量 |

单机牌共 82 − 6 = **76 张**。""")

E(
"""- **薪火** = 树枝 `BurningSticks` 的 `AfterCardExhausted`；「不可叠加」用
  `PowerStackType.Single` **再加**施放前的 `GetPower<EmberBoonPower>()` 查重——
  Single 只挡同一种能力叠层，挡不住「基础版和升级版各挂一个」。
- **同调 / 共鸣** = `Rally` / `Plot` 的「所有玩家」写法：`TargetType.AllAllies` +
  `GetTeammatesOf(Owner.Creature)`（**它包含自己**）+ `PowerCmd.Apply` 的集合重载。
- **时之礼** = 额外回合不是命令，而是模型上的两个钩子 `ShouldTakeExtraTurn` /
  `AfterTakingExtraTurn`（原版范例 `AmbergrisPower`）；结束自己回合用
  `PlayerCmd.EndTurn(Owner, canBackOut: false)`——**返回 void，不能 await**，照 `VoidForm`。""",
"""- **归途终尽之景**（旧稿代号「薪火」，模型 id 仍是 `YETANNIA-EMBER_BOON`）= 树枝 `BurningSticks` 的
  `AfterCardExhausted`；「不可叠加」用
  `PowerStackType.Single` **再加**施放前的 `GetPower<EmberBoonPower>()` 查重——
  Single 只挡同一种能力叠层，挡不住「基础版和升级版各挂一个」。
- **身先士卒 / 回应愿景之心**（旧稿代号「同调 / 共鸣」）= `Rally` / `Plot` 的「所有玩家」写法：
  `TargetType.AllAllies` +
  `GetTeammatesOf(Owner.Creature)`（**它包含自己**）+ `PowerCmd.Apply` 的集合重载。
- **先知的援助**（旧稿代号「时之礼」，模型 id 仍是 `YETANNIA-GIFT_OF_TIME`）= 额外回合不是命令，
  而是模型上的两个钩子 `ShouldTakeExtraTurn` /
  `AfterTakingExtraTurn`（原版范例 `AmbergrisPower`）；结束自己回合用
  `PlayerCmd.EndTurn(Owner, canBackOut: false)`——**返回 void，不能 await**，照 `VoidForm`。""")

E(
"""> 先知的指引（选牌 + 跨玩家给牌同时发生）和时之礼（额外回合 + 结束回合）。""",
"""> 先知的指引（选牌 + 跨玩家给牌同时发生）和先知的援助（额外回合 + 结束回合）。""")

reconstructed = cur
applied = 0
for old, new in EDITS:
    if new in reconstructed:
        reconstructed = reconstructed.replace(new, old, 1)
        applied += 1
    else:
        w("!! could not reverse-apply an edit hunk (%d)" % (applied + 1))
w("reverse-applied %d/%d hunks" % (applied, len(EDITS)))

rb = reconstructed.encode("utf-8")
BEFORE_MD_SHA = "368BC2170B883FE304F3DB4E49C5474460EE338371EAFB7F570E4B959642ABF0"
w("reconstructed pre-edit README.md: %d B %s" % (
    len(rb), hashlib.sha256(rb).hexdigest().upper()))
w("matches the hash recorded before the edits (+before packaging): %s" % (
    hashlib.sha256(rb).hexdigest().upper() == BEFORE_MD_SHA))

w()
w("######## DIFF: .tools/mod-readme.txt == the shipped README.txt (before -> after) ########")
w("".join(difflib.unified_diff(
    before_help.decode("utf-8").splitlines(True), after_help.decode("utf-8").splitlines(True),
    "README.txt (before, QA rt47 dump)", "README.txt (after)", n=1)))

w()
w("######## DIFF: README.md (before -> after) ########")
w("".join(difflib.unified_diff(
    rb.decode("utf-8").splitlines(True), cur.splitlines(True),
    "README.md (before)", "README.md (after)", n=1)))

open(os.path.join(ROOT, ".tools", "readme-fix-diff.txt"), "w", encoding="utf-8").write(out.getvalue())
print("ok")
