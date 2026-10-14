# 耶坦尼娅 Yetannia — 开发日志（原根目录 README.md 全文）

> 这里是项目的**开发过程记录**，保持原文。原来的根 `README.md` 是这份开发日志，
> 访问者看到的应该先是「这是什么、怎么装」，所以这次把根 README 换成了面向玩家/使用者的说明，
> 开发日志整体搬到 `docs/DEVELOPMENT.md`（就是本文件）。
> 使用说明见 [`../README.md`](../README.md)。
>
> **本文件里的数字、结论、流程都是「写下当时」的状态**，不代表当前版本。
> 当前卡表以 `README.md` 的「卡牌总览」为准——那张表由 `.tools/cards-xlsx.js` 从源码生成。
>
> 搬迁时只删除了**两段纯控制台粘贴**（其余内容一字未改，删除处都留了说明）：
>
> 1. 早期一次 39 张卡时期的 `self-check` 输出（原文自己标注「格式和数字都已过时」）；
> 2. 「耶坦尼娅当时的构成」一节里同一份 39 张卡时期的 `self-check type split` 输出。
>
> 另外把「卡牌总览」那张机器生成的表格换成了指向根 `README.md` 的说明（脚本只写
> `README.md`，两处各存一份必然漂移），并修正了目录树里「README.md ← 本文件」一行。
> 完整的自检代码见 `Yetannia/Code/ModSelfCheck.cs`。

---

内容已完成并在游戏内验证通过（数值、注册、本地化、美术资源加载、场景转换全部实测）。

> **本轮改动（第十七批）**：修 **因果切断** 的斩杀升级。
> 原来直接把 `CardCmd.Upgrade` 用在**被找出来的那张牌**上，而战斗中牌堆里放的是牌组卡的**可变副本**，
> 所以升级只在本场战斗内有效，下场就没了。现在改为升级它的 **`DeckVersion`**（牌组里那张持久卡），
> 这才是「等同于在火堆敲了那张牌」——`CardCmd.Upgrade` 对 `PileType.Deck` 的卡还会顺带写进地图升级记录。
> 非牌组来源的牌（生成/复制的）没有 `DeckVersion`，退化成只升级当前副本。
>> **上一轮改动（第十六批）**：7 项修正。
> 1. 奇袭 攻击 → **技能**。
> 2. 殚精竭虑的负面改成**只在下个回合**加一张眩晕（原来每回合都加），加完自动移除。
> 3. **先知的手链不再能跳过建筑师**——那是结算终局的事件，跳过会把这一局卡死。
> 4. 命定的抗争重做：2 费、**[虚无]**（无消耗），造成 18/26；**被消耗时本局游戏中它的伤害永久 +2**
>    （用原版 `GeneticAlgorithm` 那套：`[SavedProperty]` 存档字段 + 写回 `DeckVersion`）。
> 5. 厚积薄发 白 → **蓝**。
> 6. 积厚成势：升**金**；并修掉「先知直接加血上限」的 bug——现在先知**只抬高卡面数字**，
>    **打出时才把那个累计数字变成生命上限**（记账改到卡自己的 `MaxHp` 变量上，不再用隐藏能力）。
> 7. 预备：基础带[消耗]，**敲后去掉[消耗]**。
>> **上一轮改动（第十五批）**：4 张卡 + 3 个遗物 + 1 处修改，卡池 51 → **55 张**，遗物 2 → **5 个**。
> 卡：银铃响起之时（临时力量 / 达标转永久+下回合抽2）、临危不乱（临时敏捷 / 未受伤转永久+下回合回2费）、
> 星光破晓之刻（金能力：易伤敌人受伤+25%、虚弱敌人造伤-15%）、纯爱药丸（金技能：格挡+人工制品，消耗）。
> 遗物：玛瑙的药水腰带（稀有）、先知的手链（普通，给所有问号事件加「跳过拿50金币」选项）、
> 未命名·预见（罕见，每累计预见10给1费）。
> 修改：纯爱形态敲后从「费用3→2」改成「获得[保留]」。
>
> 两个新机制值得记：**先知的手链**靠 postfix `EventModel.GenerateInitialOptionsWrapper`
> 给所有事件加选项（`GenerateInitialOptions` 是抽象方法、每个事件各自重写，只有这个包装器是共用的），
> 选项文案走既有的 `LocManager.GetTable` 注入；**临时力量/敏捷**直接继承游戏自带的
> `TemporaryStrengthPower` / `TemporaryDexterityPower`，只需要提供 `OriginModel`。
>> **上一轮改动（第十四批）**：新增 9 张卡，卡池 42 → **51 张**（技能 25 / 攻击 18 / 能力 8）。
> 白 5 张、蓝 2 张、金 2 张，全部用占位名（需求里没给名字）。
> 其中两张是 X 费牌（`HasEnergyCostX` + `ResolveEnergyXValue()`），
> 一张带**按目标**的出牌条件（`ShouldPlay` + `CanPlayTargeting` 补丁，见下），
> 两张带「每抽到一次降 1 费」（`AfterCardDrawn`）。
>
> 上一轮（第十三批）：删试探打击、积厚成势改技能/消耗/立即、试探加伤害、横扫 1c、
> 背水一战触发先知、重整旗鼓敲后 0c、新增 4 张卡、韬光养晦去掉结束回合、卡面换成 test/test2。
> 更早（第十二批）：先知触发等效打出、建筑师结算补丁、运筹帷幄敲后生效、遗物改成战斗开始时预见 5/10。
> **上一轮改动（第十三批）**：12 项。
> 1. **删除** 白卡「试探打击」（`JustLucky`）。
> 2. **积厚成势**改成 技能 / [消耗] / 打出**立即**获得生命上限（原来是战斗结束时结算的能力牌）；
>    稀有度同时从金降到**蓝**。
> 3. **试探**（初始卡）增加「对所有敌人造成 6 点伤害」。
> 4. **横扫** 2 费 → **1 费**。
> 5. **背水一战**增加[消耗]，并且它消耗掉的牌现在**会触发各自的先知效果**。
> 6. **重整旗鼓**：基础效果改成原来的敲后版（抽牌堆 + 弃牌堆 + 手牌），**敲后费用 1→0**。
> 7. **新增** 蓝 0 费技能：获得 2/3 费，本回合结束时把一张复制放进弃牌堆，[消耗]。
> 8. **新增** 蓝 1 费能力：打出后每累计预见 6/4 张牌获得 1 力量（**打出前的预见不算**）。
> 9. **新增** 蓝 1 费能力：打出后每累计预见 7/5 张牌获得 1 敏捷（**打出前的预见不算**）。
> 10. **新增** 金 2 费攻击：全体 5 伤害 4/5 次，本场每洗牌一次获得重放 1。
> 11. **韬光养晦**去掉「结束你的回合」。
> 12. **卡面**换成自制图：白/蓝用 `test.png`，金用 `test2.png`（见「美术」一节）。
>
> 卡池 39 → **42 张**（技能 22 / 攻击 12 / 能力 8）。
>
> 上一轮（第十二批）：先知触发改「等效打出」（重放 + 能力牌进 Limbo）、建筑师结算补丁、
> 运筹帷幄敲后生效、初始遗物改成战斗开始时预见 5/10。
> 更早：按卡表改名与补敲后效果；打击/防御换自制卡；新增 11 张卡。

## 当前状态（已实测确认）

在 `v0.111.0` 游戏 + BaseLib `v3.4.7` 环境下启动游戏：

```
[INFO] Loading assembly DLL ...\mods\Yetannia\Yetannia.dll
[INFO] Loading Godot PCK ...\mods\Yetannia\Yetannia.pck
[INFO] [Yetannia] Yetannia: initialized
[INFO] Finished mod initialization for 'Yetannia' (Yetannia).
```

Mod 内建的自检（`Code/ModSelfCheck.cs`）在 `ModelDb` 构建完成后核对注册结果。

> ⚠️ 下面是**早期版本**（39 张卡时期）的一次运行输出，**格式和数字都已过时**，留在这里只是
> 为了让自检的**格式**有个参照。当前实测到的是
> `self-check card pool : 82 card(s)`、`self-check relic pool : 5 relic(s)`、
> `self-check portrait ok : 82/82`、`self-check art : selectIcon=528x780 locked=132x195 hud=88x88`
> （QA 第 47 轮，见 `.tools/qa/QA-RETEST47.md` §②）。卡数明细见下面「卡牌总览」一节。

> （**搬迁时删掉的一段**：原文此处粘贴了一次 39 张卡时期的 `self-check` 控制台输出——
> 就是 README 自己标注「格式和数字都已过时」的那一段。留一份写着 `39 card(s)` / `2 relic(s)` 的
> 输出，只会让后来的人以为那就是当前状态。自检代码在 `Yetannia/Code/ModSelfCheck.cs`，
> 现在它会打印 82 张卡的逐张明细。）

两行合起来才算验完，它们查的是两件不同的事：

- **`scene load`** 查「注册表查得到吗」——BaseLib 的 `NodeFactory.TryAutoConvert` 用
  `scene.ResourcePath` 去查它注册过的键（就是日志里那三行
  `Registered scene 'res://Yetannia/scenes/...' for auto-conversion to X`）。
  `[ok]` 表示两边完全一致；`MISMATCH` 就说明导出把场景变成了别的路径（见踩坑记录 4）。
  后面的类型是**转换前的原始节点类型**，本来就该是 `Node2D`/`Sprite2D`/`Control`。
- **`convert`** 查「工厂建得出来吗」——直接干跑一次真的 `NodeFactory<T>.CreateFromScene`，
  报出生成的节点类型、子节点数和游戏 `_Ready` 会去 `GetNode` 的那些命名节点是否都在。
  这是另一种失效方式：名字对上但**节点类型**不对时，基类 `ConvertNodeType` 会抛异常、
  BaseLib rethrow，转换半路死掉。干跑出来的节点不进场景树（`_Ready` 不会跑、不碰战斗状态），
  报告完立刻 `Free()` 掉。

> ⚠️ 踩坑记录 4：**BaseLib 的场景转换是靠 `scene.ResourcePath` 查表的**（最容易漏的一个）。
> Godot 默认导出会把 `.tscn` 转成二进制 `.scn` + `.remap`，于是运行时 `ResourcePath` 变成
> `res://.godot/exported/...`，和注册的 `res://Yetannia/scenes/...` 对不上，
> **转换会静默失效**（日志里什么都看不到，游戏里就是铁甲战士占位）。
> 已在 `.tools/pckproject/project.godot` 里设 `export/convert_text_resources_to_binary=false` 修掉，
> 并且自检现在会把 `ResourcePath` 打出来，不再靠猜。详见「美术」一节。
>
> ⚠️ 踩坑记录 5：**卡面数值会随战斗状态变化的卡，不能用普通 `DamageVar`**。
> 普通 `DamageVar` 的 `BaseValue` 永远等于印在牌上的那个数，你在 `OnPlay` 里手算出来的
> 总伤害**不会反映到卡面**——卡面会一直显示基础值（预见打击就踩了这个坑）。
> 要用 `CalculationBaseVar` + `ExtraDamageVar` + `CalculatedDamageVar.WithMultiplier(...)`，
> 让引擎在刷新卡面时重算。详见「伤害缩放」一节。

