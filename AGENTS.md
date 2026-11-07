# AGENTS.md — 自动化代理入口

> **每次在本仓库做任何更新、修复或发布之前，先完整阅读 [`docs/RELEASE-WORKFLOW.md`](docs/RELEASE-WORKFLOW.md)，
> 并严格按它的清单执行。** 那个文件记录的是已经真实踩过、并且发出去过的坑，不是建议。

## 每次更新都必须满足的 6 条（细节见 workflow）

1. **卡牌表双档**：`Yetannia-卡牌表.xlsx` 必须同时维护「原版」和「东尼测试版」两档数值（workflow §6.1），
   生成器 `.tools/cards-xlsx.js` 会拒绝在漏维护时生成。
2. **独立 subagent 做 QA**：上传前必须由**另一个** subagent 跑实机验收，不能自己验自己（§7.1）；
   覆盖面必须包括**战斗 + 营火 + 商店**，以及本轮改动影响的其它场景；只看战斗的 sweep 算「未完成」。
3. **程序代替鼠标**：QA 与截图一律程序驱动（`PrintWindow` + `SW_SHOWNOACTIVATE`、`PostMessage`、
   游戏自带 `--autoslay`/QA harness），**不得接管用户的鼠标或键盘**、不得把游戏窗口置顶（§7.2）。
4. **git 安全与隐私**：推送/发布前必须过安全与隐私检查（§8）；`README.md` 与 zip 内 `README.txt`
   是**写给用户看的**（安装、兼容性、更新内容、反馈方式），不是给实现者看的（§8.3）。
5. **收尾清理**：本轮结束前删除临时产物——QA 原始连拍、复制的浏览器/Steam profile、解密 cookie 临时文件、
   scratch 解包目录、`*.bak`；只保留报告引用的证据与下一轮需要的产物（§11）。
6. **诚实汇报**：按 §10 说明发布内容、哈希、测过什么，以及**明确列出没有验证的部分**。

## 快速定位

| 需要做的事 | 位置 |
|---|---|
| 发布流程 / 检查清单 | `docs/RELEASE-WORKFLOW.md` |
| 联机测试方法 | `docs/MULTIPLAYER-TESTING.md` |
| 开发与历史 | `docs/DEVELOPMENT.md` |
| 版本号 | `Yetannia/Yetannia.json`、`.tools/mod-readme.txt`（用 `.tools/bump-version.ps1`） |
| 卡牌数值两档 | `Yetannia/Code/Config/CardBalance.cs`（`Original` / `TonyTest`） |
| 联机档位同步 | `Yetannia/Code/Config/CardBalanceSync.cs`（客机跟随主机） |
| 卡牌表生成 | `.tools/cards-xlsx.js` → `Yetannia-卡牌表.xlsx` |
| 打包 / 上传 | `.tools/package-mod.ps1`、`.tools/make-workshop.py`、`.tools/uploader/win/ModUploader.exe` |