无任何 `MOD_ERROR` / 异常。

> ⚠️ 踩坑记录 1：游戏会把「尚未在设置里启用」的 Mod 记为 `is_enabled: false` 并跳过加载
> （日志里是 `Skipping loading mod Yetannia, it is set to disabled in settings`）。
> 如果哪天 Mod 突然不生效了，先去游戏的 Mod 列表里确认它是打开的。
>
> ⚠️ 踩坑记录 2：**数值升级不要同时写 `WithUpgrade()` 和 `UpgradeValueBy()`**。
> BaseLib 会在 `OnUpgrade()` 之前自动应用 `WithUpgrade` 的值（见其 `UpgradeInternalPatch`），
> 两边都写就会翻倍。本 Mod 统一只用 `OnUpgrade()` 里的 `UpgradeValueBy()`。
>
> ⚠️ 踩坑记录 3：**`PowerVar<T>` 的变量名是类型名，不是 `Power`**。
> `new PowerVar<ForesightPower>(3)` 生成的变量叫 `ForesightPower`，所以卡面文案必须写
> `{ForesightPower:diff()}`；写成 `{Power:diff()}` 游戏会把这串字**原样显示在卡面上**
> （基础游戏的 Shockwave 能用 `{Power}` 是因为它显式声明了一个名叫 `"Power"` 的 `DynamicVar`）。
> 为了避免再犯，自检现在会把每张卡的**最终渲染文案**打出来，并扫描未解析的 `{...}` 占位符：
> 日志里出现 `self-check UNRESOLVED placeholders in: ...` 就说明有卡面文案写错了。

---

## 已实现内容

### 角色：耶坦尼娅 Yetannia
- 生命上限 70，能量图标沿用基础游戏的 `colorless` 配色，卡框为紫色 HSV 着色。
- 初始牌组（10 张）：**4 打击 + 4 防御 + 回避 + 试探**。
  打击/防御是本 Mod 自己的等价卡（`Strike` / `Defend`），用的是空白卡面，见下方说明。

### 初始遗物：先知发饰
> 战斗开始时，预见 5。（先古版「先知头冠」：战斗开始时，预见 10。）

实现在 `Code/Relics/ProphetsEye.cs`（超越版 `ProphetsEyePlus.cs`）。
遗物继承自 `AbstractModel`，本身就是战斗钩子监听者。

> ⚠️ **时机很关键**：`Hook.AfterPlayerTurnStart`（连它的「Early」阶段）整段都是在
> `SetupPlayerTurn` 抽完 5 张**之后**才派发的。要想在起手牌之前预见，必须用
> **`AbstractModel.BeforeHandDraw`**——先知发饰、先知头冠和先见之明都走这个钩子。
> 否则玩家会先抽到牌、再被要求预见他本来就要抽的牌。

> **「战斗开始时」怎么限定的**：`BeforeHandDraw` 每回合都会调，所以用
> `player.PlayerCombatState?.TurnNumber != 1` 来只让它在**第一回合**生效
> （`TurnNumber` 从 1 开始、每回合自增，下一场战斗自然重置，不需要额外的标志位）。

### 关键词：先知
> 当此牌从抽牌堆进入弃牌堆时，触发本牌的先知效果。
> 先知后面没有额外描述时，表示「从抽牌堆被弃置时的效果和打出时一样」。

- 关键词本体：`Code/Keywords/YetanniaKeywords.cs`，通过 BaseLib 的 `[CustomEnum]` 生成，
  本地化键为 `YETANNIA-PROPHET`。
- 本地化：`Code/Keywords/KeywordLocPatch.cs`。BaseLib 只支持给「模型」注入本地化，而
  `card_keywords` 不是模型表；Mod 又没有 `.pck` 来放 JSON 词条表，所以这里在
  `LocManager.GetTable` 上加后置补丁，第一次拿到 `card_keywords` 表时把两条词条合并进去
  （切换语言后会自动重新注入）。
- **触发逻辑统一放在基类 `YetanniaCard` 里**：重写
  `AbstractModel.AfterCardChangedPiles(card, oldPileType, clonedBy)`，判断
  `oldPileType == PileType.Draw` 且 `card.Pile.Type == PileType.Discard`。
  战斗中牌堆里的每张 `CardModel` 本身就是钩子监听者，所以卡牌能监听自己的换堆事件。
  注意：**从手牌被弃置不会触发**，这正是词条的要求。
- 每张带先知的卡只需要重写 `protected override Task OnProphet(PlayerChoiceContext ctx)`，
  写自己的先知效果即可。
- ⚠️ 换堆不是玩家操作，没有真正的 choice context，基类传的是
  `ThrowingPlayerChoiceContext`（游戏里给「钩子触发、不应询问玩家」场景准备的）。
  所以**先知效果里不能要求玩家做选择**（比如不能在里面用预见）。

#### 先知触发要「等效打出」，不是「触发一次效果」

基类的触发逻辑做两件额外的事，让被弃置的触发真的等价于打出这张牌：

1. **重放 N 次**：正常打出时 `OnPlay` 会跑 `playCount = GetEnchantedReplayCount() + 1` 次
   （见 `CardModel.OnPlayWrapper` 的循环）。先知触发原来是跑 1 次，于是带「重放」的牌
   被预见过牌时会白丢重放。现在触发也跑同样次数。
   顺带：`ProphetTallyPower`（先知累积）按**每次结算**+1，所以重放触发算作多次先知效果。
2. **能力牌进 Limbo**：打出能力牌时 `GetResultLocationForCardPlay()` 返回 `PileType.None`，
   游戏走的是 `CardPileCmd.RemoveFromCombat`——能力牌会**离开这场战斗**，不能再被打出第二次。
   先知触发原来把牌留在弃牌堆里，结果就是「效果发动了，牌还在」，可以再抽到再打一次。
   现在 `Type == CardType.Power` 的牌在触发后同样 `RemoveFromCombat`。

> 这两条都只在**弃牌触发的路径**上加逻辑，正常打出走的还是游戏原本的流程。

### 卡牌总览

> 本节的表格**由 `.tools/cards-xlsx.js` 生成**，`package-mod.ps1` 每次打包都会自动同步，**请勿手改**。
> 这里曾经是手维护的，结果漂移到 58 行对 82 张、标题还写着「60 张」，漏掉了 34 张卡——生成之后
> 加卡就不可能再让 README 掉队。
>
> 命名与数值来自你给的 `卡牌表1.0.xlsx`（后续批次按你的追加说明改）。
> **只有显示名改了，类名 / 文件名 / 模型 ID 一律不动**（这样旧存档仍然能解析），
> 批量改名脚本是 `.tools/rename-cards.js`。效果文案取详细写法：本体一段，`敲后：` 另起一段。

> **卡牌总览的表格由 `.tools/cards-xlsx.js` 生成，现在挂在根目录
> [`README.md`](../README.md) 的「卡牌总览」一节**（脚本把它写死到 `README.md`，见
> `.tools/cards-xlsx.js:1064`），这里不再重复一份，以免两处漂移。

完整表格（含每一项敲后数值、源文件对照、关键词表）由 `.tools/cards-xlsx.js` 生成
`Yetannia-卡牌表.xlsx`（该 xlsx 不入库，按需本地生成）。

### 打击 / 防御（`YetanniaStrike` / `YetanniaDefend`）

这两个是**本 Mod 自己实现**的，不是基础游戏的 `StrikeIronclad` / `DefendIronclad`。

原因是卡面：`CustomPortraitPath` 只对 BaseLib 的 `CustomCardModel` 子类生效，而基础游戏的
打击/防御直接继承 `CardModel`，再怎么写都拿不到空白卡面。数值、标签、稀有度和基础游戏完全一致
（1 费 6 伤害 / 敲 +3、1 费 5 格挡 / 敲 +3、`CardRarity.Basic`、
`CardTag.Strike` / `CardTag.Defend`），所以「统计打击牌」之类的效果照常工作。

副作用：它们会进卡池，于是基础卡从 2 张变成 4 张——这反而和基础游戏角色的结构一致了
（基础游戏每个角色也是 4 张 Basic）。

### 攻击牌 test（请君入瓮 `TestAttack`）

- 金卡，1 费，造成 12 点伤害，升级后 16 点（`{Damage:diff()}` 自适应显示）。
- 先知：**对随机目标打出此牌，然后此牌伤害翻倍。**
- 顺序是有意的：先用**当前**伤害打一次，再翻倍。所以第一次触发打 12、把牌留在 24，
  第二次打 24、留在 48，以此类推。
- 随机目标用 `TargetingRandomOpponents(CombatState)`，和原版 Ricochet / Volley 同一套。
  打出时 `FromCard(this, null)`——先知触发不是一次「出牌」，但命令仍然需要攻击者
  （牌主的生物）和这张牌作为 model source。
- **不会递归**：触发来自换堆（抽牌堆 → 弃牌堆），而攻击不会移动这张牌，
  所以它不可能重新进入 `AfterCardChangedPiles`。
- 费用**不会**随先知增长（早期版本触发后会给这张牌 +1 费，已按要求去掉）。

### 技能牌 test（运筹帷幄 `TestSkill`）

- 蓝卡，0 费，消耗。
- 将你的所有手牌置于抽牌堆顶，预见 8（升级 10），然后抽取等量的牌。
- 「预见」使用 BaseLib 的 `ScryCmd`。
- 放入牌堆顶时按手牌**逆序**添加，因为 `CardPilePosition.Top` 是插入到索引 0，逆序才能保持
  手牌原本的上下顺序。

### 初始卡

- **回避 `ForesightWard`**：基础，0 费技能。获得 3 点格挡（升级 4）；先知：获得 4 点格挡（升级 6）。
  卡上有**两个**格挡变量：`Block`（打出用）和名为 `ProphetBlock` 的第二个 `BlockVar`
  （先知触发用），这样两者可以有不同的升级增量。两者都走 `CreatureCmd.GainBlock`，
  因此力量/敏捷类格挡修正对两边都生效。
- **试探 `OminousDecree`**：基础，1 费技能，目标为所有敌人。给予全体 1 层易伤 + 1 层虚弱。
  **敲后是费用 1 → 0，层数不变**。先知没有额外描述 → 效果与打出相同。
  用 `PowerCmd.Apply<T>` 的集合重载一次性作用于 `CombatState.HittableEnemies`，
  和基础游戏的 Shockwave 写法一致。同时实现 `ITranscendenceCard`，供欧罗巴斯的「替换初始卡」使用。

### 新增卡牌的机制落点

新增的 11 张里有几张需要单独的机制，记在这里方便以后改：

| 卡 | 关键实现 |
|---|---|
| 制敌机先 / 奇袭 | 意图判定用 `creature.Monster?.IntendsToAttack`——基础游戏自己就是用这个属性判断「意图是攻击」的（含 Attack 与 DeathBlow）。奇袭把 `Monster == null` 也当作「非攻击」。 |
| 厚积薄发 / 预见打击 | 数值随战况变化，必须用 `CalculatedDamageVar`（见下一节）。 |
| 奋不顾身 | 生成眩晕走 `CombatState.CreateCard<Dazed>` + `CardPileCmd.AddGeneratedCardToCombat`，和殚精竭虑同一条路径。 |
| 伺机而动 | 自己实现 BaseLib 的 `IAfterScryed` 记录「本回合预见过」，用 `PlayerCombatState.TurnNumber` 判断是否还在本回合——不需要额外的隐藏增益，也不需要重置钩子。 |
| 韬光养晦 | 保留手牌用 `CardCmd.ApplySingleTurnRetain`（基础游戏 Expertise 的写法，会自己失效）；置顶复用预备的选择器；下回合费用用 `EnergyNextTurnPower`；结束回合用 `PlayerCmd.EndTurn(Owner, canBackOut: false)`，基础游戏 VoidForm 就是这么做的。 |
| 全力进攻 | `card.EnergyCost.AddThisTurnOrUntilPlayed(-1)`——它的过期条件是 `EndOfTurn | WhenPlayed`，正是「直到它被打出」。 |
| 重整旗鼓 | 状态牌 = `CardType.Status`，基础只查抽牌堆、敲后加上弃牌堆与手牌——**任何情况下都只取状态牌**，
敲后拓宽的是「查哪些牌堆」而不是「拿什么」；先把状态牌收集成列表再逐张消耗，避免边遍历边改动牌堆。
卡面用引擎自带的 `{IfUpgraded:show:…|…}` 分支表达范围差异（见下）。 |
| 纯爱形态 | 见下面的专门小节。 |

### 纯爱形态（`PureLoveFormPower`）

> 本场战斗中，当你从抽牌堆弃置非[先知]牌时，将其视为打出。

- 增益挂在玩家身上，重写 `AfterCardChangedPiles`，条件与先知触发完全对称：
  `oldPileType == PileType.Draw` 且 `card.Pile?.Type == PileType.Discard`，
  但**反过来排除**带先知关键词的牌（它们走自己的先知效果）。
- 「视为打出」用 `CardCmd.AutoPlay(ctx, card, null)`，和基础游戏 Sly 的
  `AutoPlayType.SlyDiscard` 是同一条路径——**牌已经在弃牌堆里了，再从这里打出去**是支持的。
  目标传 `null`，`AutoPlay` 自己会给需要目标的牌随机挑一个，正好对应需求里
  「指定目标的牌为随机目标」。
- 钩子不带 choice context，所以用 `BlockingPlayerChoiceContext`
  （它的文档说明里就点名了「钩子触发但要等玩家决策」的场景，例如 Hellraiser 的 Seeking Strike）。
- **不会自我递归**：守卫要求「抽牌堆 → 弃牌堆」这一次跃迁，而打出牌只会把它从 play 堆送去结算堆，
  不可能再回到抽牌堆。
- 需求括号里那句「（指定目标的牌为随机目标，括号内无需写入卡牌描述）」是给实现者的说明，
  所以卡面文案里没有它。

### 敲后只改描述、不改数字：`{IfUpgraded:show:…|…}`

重整旗鼓的敲后效果是**作用范围**变了（抽牌堆 → 抽牌堆 + 弃牌堆 + 手牌），没有数字可标。
基础游戏自己的做法是用升级分支格式器：

```
消耗你抽牌堆的状态牌{IfUpgraded:show:，以及弃牌堆和手牌的状态牌|}。
```

`CardModel.GetDescriptionForPile` 会自动往变量表里塞一个 `IfUpgradedVar`，
它的显示模式由 `IsUpgraded`（以及是否在看待升级预览）决定，所以同一串文案在
**卡面 / 升级预览 / 卡牌图鉴** 三个地方都会自动显示对应的那一支
（升级预览那支还会被染成绿色）。`Enlightenment`、`Stoke`、`Splash` 用的就是这个。

> 自检现在会把**敲后文案也渲染一遍**（`self-check desc up`），
> 否则这一类「只存在于升级分支里的文字」写错了根本不会有人发现。


### 伤害缩放（`CalculatedDamageVar`）

「预见打击」（原宿命累积）和「厚积薄发」的伤害都随战况变化，必须走**计算型变量**，
否则卡面永远显示基础值：

```csharp
protected override IEnumerable<DynamicVar> CanonicalVars =>
[
    new CalculationBaseVar(6),        // 卡面基础伤害
    new ExtraDamageVar(3),            // 每次触发的增量
    new CalculatedDamageVar(ValueProp.Move).WithMultiplier(
        static (CardModel card, Creature _) => (decimal)YetanniaCard.ProphetTallyOf(card))
];
```

- 打出时用 `DamageCmd.Attack(DynamicVars.CalculatedDamage)`，
  `AttackCommand` 每次结算都会重算，所以读的是**结算那一刻**的数值。
- 卡面显示的是 `PreviewValue`：`NCard.UpdateVisuals` → `CardModel.UpdateDynamicVarPreview`
  → `CalculatedVar.UpdateCardPreview` → `Calculate()`；而 `NPlayerHand` 订阅了
  `CombatManager.StateTracker.CombatStateChanged`，**任何战斗状态变化都会刷新手牌**，
  所以计数一变，卡面数字立刻跟着变（比基础值高时还会显示为绿色）。
- 升级要改的是 `CalculationBase` 和 `ExtraDamage`（6→9、3→4），
  `UpgradeInternal()` 之后会调 `DynamicVars.RecalculateForUpgradeOrEnchant()` 把新基数同步过去。
- 两张牌用的取数函数不同：预见打击用 `ProphetTallyOf`（本场战斗先知触发次数），
  厚积薄发用 `ProphetCardCount`（战斗中带先知关键词的牌数）。

> ⚠️ `WithMultiplier` 的入参**不能是捕获了 `this` 的 lambda**——它内部会检查
> `multiplierCalc.Target is AbstractModel` 并抛异常。所以要用 `static` lambda，
> 而且静态 lambda 里**不能写继承来的非限定成员名**（编译器会当成 `this` 引用，
> 报 CS8821），必须写成 `YetanniaCard.ProphetTallyOf(card)` 这样的全限定形式。
> 这也是为什么基类里有两个 `internal static` 取数函数。

### 先古内容
- **欧罗巴斯的替换初始卡**：`OminousDecreeTranscendent`（合击，原名厄运宣告·超越），**稀有度是先古卡**。
  `OminousDecree` 实现 `ITranscendenceCard`，BaseLib 的 `ArchaicToothTranscendenceUpgradesPatch`
  会在玩家走「古老之牙」路线时把初始卡换成它：给予所有敌人 2 层易伤 + 2 层虚弱并造成 15 伤害。
  **敲后不增加易伤/虚弱层数，而是费用 1 → 0**（伤害仍然 15 → 20）。
- **欧罗巴斯的替换先古遗物**：`ProphetsEyePlus`（先知头冠，战斗开始时预见 10）。
  `ProphetsEye.GetUpgradeReplacement()` 接的是游戏的 `TouchOfOrobas.GetUpgradedStarterRelic`。
- **达弗的先古卡**：`DarvsProphecy`（引领之光），技能，3 费（**敲后 2 费**），固有，
  预见整个抽牌堆，消耗。实现 `ITomeCard`，BaseLib 的 `DustyTomeCardPatch` 会把它加入
  达弗「陈旧的书卷」的卡池。

### 移植自《杀戮尖塔 1》观者的预见卡（6 张，稀有度/费用/效果与原作一致）

| 卡 | 稀有度 | 费 | 类型 | 效果 |
|---|---|---|---|---|
| 试探打击 `JustLucky` | 白 | 0 | 攻击 | 预见 1/2，获得 2/3 格挡，造成 3/4 伤害 |
| 先制 `CutThroughFate` | 白 | 1 | 攻击 | 造成 7/9 伤害，预见 2/3，抽 1 张牌 |
| 修顿 `ThirdEye` | 白 | 1 | 技能 | 获得 7/9 格挡，预见 3/5 |
| 有条不紊 `Foresight` | 蓝 | 1 | 能力 | **抽 5 之前**预见 3/4 |
| 步步为营 `Nirvana` | 蓝 | 1 | 能力 | 每当你预见时，获得 3/4 格挡 |
| 回马枪 `Weave` | 蓝 | 0 | 攻击 | 造成 4/6 伤害；每当你预见时，从弃牌堆移回手牌 |

「每当你预见时」的两张卡靠 BaseLib 的 `IAfterScryed` 钩子实现（由 `ScryCmd` 派发），
所以**本 Mod 里所有预见都必须走 `ScryCmd`**，否则这两个效果不会触发。
（伺机而动也用同一个钩子记录「本回合预见过」。）

### 能力牌（`Code/Powers/`）
`ProphetTallyPower`（先知累积，记录本场战斗触发次数）、`ForesightPower`、`NirvanaPower`、
`PropheticStudyPower`、`FatedVitalityPower`、`CycleOfProphecyPower`、`PureLoveFormPower`。

### 预见消耗流（3 张）
| 卡 | 稀有度 | 费 | 类型 | 效果 |
|---|---|---|---|---|
| 抉择 `PurifyingVision` | 蓝 | 1 | 技能 | 预见 2，消耗因此被弃置的牌，抽 2/3 |
| 预备 `RearrangedFate` | 白 | 0 | 技能 | 将任意数量的手牌放到抽牌堆顶 |
| 背水一战 `GrandProphecy` | 金 | 2 | 技能 | 预见 6/8，消耗因此被弃置的牌，抽取剩下的牌 |

两张「消耗弃牌」的卡都走 `CardCmd.Exhaust`，所以消耗相关的钩子会正常触发。
`ScryCmd` 会把预见弃掉的牌放进弃牌堆，这里再逐张消耗掉。

> 预备目前**不可升级**——你更新后的表里第 13 行仍然写着「不可升级：没有敲后效果」，
> 所以按表的来（见「需要你确认」里的说明）。

> **已删除**：曾经有过一批「纯数值过渡牌」（10 张无先知词条的干净数值牌，
> 文件为 `OmenStrike` / `TwinOmen` / `RuinousBlow` / `FatedGuard` / `SunderingProphecy` /
> `CrushingOmen` / `WeakeningProphecy` / `IronBulwark` / `OracularFocus` / `FinalJudgement`）。
> 两轮调整后仍然达不到要求，按指示**全部删除**，`Code/Cards/` 与 `Code/Powers/OracularFocusPower.cs`
> 里已无残留。下面的「数值设计基准」一节保留下来，作为后续加卡时的对标参考。

---

## 数值设计基准（对标原版）

### 来自视频的观点

参考视频：[安八分钱？东尼意思？浅析尖塔卡牌数值设计](https://www.bilibili.com/video/BV14NMd6dEwq)（作者：穿-云-箭）。

> 说明：我无法观看视频，下面是**作者本人在视频简介里写的观点**加上视频标题，
> 不是逐句听写的字幕。如果视频正文还有别的结论，以你看过的为准。

1. 目的是用**一条基准线**分析卡牌数值，和卡牌强度无关；作者也说明这对实际抓牌没有指导意义。
2. 作者自认视频里的数值计算有缺陷，**对「功能性词条」的计数偏低**。
3. **一层易伤的价值通常大于 3 点数值，虚弱同理。** 能上第二层的牌更有价值，
   但多层易伤是跨回合收益、没有即时数值产出，层数过多通常无收益，
   所以视频把第一层和第二层的易伤/虚弱按同样数值计数。
4. **纯数值攻击卡的敲位提升通常大于「数值 + 功能」混合卡。**
5. 一代（杀戮尖塔 1）相较二代数值略低——因为二代删掉了一批低数值的垃圾牌。
6. **由于卡位集中，2 费卡相较 1 费卡的基础数值、敲位提升通常不满 2 倍关系。**
7. 作者给的算例：冲刺 10/10 合计 24 伤害，敲后 13/13 合计提升 7.2 伤害。

### 我们从游戏数据里量出来的原版基准

用 `.tools/poolratio.js` 直接统计反编译出来的原版角色卡池：

| 角色 | 卡数 | 攻击 | 技能 | 能力 |
|---|---|---|---|---|
| 铁甲战士 | 90 | 43% | 34% | 22% |
| 静默猎手 | 91 | 30% | 51% | 20% |
| 亡灵缚者 | 91 | 38% | 40% | 22% |
| 摄政王 | 91 | 35% | 44% | 21% |
| 故障机器人 | 91 | 32% | 45% | 23% |
| **均值** | | **36%** | **43%** | **21%** |

结构上还有两条硬性规律：

- **白卡（Common，20 张）完全没有能力牌**，只有攻击和技能；能力牌集中在蓝卡（38 张）和金卡（27 张）。
- 稀有度总量约为 Common 20 / Uncommon 38 / Rare 27（另有 Basic 4 / Ancient 2）。

### 原版卡牌的实测数值表（用 `.tools/cardstats.js` 统计）

统计范围：5 个原版角色卡池里**不含其他效果**的纯伤害攻击 / 纯格挡技能。

**纯伤害攻击（基础 → 敲位提升）**

| 稀有度 | 费用 | 原版样例 | 该档取值 |
|---|---|---|---|
| 基础 | 1c | 打击 6(+3) | 6 / +3 |
| 白 | 0c | Claw 3、Anger 6、Slice 6、CollisionCourse 10 | 3–10 / +1–+4 |
| 白 | 1c | 32 张，中位 8、众数 9 | **8–10 / +2–+3** |
| 白 | 2c | Predator 15(+5)、Cinder 18(+6) | **15–18 / +5–+6** |
| 白 | 3c | Reap 27(+6) | 27 |
| 蓝 | 1c | 8–10 / +2–+3（Devastate 35 是异类） | **8–10** |
| 蓝 | 2c | Uppercut 13、RocketPunch 13、Severance 13、Unrelenting 14、Pounce 14、Synthesis 14 | **13–15** |
| 蓝 | 3c | Stomp 12、Pinpoint 15、HowlFromBeyond 18、Sunder 26、**Bludgeon 32(+10)** | 12–32 |
| 金 | 2c | AdaptiveStrike 18、HeirloomHammer 20、Hyperbeam 24 | **18–24** |
| 金 | 3c | IceLance 19、Mangle 20、Bombardment 18 | 18–20 |

**纯格挡技能**

| 稀有度 | 费用 | 原版样例 | 该档取值 |
|---|---|---|---|
| 基础 | 1c | 防御 5(+3) | 5 / +3 |
| 白 | 1c | 15 张，均值 6.8，高段 8(+3)、9(+3) | **6–9 / +2–+3** |
| 白 | 2c | 16(+4)、11(+4) | 11–16 |
| 蓝 | 1c | 5–8 / +3 | 5–8 |
| 蓝 | 2c | 12、11、12、11 | 11–12 |
| 金 | 2c | 30(+10) | 30 |

**带易伤 / 虚弱的卡（关键）**

| 卡 | 稀有度 | 费 | 数值 |
|---|---|---|---|
| Tremble | 白 | 1c | 3 层易伤(+1)，无伤害 |
| SuckerPunch | 白 | 1c | **8 伤害 + 1 虚弱**（+2 伤害 +1 虚弱） |
| Thunderclap | 白 | 1c 群体 | 4 伤害 + 1 易伤全体（+3 伤害） |
| LegSweep | 蓝 | 2c | **11 格挡 + 2 虚弱**（+3 格挡 +1 虚弱） |
| Uppercut | 蓝 | 2c | 13 伤害 + 1 易伤 + 1 虚弱 |
| Haze | 蓝 | 2c 群体 | 4 中毒 + 1 虚弱全体 |
| MeteorShower | 先古 | 0c 群体 | 14 伤害 + 2 易伤 + 2 虚弱 |
| Bash | 基础 | 2c | 8 伤害 + 2 易伤 |

### 我第一版做错的四个地方（写在这里，下次加卡别再犯）

这一节是那批被删掉的过渡牌留下的教训，对后续补卡同样适用：

1. **拿基础牌当白卡基准**。我把白卡 1 费纯伤害定成 6（照抄打击），但**原版白卡的众数是 9**——
   打击/防御是设计地板，不是白卡基准线。
2. **以为群体攻击要大幅降数值**。STS2 里**群体攻击和单体基本同数值**：白卡 1 费群体是 8–9，
   和单体的 8–10 一个水平。
3. **以为易伤/虚弱要吃掉大量模**。原版恰恰相反：SuckerPunch（8 伤害 + 1 虚弱）和纯伤害卡持平，
   LegSweep（11 格挡 + 2 虚弱）和纯格挡卡持平——**功能词条在原版里几乎不计费**。
4. **稀有度没有体现出差距**。`稀有度占模`：纯数值的蓝卡必须明显压过白卡，
   否则玩家没有理由去拿高稀有度的纯数值卡。

### 耶坦尼娅当时的构成（自检实测）

> （**搬迁时删掉的一段**：原文此处又粘了一次上面那份 39 张卡时期的 `self-check type split` 输出。
> 下面这段评论是那个时期写的，数字同样是那时的。）

**白卡没有能力牌**，这条和原版一致。技能占比（51%）仍然高于原版均值（43%），攻击偏低（31% vs 36%）——
比上一版（54/23）近了一点，后面补卡时继续优先补攻击牌。

> 顺带一提：「横扫」（白卡 2 费群体 10/14）按上面那张表其实偏低
> （白卡 1 费群体就有 8–9），但那是你给的数值，我没有动。要调的话说一声。

---

## 目录结构

```
D:\桌面\sts2mod\
├─ Yetannia\                     ← Mod 工程
│  ├─ Yetannia.csproj            普通 net9.0 类库（刻意不使用 Godot.NET.Sdk）
│  ├─ Yetannia.json              Mod 清单（游戏靠它发现 Mod）
│  ├─ nuget.config               指向本地 NuGet 代理
│  ├─ Sts2PathDiscovery.props    自动定位游戏安装目录
│  └─ Code\
│     ├─ MainFile.cs             入口 [ModInitializer]，装载 Harmony 补丁
│     ├─ Loc.cs                  中英文切换小工具
│     ├─ ModAssets.cs            pck 内资源路径
│     ├─ ModSelfCheck.cs         启动自检（不需要可整个删掉）
│     ├─ Character\              角色、卡池、遗物池、药水池（含 4 个自定义场景路径）
│     ├─ Cards\                  卡牌基类（含先知触发、卡面分配）+ 82 张卡
│     ├─ Powers\                 能力（22 个具名能力 + 3 个支撑类）
│     ├─ Keywords\               先知关键词 + 本地化注入
│     └─ Relics\                 遗物基类 + 5 个遗物
│  └─ build\Yetannia.pck         Godot 导出的美术包（由 export-pck.ps1 生成）
├─ 卡牌表1.0.xlsx                ← 你给的设计表（命名与数值的来源）
├─ Yetannia-卡牌表.xlsx          当前实现的对照表（由 cards-xlsx.js 生成）
├─ Yetannia-v0.2.1-test.zip      ← 发给别人测试用的整包（由 package-mod.ps1 生成）
├─ README.md                     ← 面向访问者的说明（本开发日志在 docs\DEVELOPMENT.md）
└─ .tools\                       工具链（不属于 Mod，可随时删除）
   ├─ dotnet\                    便携版 .NET 9 SDK（9.0.318）
   ├─ godot\                     Godot 4.5.1（仅用来导出 pck）
   ├─ pckproject\                只含美术、没有 C# 的 Godot 工程
   │  └─ Yetannia\
   │     ├─ images\charui\       选人立绘 / 顶栏头像 / 描边
   │     ├─ images\card_portraits\            82 张卡各一张卡面（+ test/test2/blank 兜底）
   │     └─ scenes\              creature_visuals / rest_site / merchant / char_select
   ├─ export-pck.ps1             从 pckproject 导出 Yetannia.pck
   ├─ package-mod.ps1            构建 + 打包成可解压进 mods\ 的 zip
   ├─ mod-readme.txt             随包发出去的安装说明（脚本会拷成 mod 目录里的 README.txt）
   ├─ cards-xlsx.js              生成 Yetannia-卡牌表.xlsx（自带最小 OOXML/ZIP 写入器）
   ├─ rename-cards.js            按卡牌表批量改显示名（只改 CardLoc 的两个标题串）
   ├─ dump-card-names.js         打印每张卡当前的显示名（核对改名结果用）
   ├─ ffmpeg\                    从视频壁纸抽帧用
   ├─ nuget-proxy.js             本地 NuGet 代理
   ├─ dl.js / pck.js             下载器 / Godot PCK 解包器
   ├─ verify.ps1                 一键：构建 → 部署 → 启动 → 读自检
   ├─ watch-run.ps1              启动游戏并盯着日志，直到自检出现
   ├─ screenshot.ps1             截屏 / 模拟点击（受 UIPI 限制，见下）
   ├─ set-mod-enabled.js         直接开关 settings.save 里某个 Mod 的 is_enabled
   ├─ decomp-proj\               反编译的游戏程序集（查 API 用）
   └─ gamefiles\                 从游戏 .pck 里解出的本地化文件
```

---

## 卡牌总表（Excel）

工作区里有两个表，分工不同：

| 文件 | 是什么 |
|---|---|
| `卡牌表1.0.xlsx` | **你给的设计表**，命名与数值的来源。我只读取，不修改。 |
| `Yetannia-卡牌表.xlsx` | **当前实现的对照表**，由 `.tools/cards-xlsx.js` 生成，用来核对我实现得对不对。 |

`Yetannia-卡牌表.xlsx` 的结构：

> **v0.5.10 已更新**：卡表拆出了独立的「升级后效果」和「升级后花费」两列。
> 这两列不是新写的内容——卡面的敲后说明本来就以 `<基础效果>\n\n敲后：<变化>` 的形式存着，
> 生成器只是在 `敲后：` 处切开（尾部的 `※ …` 备注会留在基础效果那边），
> 升级后花费则从「费用 1→0」这句话里读，避免同一个数字存两份、日后走神。

| 工作表 | 列 |
|---|---|
| **卡牌总表** | 名称 / 类型 / 花费 / 升级后花费 / 稀有度 / 效果 / 升级后效果 |
| **对照（源文件）** | 名称 / 源文件 / 类型 / 花费 / 稀有度，表尾附关键词说明 |

重新生成（改了卡之后跑一次就行）：

```powershell
node D:\桌面\sts2mod\.tools\cards-xlsx.js
```

数据是**手写在脚本里**的 `cards` 数组，不是从程序集里读的——这是有意的：
卡牌文案在 `Localization` 里是带 `{Damage:diff()}` 占位符的模板，直接抓出来给填表用很难读，
所以表里写的是「渲染后」的说法（例如「造成 12 点伤害」而不是「造成{Damage:diff()}点伤害」）。
**改卡之后记得同步这个数组**，或者把这句当作已知的维护成本。

> 表格用 `.tools/cards-xlsx.js` 生成。环境里没有任何电子表格库，所以那个脚本手写了
> 最小 OOXML + ZIP（全部用 stored 不压缩，只需要 CRC32 和 local/central header），
> 不依赖 Node 的 zlib，也不联网。单元格用 `t="inlineStr"`，因此不需要 sharedStrings 部件。

---

## 已知行为（看着像 bug，其实是机制）

排查前先看这一节，免得把下面两条当成缺陷重查。两条都有日志证据，不是推测。

### 1. 一次预见里弃掉多张先知牌，靠后的几张"什么也没做"

**成因**：这一批里有伤害型先知牌（`ACCUMULATED_FATE` 厚积薄发、`PROPHETIC_CLEAVE`）打死了最后一个敌人，
`CombatManager.IsOverOrEnding` 就在**那张牌自己的结算过程中**翻真；此后所有效果类命令都会直接 early-return
（`PowerCmd.Apply`、`CardPileCmd.DrawInternal`、`DamageCmd` 等同一族标志），所以剩下的牌会打出
`begin`/`done` 却既无效果、也不涨先知累积。

**怎么认**：看 `[prophet]` 行上的 `overOrEnding=` 字段即可——后缀为空转的那批，翻转点永远在后缀第一张牌上
（它的 `begin` 还是 false、`done` 已经是 true）。

**实测**：两局共 76 次"门为真"的结算全部空转、341 次"门为假"的结算全部 +1，**零反例**。

### 2. 弃掉的牌又被抽回来了

**成因**：抽牌堆为空时抽牌会**把弃牌堆洗进抽牌堆**——这是原版机制，不是本 mod 的行为。若这次抽牌由
"被弃置时"的先知效果触发（引蛇出洞），你刚为过滤牌库弃掉的牌就会一起被洗回去。

**已经做过的缓解**：先知触发**不再插在预见弃牌的循环中间**，而是等一次预见的所有弃牌落盘后统一释放
（见 `Cards/ProphetQueue.cs`）。洗牌本身不变，但它不再发生在它所反应的那批弃牌进行到一半的时候。
改前 95%（37/39）的多触发批量里弃牌堆还在增长，改后为 0/34。
## 美术

> **当前策略：每张卡都有自己的卡面，角色形象是从模型渲染出来的逐帧动画。**
> 82 张卡各有一张 `card_portraits/<卡 id>.png`（两张先古卡是 608×856，其余 500×380）；
> `test.png` / `test2.png` / `blank.png` 只是「卡面无图」时的兜底，现在没有任何一张卡会用到它们。
> 选人立绘 / 顶栏头像 / 选人背景是自制贴图（桌面壁纸抽帧）；战斗形象 / 休息处 / 商人
> 是自制场景，播的是同一张模型图集 `images/creature/yetannia_atlas_0.png` 的逐帧动画。
> 遗物图标、费用 / 能量图标、地图头像现在也都是自制的，见「占位与后续」。

### 一、图片贴图（选人立绘 / 顶栏头像 / 卡面）

角色立绘来自你桌面壁纸（Wallpaper Engine 视频 `【千年之旅ELF】耶坦尼娅-维拉尔之梦`）的一帧：

1. `ffmpeg` 从 `l2t 2_tvai.mp4` 抽帧；
2. 裁成选人立绘比例（游戏原生是 132x195，这里出 4 倍图 528x780）和 85x85 的顶栏头像（出 340x340）；
3. 放到 `.tools/pckproject/Yetannia/images/charui/`；
4. `& .tools\export-pck.ps1` 用 Godot 导入并导出 `Yetannia\build\Yetannia.pck`；
5. `Yetannia.json` 里 `has_pck: true`，构建时会把 pck 一起复制进游戏。

产物与挂载点：

| 文件 | 尺寸 | 挂在哪 |
|---|---|---|
| `charui/char_select_yetannia.png` | 528x780 | `CustomCharacterSelectIconPath` / `LockedIconPath` |
| `charui/character_icon_yetannia.png` | 340x340 | `CustomIconTexturePath`（顶栏头像） |
| `charui/character_icon_yetannia_outline.png` | 340x340 | `CustomIconOutlineTexturePath`（描边） |
| `card_portraits/<卡 id>.png` | 500x380 | 每张卡自己的卡面（82 张各一张，`YetanniaCard.CustomPortraitPath`） |
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

改图之后**必须重跑 `export-pck.ps1`**，否则游戏里还是旧的。

> 关键点：游戏的 `CharacterSelectIcon` 是 `ResourceLoader.Load<CompressedTexture2D>()`，
> 需要 Godot 导入后的 `.ctex`，光丢一个 png 进 mods 目录是加载不到的——这也是必须走 Godot 的原因。

### 二、场景（战斗 / 火堆 / 商人 / 选人背景）

`CustomVisualPath` / `CustomRestSiteAnimPath` / `CustomMerchantAnimPath` /
`CustomCharacterSelectBg` 指向的是 Mod 自己的 `.tscn`，由 BaseLib 的 `NodeFactory`
在运行时**转换成游戏节点**：它按场景的 `ResourcePath` 反查注册过的工厂，
工厂再从场景里的 `Sprite2D` 纹理去构建 `NCreatureVisuals` / `NRestSiteCharacter` /
`NMerchantCharacter`。

| 场景文件 | 根节点 | 说明 |
|---|---|---|
| `scenes/creature_visuals/yetannia.tscn` | `Node2D` | 战斗形象，含 `Visuals`(Sprite2D) / `FormVfx` / `Bounds` / `CenterPos` / `IntentPos`，全部 `unique_name_in_owner` |
| `scenes/rest_site/yetannia_rest_site.tscn` | **`Sprite2D`** | 火堆形象 |
| `scenes/merchant/yetannia_merchant.tscn` | **`Sprite2D`** | 商人形象 |
| `scenes/char_select/char_select_bg_yetannia.tscn` | `Control` | 选人背景，一个铺满的 `TextureRect`（`expand_mode=1`, `stretch_mode=5`） |

选人背景**不走工厂**（`CharacterSelectBg` 只是把路径交给游戏，游戏自己 load+instantiate），
所以它保持普通 `Control` 就行；另外三个必须走工厂。

工厂对场景里的节点名和**节点类型**都有要求——名字对上但类型不对时，
基类 `ConvertNodeType` 会直接抛异常，BaseLib 又会 rethrow，转换就中途死掉。
下面这些是游戏自己 `_Ready` 里会 `GetNode` 的东西，一个都不能少：

| 目标类型 | 必须有的节点（`%` = 需要 unique name） |
|---|---|
| `NCreatureVisuals` | `%Visuals`(Node2D，工厂会警告但不会生成) / `Bounds`(Control) / `%IntentPos`(Marker2D) / `%CenterPos`(Marker2D) / `%FormVfx`(Control，可自动生成) |
| `NRestSiteCharacter` | `ControlRoot`(Control) / `%Hitbox`(Control) / `%SelectionReticle`(可自动生成) / `%ThoughtBubbleLeft`、`%ThoughtBubbleRight`(可自动生成) |
| `NMerchantCharacter` | 无 |

> 我们的战斗场景把 5 个节点全写全了（含 `%FormVfx`），所以工厂什么都不用生成。
> 火堆场景只给根 `Sprite2D` + 纹理，剩下的 `Hitbox` / `SelectionReticle` /
> 左右气泡都由工厂按纹理尺寸推出来——这是工厂的推荐用法。

> ⚠️ **火堆 / 商人场景的根节点必须是 `Sprite2D`**，工厂就是从根（或子）`Sprite2D` 的
> `texture` 去建节点的，根写成 `Node2D` 会拿不到纹理。

> ⚠️ **`.tscn` 不能被 Godot 导出成二进制 `.scn`**。默认导出会把文本场景转成
> `.scn` + `.remap`，于是运行时 `scene.ResourcePath` 变成
> `res://.godot/exported/...` 而不是我们注册的 `res://Yetannia/scenes/....tscn`，
> 工厂匹配不上，**转换会静默失效**（基础游戏自己的场景是原样 `.tscn` 发布的）。
> 已在 `.tools/pckproject/project.godot` 里关掉：
> ```ini
> [editor]
> export/convert_text_resources_to_binary=false
> ```
> 改完必须重新 `export-pck.ps1`，并用 `self-check scene load` 那几行确认
> 拿到的是 `NCreatureVisuals` / `NRestSiteCharacter` / `NMerchantCharacter`
> 而不是裸的 `Node2D` / `Sprite2D`。

---

## 构建与部署

```powershell
# 1) 若需要还原 NuGet 包，先起本地代理（会话结束后可关）
node D:\桌面\sts2mod\.tools\nuget-proxy.js 8899

# 2) 改了美术的话，先重导 pck
& D:\桌面\sts2mod\.tools\export-pck.ps1

# 3) 构建并直接部署进游戏 mods 目录
$env:DOTNET_ROOT = "D:\桌面\sts2mod\.tools\dotnet"
cd D:\桌面\sts2mod\Yetannia
& "D:\桌面\sts2mod\.tools\dotnet\dotnet.exe" build -c Release -p:DeployToGame=true
```

> ⚠️ 重新导出 pck 后，确认它里面装的是**文本** `.tscn` 而不是二进制 `.scn`：
> `.tools/pck.js` 列目录应该看到 `Yetannia/scenes/.../*.tscn`，
> 若出现 `.scn` / `.remap` 就说明 `export/convert_text_resources_to_binary=false` 没生效
> （见踩坑记录 4）。

或者跑一键脚本（会先关掉占用 DLL 的游戏进程、启动 Steam 与游戏、回报自检结果）：

```powershell
& D:\桌面\sts2mod\.tools\verify.ps1        # 构建 + 部署 + 跑一遍并读自检
& D:\桌面\sts2mod\.tools\watch-run.ps1     # 只跑并盯着日志（加载慢时更好用）
```

> 注意：装了 50 个 Mod 的环境下游戏从启动到 `ModelDb.Init` 可能要 1~3 分钟，
> `verify.ps1` 的等待时间有时不够，此时用 `watch-run.ps1`（默认等 600 秒）。

### 发布前必测（固定流程，不要跳）

**任何提版本、打包之前，都必须先跑一轮机器人实战复测。** 不要因为"改动很小"就跳过——
这个工作区里已经出现过两次"小改动"直接变成必崩或静默失效：一次是把偶发崩溃改成了 100% 必崩
（`.tools/qa/QA-RETEST2.md`），一次是修好一个问题却引出一个新的跨战斗崩溃（`QA-RETEST3.md`）。
单靠编译通过和自检渲染**抓不到**这类问题。

测试台在工作区 `YetanniaQA\`（独立 mod，不含任何 Yetannia 内容）。测法是让游戏**自带但被
retail 禁用的 AutoSlay 机器人**真打，外加卡池覆盖、只读探针和终局模式：

```powershell
# 启用测试台（测完记得关回去；settings.save 必须保持无 BOM）
node D:\桌面\sts2mod\.tools\set-mod-enabled.js `
  "C:\Users\<user>\AppData\Roaming\SlayTheSpire2\steam\<steamid64>\settings.save" YetanniaQA true

# 起一局：自动选人 / 卡池覆盖 / 遗物 / 探针 / 终局模式
Start-Process "D:\SteamLibrary\steamapps\common\Slay the Spire 2\SlayTheSpire2.exe" `
  -ArgumentList '--autoslay','--qagym','--qarelic','--qaprobe','--qawin','--seed=qa7' `
  -WorkingDirectory "D:\SteamLibrary\steamapps\common\Slay the Spire 2"
```

判定底线（每轮都要过）：

- 0 个 Yetannia 归属异常；所有 `[scry] #N BEGIN` 都有配对 `END`（0 THREW / 0 PENDING）
- `self-check failed` / `UNRESOLVED` / `MISSING power icons` 全 0
- 至少一局走到建筑师事件并回到主菜单
- 日志归档到 `.tools/qa/logs/`，结论写进 `.tools/qa/QA-RETEST*.md`

**打包后还要核对包内 DLL 的 SHA256 与被测构建一致**才算交付。哈希要从 zip 里解出来再取，
不要拿 `bin\Release` 代替——那证明不了归档里装的是哪一份。

> 已知覆盖不到的两块，别误以为测过了：① **真·预见选牌界面**——AutoSlay 自带 selector 直接
> 返回结果，`[scry] GRID` 全程为 0，所以真 UI 路径没被走过；② **联机**——单人局里那 5 张联机
> 卡是硬塞进手牌的，只能证明"塞进来不崩"。

运行游戏需要 **Steam 客户端处于运行状态**。

> **直启 exe 现在也能用了**（比走 `steam://rungameid/2868840` 方便，因为能控制在哪个进程上做自动化）：
> 在游戏根目录放一个 `steam_appid.txt`，内容 `2868840`，然后直接起 exe 即可，
> 日志里会看到 `Steam is running: True` + `Steamworks initialization succeeded!`。
> 两个前提：
> 1. **Steam 客户端不能以管理员身份运行**——否则它会以更高完整性启动游戏，
>    而高完整性进程**收不到**普通完整性进程发来的按键/点击（UIPI），自动化会静默失灵；
>    早期还会直接弹「Steam应用已崩溃，请尽快从 Steam 重新启动游戏」。
> 2. 长命令要用后台任务或 `Start-Process` 起，**不要**用前台 pwsh 直接跑 exe：
>    前台调用超过工具超时（约 120 秒）会被杀掉，并**连带杀掉子进程游戏**。

### 打包给别人测试

```powershell
& D:\桌面\sts2mod\.tools\package-mod.ps1              # 构建 + 打包
& D:\桌面\sts2mod\.tools\package-mod.ps1 -SkipBuild   # 复用上次构建，只重新打包
```

产出 `Yetannia-v<版本>-test.zip`（当前 ≈20 MB；正式发布时用 `-Out Yetannia-v1.0.0.zip` 指定名字）。
压缩包**顶层就是 `Yetannia/` 文件夹**，
所以「解压到 `...\Slay the Spire 2\mods\`」正好得到 `mods\Yetannia\...`——
不会像常见的「解压出一层同名目录」那样多套一层。

包内文件（**4 个，不含 `.pdb`**——Release 构建 `DebugType=none`，不再产生符号；
早期版本带过 `.pdb`，因为里面写死了构建机的源码绝对路径，已刻意移除）：

| 文件 | 说明 |
|---|---|
| `Yetannia.json` | Mod 清单，游戏靠它发现 Mod |
| `Yetannia.dll` | 代码 |
| `Yetannia.pck` | 美术与场景 |
| `README.txt` | 安装说明，来自 `.tools/mod-readme.txt` |

几个刻意的选择：

- zip 是用 `ZipArchive` **手写**的，不是 `Compress-Archive`：条目名强制用正斜杠、
  且不写目录条目。有些解压工具对这两点处理不一致，而 mod 目录一旦解压错位就完全不加载。
- 说明文件放在 **mod 文件夹里面**，这样压缩包顶层只有一个条目。
  Mod 加载器只认 `*.json` 清单，多一个 txt 不影响加载（已实测：日志里
  `Loading assembly DLL ...mods\Yetannia\Yetannia.dll` + `card pool : 82 card(s)` 正常）。
- `Yetannia.json` 里的 `author` 目前还是 `local-dev`，正式发出去之前建议改成你的名字。


### 依赖

- **BaseLib v3.4.7**：本机已通过 Steam 创意工坊安装（`workshop/content/2868840/...`），
  Mod 清单里声明了该依赖。若以后取消订阅，可把 `.tools\staging\` 里的
  `BaseLib.dll / .json / .pck` 复制到 `mods\BaseLib\` 作为本地替代
  （注意：**不要**同时保留工坊版和本地版，游戏会随机禁用其中一个）。

### 对游戏配置做过的改动

为了让验证能跑起来，我改过一处游戏设置，如需还原可以自行处理：

- 文件：`%APPDATA%\SlayTheSpire2\steam\<steamid64>\settings.save`
- 改动：把 `mod_settings.mod_list` 里 `Yetannia` 的 `is_enabled` 从 `false` 改成 `true`
  （原文件已备份为同目录下的 `settings.save.bak`）。
- 需要的话也可以在游戏内 Mod 列表里手动开关，效果一样。

---

## 继续加卡 / 加遗物

卡牌（丢进 `Code/Cards/`，命名空间保持在 `Yetannia.*` 下以便 ID 前缀正确）：

```csharp
public sealed class MyNewCard : YetanniaCard
{
    public MyNewCard() : base(1, CardType.Attack, CardRarity.Common, TargetType.AnyEnemy) { }

    protected override IEnumerable<DynamicVar> CanonicalVars => [new DamageVar(6, ValueProp.Move)];
    protected override void OnUpgrade() => DynamicVars.Damage.UpgradeValueBy(3m);

    protected override async Task OnPlay(PlayerChoiceContext ctx, CardPlay play)
    {
        ArgumentNullException.ThrowIfNull(play.Target);
        await DamageCmd.Attack(DynamicVars.Damage.BaseValue)
            .FromCard(this, play).Targeting(play.Target)
            .WithHitFx("vfx/vfx_attack_slash").Execute(ctx);
    }

    public override List<(string, string)> Localization =>
        Loc.Pick(new CardLoc("中文名", "造成{Damage:diff()}点伤害。"),
                 new CardLoc("Name", "Deal {Damage:diff()} damage."));
}
```

带先知的卡：在上面基础上加 `CardKeyword` 并重写 `OnProphet`（触发时机由基类处理，不用自己判断牌堆）：

```csharp
public override IEnumerable<CardKeyword> CanonicalKeywords => [YetanniaKeywords.Prophet];

protected override async Task OnProphet(PlayerChoiceContext ctx)
{
    // 从抽牌堆被弃置时发生的事。不能在这里请求玩家做选择。
}
```

遗物（丢进 `Code/Relics/`，同样继承 `YetanniaRelic`）只需设 `Rarity` 和 `Localization`，
再按需重写战斗钩子（`AfterPlayerTurnStart`、`AfterCardChangedPiles`、`AfterCombatVictory` 等）。

`ModSelfCheck.cs` 会自动把新内容也报出来（含基础数值和升级后数值），加完卡直接跑 `verify.ps1`
就能确认注册、本地化与数值是否都正确。

> 若新加的卡一开始没生效，先确认游戏 Mod 列表里 Yetannia 是**启用**状态——
> 游戏对没启用过的 Mod 会写 `is_enabled: false` 并直接跳过加载。

---

## 预见卡死的排查（`[scry]` 追踪）— `Code/Diagnostics/ScryTrace.cs`

测试者报告过「挥舞 / 其他预见牌有时候卡在屏幕中间不结算」。

**已定位并修复（v0.5.8）。** 定位过程本身值得留着：

v0.5.7 先**只加观测、不改任何行为**——把本 Mod 的每一次预见都改走 `ScryTrace.Run`
（卡牌的 `YetanniaCard.Scry`，加四个直接调 `ScryCmd` 的地方：`ProphetsEye` /
`ProphetsEyePlus` / `ForesightPower` / `DelayedScryPower`）——然后拿到测试者那份
125 MB 的 `godot.log`，里面的轨迹直接把根因指了出来。

每次预见留一对日志：

```
[scry] #3 BEGIN GlimpseFate amount=1 drawPile=9 ctx=BranchingPlayerChoiceContext turn=4 inFlight=1
[scry] #3 END   GlimpseFate elapsed=812ms discarded=0
```

如果卡死，就**只有 BEGIN、没有 END**，10 秒后再跟一条错误：

```
[scry] #3 STILL PENDING after 10s: ... — the scry never returned
```

| 字段 | 含义 |
|---|---|
| `#N` | 本次进程内的第几次预见（用来配对） |
| `label` | 发起的卡牌类名 / 遗物名 / 能力名 |
| `drawPile` | 当时的抽牌堆张数 |
| `ctx` | 当时的 `PlayerChoiceContext` 类型 |
| `turn` | 回合数（1 = 开场那一回合） |
| `inFlight` | **当时有几个预见还没结束**（≥2 = 重叠） |
| `elapsed` / `discarded` | 返回耗时 / 玩家弃掉几张 |

### 为什么专门记 `inFlight`

自检跑通那次留下了这样一段（重叠是自检往手里硬塞牌造出来的，正常游玩不会这样）：

```
#1 BEGIN ProphetsEye  amount=5 ctx=HookPlayerChoiceContext     inFlight=1
#2 BEGIN GlimpseFate  amount=1 ctx=BranchingPlayerChoiceContext inFlight=2   ← 两个预见同时在飞
     Player 1 chose cards []
#2 END   GlimpseFate  elapsed=3ms discarded=0
#3 BEGIN GrandProphecy amount=6                                 inFlight=2
     Player 1 chose cards []
#3 END   GrandProphecy elapsed=0ms
     Player 1 chose cards [5 张]        ← 这 5 张才是遗物那个界面的答案
#1 END   ProphetsEye  elapsed=7325ms discarded=5
```

它证明了一件要紧的事：**卡牌选择的应答是「环境级」的，不绑定到具体请求上。**
第一个预见还在等玩家，第二个预见照样能被创建、并被**当时装着的那套选择器**答掉。
一旦 A 的答案被吞给了 B，A 就永远等不到返回 —— 牌就停在屏幕中间不结算。
`inFlight` 就是用来抓这个的。

### 根因（v0.5.8 已修）

`ScryThresholdPower`（预见之力 / 预见之敏 的基类）**没有 `CanonicalVars`**，
所以那个 `Threshold` 动态变量**根本不存在**。于是两头都炸：

- 卡牌 `OnPlay` 里写 `power.DynamicVars["Threshold"].BaseValue` → `KeyNotFoundException`；
- `ScryThresholdPower.AfterScryed` 里读它 → 同样 `KeyNotFoundException`。

**要命的是第二个。** `AfterScryed` 是 BaseLib 的 `IAfterScryed` 回调，由 `ScryCmd` 在
**预见内部**派发。异常从那里抛出去，会一路穿出 `ScryCmd`、穿出卡牌的 `OnPlay`，
于是这次出牌以异常收场——**牌就停在屏幕中间不再结算**。测试者日志里的轨迹：

```
[ERROR] [scry] #71 THREW CutThroughFate after 2803ms: KeyNotFoundException: ... 'Threshold' ...
   at Yetannia.YetanniaCode.Powers.ScryThresholdPower.AfterScryed(...)   ScryThresholdPower.cs:line 58
   at Yetannia.YetanniaCode.Diagnostics.ScryTrace.Run(...)               ScryTrace.cs:line 61
   at Yetannia.YetanniaCode.Cards.YetanniaCard.AfterCardChangedPiles(...)
   at Yetannia.YetanniaCode.Cards.YetanniaCard.ResolveProphet(...)
   at Yetannia.YetanniaCode.Cards.CutThroughFate.OnPlay(...)
```

中招的路径（日志里实际出现的）：先制 `CutThroughFate`、运筹帷幄 `TestSkill`、
高举旗帜 `Divination`、延时预见 `DelayedScryPower`、先知触发 `ResolveProphet`、
纯爱形态 `PureLoveFormPower`，以及 `ScryAgility.OnPlay` 自己写变量时。

**这解释了「有时候」**：只有当「预见之力 / 预见之敏」已经在场时才会触发；
一旦它在场，**之后每一次预见都会炸**。

修法：

1. `ScryThresholdPower` 补上 `CanonicalVars`，把 `Threshold` 变成真实存在的动态变量；
2. 加 `SetThreshold(int)` 让卡牌安全写入，`ThresholdOf()` 安全读取——
   这两个方法**都不允许抛异常**，因为在这里抛异常等于直接把玩家正在打的牌卡死；
3. 两张能力牌的文案从 `{Threshold}` 改成 `{Threshold:diff()}`（原来那个写法会报
   `No source extension could handle the selector named "Threshold"`，日志里 45 次）；
4. **自检补上了「能力牌描述」这一整块**——它原来只渲染卡牌和遗物，所以 `{Threshold}` 这种
   错才会一路漏到测试者手里。

> `PowerModel` 没有 `DynamicDescription`（它的注释自己都写了：「Unlike other models'
> DynamicDescription, this doesn't include any variables」），所以得照 `HoverTips` 的做法手工拼：
> 取 `powers` 表里的条目 → `DynamicVars.AddTo(loc)` → `GetFormattedText()`。
> 另外**必须用 `ModelDb.Power<T>().ToMutable()`**，直接拿 `ModelDb.Power<T>()` 得到的是
> canonical 实例，读 `DynamicVars` 会抛 `CanonicalModelException`。
>
> 判定「没渲染干净」有两个条件、别只写一个：文本里还剩 `{`，**或者渲染本身抛了异常**
> （后者连占位符都还没机会出现，只查花括号会把它当成通过）。

> 另外，`AfterScryed` 里那个 `inFlight` 重叠理论**不是**本次的原因，那个重叠是自检
> 自己造出来的。它仍然值得留着——见上一节。

### 复验结论：纯爱形态 + 嵌套预见 —— 干净

测试者日志里有一条落在这条路径上的报错：

```
GameAction GenericHookGameAction ... source POWER.YETANNIA-PURE_LOVE_FORM_POWER ...
  last involved CARD.YETANNIA-CUT_THROUGH_FATE ...
  completed with exception: (An attempt was made to transition a task to a final state when it had already completed.)
```

先制 / `CutThroughFate` 正是一张带预见的牌，所以嫌疑是「纯爱形态自动打出一张自己也要做选择的牌」
这条嵌套选择路径有问题。**已用脚本化场景复验，结论是没问题。**

场景（`Code/Diagnostics/PureLoveCheckHarness.cs`，flag `purelove.flag`）：
挂上纯爱形态 → 把「先制」放进抽牌堆 → 直接驱动 Draw→Discard（这就是纯爱形态唯一监视的东西，
比真打一张预见牌更确定）→ 再等异步的 hook game action 跑完。

v0.5.8 上的实际日志：

```
[purelovecheck] 纯爱形态 applied: True
[purelovecheck] YETANNIA-CUT_THROUGH_FATE into draw pile (pile=Draw)
[purelovecheck] Draw -> Discard transition completed
[scry] #2 BEGIN CutThroughFate amount=2 drawPile=9 ctx=BranchingPlayerChoiceContext turn=1 inFlight=1
[scry] #2 END   CutThroughFate elapsed=247ms discarded=0
```

嵌套预见**正常返回**（247 ms，`ctx=BranchingPlayerChoiceContext`），`inFlight` 始终是 1。
整份日志里 `transition a task to a final state` **0 次**、`PureLoveFormPower` 的栈帧 **0 个**、
GameAction 失败 **0 次**。

**所以那条报错是 v0.5.7 `ScryThresholdPower` 抛异常、任务 faulted 之后的余波**，
根因修掉后自然消失。

> 另外确认过：`PureLoveFormPower` 里那四行（构造 `HookPlayerChoiceContext` →
> `AssignTaskAndWaitForPauseOrCompletion` → `InvokeExecutionFinished`）与 BaseLib 自己的
> `HookUtils.DispatchWithContext` **逐字一致**，不是误用 API。
> 而 `BranchingPlayerChoiceContext` 的类注释自己写着这套 API
> 「very experimental and needs proving out in real testing」——这块以后仍然值得盯。

### 附带发现：测试者那份日志为什么有 125 MB

**和本 Mod 无关。** 日志里 105 万行中有 5.8 万次同一个异常：

```
System.MissingMethodException: Method not found:
  'MegaCrit.Sts2.Core.Bindings.MegaSpine.MegaAnimationState.SetAnimation(System.String, Boolean, Int32)'
   at AncientWaifus.Core.GlobalTouchHook.HandleGlobalInput(InputEvent event)
   at AncientWaifus.Core.GlobalInputCatcher._Input(InputEvent event)
```

`AncientWaifus` 挂了个全局输入捕获节点，**每一个输入事件都会抛一次** MissingMethodException
（它对不上当前游戏版本的 `MegaAnimationState.SetAnimation` 签名），而且异常日志本身
又抛 `NullReferenceException`，于是每次都吐出整段 C# backtrace。58,467 × 约 20 行 ≈ 125 MB。

**该让测试者删除或更新 `AncientWaifus`**，否则日志永远是几百 MB、别的信息全被淹没。

### 自检开关（在 `mods\Yetannia\` 下建空文件）

| 文件 | 作用 |
|---|---|
| `scrycheck.flag` | 下一场战斗自动跑两个预见场景，**用自动选择器**回答，不用人点 |
| `scrycheck.ui.flag` | 同上，但**必须真人点选牌界面**，用来验证真实 UI 路径 |

两个都是**每次启动只跑一次**，跑完就该删掉 —— 不删的话每局战斗开场都会被塞两张牌进来。
`ScryCheckHarness` 挂在 `NCombatRoom._Ready` 上，而那个钩子**可能早于本地玩家就绪**，
所以里面是「最多轮询 20 秒等玩家」，不是拿到就干（早期版本在这里直接放弃，
于是 "no local player; aborting" 让整次测试静默失效过一次）。

---

## 游戏侧需要打补丁的地方

有些问题是**游戏的既有代码不处理自建角色**，只能在 Mod 侧打补丁。

### 建筑师（The Architect）无法结算 — `Code/Patches/ArchitectNullDialoguePatch.cs`

`TheArchitect.DefineDialogues()` 把每个原版角色的对话硬编码在 C# 里，而 `AgnosticDialogues`
是空的；`LoadDialogue()` 又用 `allowAnyCharacterDialogues: false` 去取。对自建角色来说
`GetValidDialogues` 返回**空列表**，`Rng.NextItem` 返回 `default`，于是 `Dialogue` 是 null。

`Dialogue` 为 null 在别处都没事（`GenerateInitialOptions` 有判空、`PlayCurrentLine` 有判空），
**只有 `WinRun` 连续两次无保护地解引用 `Dialogue.EndAttackers`**（`TheArchitect.cs` 353/354 行）。
所以走到终点、点「继续」的那一刻会抛 NullReferenceException，这一局永远结算不了。

修法是给 `WinRun` 加一个 Harmony **prefix**：如果 `Dialogue` 是 null，就塞一个
`new AncientDialogue("")`（`EndAttackers = None`）进去，然后照常跑原方法。

- 只有原本是 null 时才动手，**原版角色完全不受影响**。
- `new AncientDialogue("")` 只有**一行且那行的 `LineText` 是 null**，
  `PlayCurrentLine` 遇到 null 会直接 return，所以**什么都不会说**——正好是「对话留空」。
- 用构造函数没法造「0 行」的对话（`sfxPaths.Length == 0` 会抛），所以是 1 行空行而不是 0 行；
  这也刚好让 `GenerateInitialOptions` 直接给出 PROCEED，和没有对话时的表现一致。
- 自检里有一行 `self-check architect : target=True prefixes=1`，用来确认补丁真的挂上了
  （`PatchAll` 会因为读不到补丁类而**静默跳过**，不验证等于没打）。

> 排查过程中确认过：其它先古事件的 `Dialogue` 读取都有判空，只有建筑师这一处是裸的。

### 水色之舞 的「只能对意图攻击的敌人打出」 — `Code/Patches/CounterStrikeTargetPatch.cs`

这条规则**一个钩子表达不完**，因为最自然的那个钩子拿不到目标：

- `AbstractModel.ShouldPlay(card, autoPlayType)` 是游戏判定「这张牌能不能打」的地方
  （`CardModel.CanPlay` 会问它），但它的签名里**没有目标**，所以只能写成
  「场上至少有一个敌人的意图是攻击」——这是**必要条件**，不是完整规则。
  保留它的好处是：场上没人要打你时，这张牌会直接在手牌里变灰。
- `CardModel.CanPlayTargeting(Creature? target)` **是**带目标的，而且正是手动出牌走的那个关口：

  ```
  NCardPlay（拖拽反馈） -> CanPlayTargeting(target)
  NCardPlay（松手）     -> CardModel.TryManualPlay(target) -> CanPlayTargeting(target)
                           -> EnqueueManualPlay -> PlayCardAction
  ```

  所以在这里加一个 Harmony **postfix**，把「目标是意图攻击的敌人」补上。
  补丁只对 `CounterStrike` 生效、只会把结果由 true 改成 false，原版卡完全不受影响。

自检里有一行 `self-check counter : target=True postfixes=1` 用来确认补丁真的挂上了。

### 自建角色的先知 / 重放 / 能力牌

见上面「先知触发要『等效打出』」一节——那些是 Mod 自己的行为，不需要补丁。

---

## 占位与后续

1. **选人立绘 / 顶栏头像 / 选人背景 / 战斗形象 / 火堆 / 商人 都已经是耶坦尼娅了**
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
   或者直接改 `Localization` 里的字符串。
5. 「预见」目前只是描述文字，不是可悬停的关键词。如果想让它像「先知」一样可悬停，
   可以给卡牌加 `HoverTipFactory.Static(BaseLibTip.Scry)`（`DarvsProphecy` 里已有示例）。

---

## 需要你确认的设计点

### 这一轮（卡牌表 1.0）留下的问题

**已按你更新后的表修掉的：**

- ~~「试探」重名~~ → 白卡 `JustLucky` 改名为 **试探打击**（英文 `Probing Strike`），
  初始卡 `OminousDecree` 保留「试探」。
- ~~重整旗鼓 / 全力进攻没有敲后效果~~ → 按表补上：
  重整旗鼓敲后把范围从抽牌堆扩到「抽牌堆 + 弃牌堆 + 手牌」（**始终只取状态牌**，敲后拓宽的是查哪些牌堆）；
  全力进攻敲后自身费用 1→0。两张都不再是不可升级。
- ~~重整旗鼓「抽牌堆/全部」有歧义~~ → 表里写明了：基础只查抽牌堆，敲后才是全部。

**还需要你定的：**

1. **第 38 行没有名字**（技能 / 2 费 / 蓝：16 格挡 + 自加 1 层虚弱 + 下回合 1 费）。
   我先用 **「未命名」** 占位（`UnnamedTechnique.cs`），等你给名字。
2. **英文名是我起的**：表里只有中文名，英文标题（`Loc.Pick` 的第二个参数）是我按中文意译的。
   例如「修顿」我没把握是名字还是「修盾」的笔误，暂时音译成 `Xiudun`。要改直接说。
3. **厚积薄发的计数口径**：「你每拥有 1 张先知牌」按基础游戏缩放攻击牌的口径实现——
   统计**战斗中所有己方牌堆**（手牌/抽牌堆/弃牌堆/消耗堆/出牌堆）里带先知关键词的牌，
   所以**它自己也算一张**。想改成只数手牌、或不算自己，都可以调。
4. **韬光养晦会立刻结束回合**（按原文「结束你的回合」的字面实现）。
   如果你其实想要「保留手牌 + 置顶 + 下回合给费，但不结束回合」，去掉最后一步即可。

### 更早批次遗留的问题

5. **运筹帷幄的「抽等量的牌」**：实现为「抽回等于你放回牌堆顶的张数」，手牌数量保持不变。
6. **请君入瓮（原 test 攻击）的先知效果**：对随机目标打出此牌（用当前伤害），然后伤害翻倍；
   本场战斗内永久且可叠加（打出 12 → 留 24 → 打出 24 → 留 48），费用不变。
7. **先知累积的计数**：用一张可见的「先知累积」增益记录本场战斗触发次数（方便你自己看数字），
   如果你希望它隐藏起来，我可以改。
   计数在**先知效果结算之后**才 +1，所以预见打击自己的那次先知触发用的是触发前的层数；
   想改成「先加层再结算」的话说一声。
8. **积厚成势的先知叠加**：打出时把数字设为 2/3；之后每次先知触发 +2/3，封顶 8/12；
   如果先知在打出前就触发，也会先累加（打出时再叠加一次基础值）。
   若你想要「无论触发几次都封顶 8/12、且打出前不累计」，告诉我我改。
9. **合击（原厄运宣告·超越）**：类型与费用沿用了被替换的初始卡（技能 / 1 费），
   但它同时造成伤害——如果你希望它改成攻击牌，说一声。
   另外「敲后不增加易伤虚弱、费用变 0」我理解成**伤害的 15 → 20 仍然保留**。
10. **引领之光（达弗）**是挂在「陈旧的书卷 / Dusty Tome」奖励池里的（BaseLib 的 `ITomeCard` 机制），
    达弗的事件本身不动。若你想让它出现在达弗的其他选项里，需要另外做。
11. **预备不可升级**——你更新后的表里第 13 行仍然写着「不可升级：没有敲后效果」，那就按表的来。
12. **数值比例**：现在是攻击 32% / 技能 45% / 能力 21%（另有 2 张状态牌），原版均值是 36/43/21。
    技能占比略偏高、攻击偏低——你补卡时优先补攻击牌更容易贴回原版比例。
    （口径：82 张全部计入，26 攻击 / 37 技能 / 17 能力 / 2 状态；上面第 545 行的原版基准表是按角色分的。）
13. ~~先古卡（合击 / 引领之光）和白蓝卡共用 `test.png`~~ → 已各有一张 608×856 的竖幅卡面
    （槽位 598×842，和普通卡的 500×380 / 250×190 不是一套比例）。

---

## 工具链备注

这套环境有几个绕不开的坑，已在工程里处理好：

- **沙箱内 Windows schannel 不可用**，`dotnet` / `curl` 的 HTTPS 会直接失败。因此写了一个 Node
  本地 NuGet 代理（`nuget-proxy.js`，Node 用 OpenSSL 所以正常），把 `https://api.nuget.org`
  以纯 HTTP 暴露给 dotnet；`nuget.config` 指向它。
- **旧版 Windows PowerShell 5.1 会把无 BOM 的 `.ps1` 当 ANSI 读**，脚本里出现中文路径会乱码。
  `.tools` 下的脚本因此全部只用 ASCII，路径从 `$PSScriptRoot` 推导。
- **游戏进程比普通 shell 权限高**（Steam 启动的），`Stop-Process` 会 Access denied，
  要用 `Invoke-CimMethod -MethodName Terminate` 才能关掉。
- **游戏窗口不能被脚本模拟点击**（UIPI 会拦掉低权限进程发往高权限窗口的输入），
  所以 `screenshot.ps1` 只能截屏、无法自动点进选人界面。美术是否显示正确是靠
  `self-check art` 那两行（直接读 `CharacterSelectIcon` / `IconTexture`）来验证的。

`.tools\decomp-proj\` 是 ILSpy 反编译出的游戏源码（查 API 时非常好用），
`.tools\pck.js` 可以解包游戏 `.pck`（Godot 4 PCK v3 格式）取本地化等资源。
`.tools\gamefiles\` 是从游戏 pck 里解出来的全部本地化文件，写卡牌文案时可直接对照基础游戏用词。

---

## 联机支持（v0.5.9）

**这个 Mod 现在支持联机，共有 6 张联机专属牌。**

### 联机专属是怎么实现的

游戏自带 `CardMultiplayerConstraint`（`Entities/Cards/CardMultiplayerConstraint.cs`：
`None / MultiplayerOnly / SingleplayerOnly`）。`CardPoolModel.GetUnlockedCards` 会按
`RunState.CardMultiplayerConstraint`（由人数推导：`Players.Count <= 1 ? SingleplayerOnly : MultiplayerOnly`）
**自动筛掉**不该出现的牌。所以卡上只要写一句：

```csharp
public override CardMultiplayerConstraint MultiplayerConstraint => CardMultiplayerConstraint.MultiplayerOnly;
```

单人局里它就不会出现在任何牌池、奖励或商店，**不需要手写任何回避逻辑**。

> **Mod 清单里没有任何联机字段**——`ModManifest` 全部字段只有
> id/name/author/description/version/has_pck/has_dll/dependencies/affects_gameplay/min_game_version。
> 联机只比对 `affects_gameplay` 的 Mod 列表（`PeerVersionInfo`），所以
> **所有玩家必须装同一套 Mod 且版本一致**。

### 联机专属的 6 张牌

| 牌 | 费 | 稀有度 | 类型 | 效果 |
|---|---|---|---|---|
| 先知的指引 `GuidanceOfTheProphet` | 1 | 金 | 技能 | 从 3 张随机能力牌中选 1 加入手牌并本回合免费打出（敲后那几个选项是已升级的）；然后**此牌**进入随机一名队友的弃牌堆 |
| 归途终尽之景 `EmberBoon` | 1 | 金 | 技能 | 指定一名队友；本场战斗中他每消耗一张牌，随机生成一张牌加入其手牌（敲后为已升级的）。不可叠加 |
| 身先士卒 `SharedFocus` | 1（敲后 0） | 蓝 | 能力 | 所有玩家获得 1 点敏捷 |
| 天之恩典 `SharedRegen` | 0 | 白 | 技能 | 所有玩家获得 2/3 点再生，消耗 |
| 先知的援助 `GiftOfTime` | 3（敲后 2） | 蓝 | 技能 | 指定一名队友：他本回合结束时获得一个额外回合；然后结束你的回合 |
| 回应愿景之心 `SharedMight` | 1（敲后 固有） | 蓝 | 能力 | 指定一名队友：本场战斗中当你获得力量 / 敏捷（不因此牌）时，他获得等量 |

单机牌共 82 − 6 = **76 张**。

### 每张牌照的原版参考

- **先知的指引** = 富足 `Abundance`（选 1 张 → `CardSelectCmd.FromChooseACardScreen` →
  `SetToFreeThisTurn` → `AddGeneratedCardToCombat`）＋ 魔球 `TheBall`（覆写
  `GetResultLocationForCardPlay` 把打出的牌送去队友）。
  ⚠️ `CardPileCmd.GiveToAnotherPlayer` 的文档明确写着**不要从 `OnPlay` 里调用它**
  （出牌后的钩子会在接收方身上触发）——必须走 `GetResultLocationForCardPlay`，
  引擎自己在 `CardModel.OnPlayWrapper` 里会调用它。
- **归途终尽之景**（旧稿代号「薪火」，模型 id 仍是 `YETANNIA-EMBER_BOON`）= 树枝 `BurningSticks` 的
  `AfterCardExhausted`；「不可叠加」用
  `PowerStackType.Single` **再加**施放前的 `GetPower<EmberBoonPower>()` 查重——
  Single 只挡同一种能力叠层，挡不住「基础版和升级版各挂一个」。
- **身先士卒 / 回应愿景之心**（旧稿代号「同调 / 共鸣」）= `Rally` / `Plot` 的「所有玩家」写法：
  `TargetType.AllAllies` +
  `GetTeammatesOf(Owner.Creature)`（**它包含自己**）+ `PowerCmd.Apply` 的集合重载。
- **先知的援助**（旧稿代号「时之礼」，模型 id 仍是 `YETANNIA-GIFT_OF_TIME`）= 额外回合不是命令，
  而是模型上的两个钩子 `ShouldTakeExtraTurn` /
  `AfterTakingExtraTurn`（原版范例 `AmbergrisPower`）；结束自己回合用
  `PlayerCmd.EndTurn(Owner, canBackOut: false)`——**返回 void，不能 await**，照 `VoidForm`。

### 老牌的联机安全性（已逐个核对）

所有跨玩家钩子（`AfterScryed` / `AfterCardExhausted` / `AfterCardDrawn` /
`AfterPlayerTurnStart` / `AfterShuffle` / `BeforeSideTurnEnd` / `BeforeHandDraw`）
**每一个都按「这是不是我的」过滤过**（`player != Owner.Player`、`participants.Contains(Owner)`、
`ReferenceEquals(card, this)` 等），所以联机下 A 的预见不会触发 B 的能力。
事件补丁用的是 `EventModel.Owner`（事件归属的玩家）而不是本地玩家，两端选项不会不一致。

> **仍未验证**：没有真的跑过双人局。上面全部是从原版实现和 API 契约推出来的，
> 逻辑上站得住，但「两张牌同时生效」的实际手感没测过。新牌里最先该测的是
> 先知的指引（选牌 + 跨玩家给牌同时发生）和先知的援助（额外回合 + 结束回合）。
