# 频道 AI 配音（`.tools/tts/`）

> **以后所有视频统一用这里的 `channel` 声线**（可换 preset，但不要再临时换第三方配音工具）。
> 默认参数在 `presets.json`；改声线只改这一个文件，已生成的音频不要手改。

## 一、先看结论：B 站主流 AI 配音是什么

查了 B 站上热度较高的 AI 配音测评、教程和实际使用场景，主流大致分四类：

| 路线 | 典型工具 / 声线 | 用在哪 | 备注 |
|---|---|---|---|
| **剪映 / 必剪内置配音** | 吴敏霞（免费、使用频率最高的免费女声）、真人播客女、慢播讲故事（会员）、台湾腔甜妹、解说小帅 / 解说小哥等 | 影视解说、资讯盘点、营销号、游戏短视频 | B 站“从夯到拉锐评剪映几个热门的 ai 配音”把这几个列为热门选项：吴敏霞和真人播客女免费且高频，慢播讲故事是会员向、台湾腔甜妹偏温柔；缺点是同质化严重，API 不可得 |
| **微软 Edge TTS（edge-tts）** | 云希（Yunxi）、晓晓（Xiaoxiao）、云健（Yunjian） | 技术 / 工具 / 游戏区、教程、字幕组 | 免费、无字数限制；B 站大量“营销号 AI 配音”“AI 自动翻译配音”教程用的就是它 |
| **GPT-SoVITS / IndexTTS / RVC 克隆** | up 主自己的声纹，或角色 / 梗声线 | 整活、角色配音、个人风格频道 | 效果取决于参考素材；需要 1–3 分钟干净人声，素材版权要自己确认 |
| **商业 TTS** | 火山引擎（豆包）、阿里云、腾讯智影、魔音工坊 | 商单、批量口播 | 有免费额度但需要账号/付费；B 站“解说猫 TTS”这类教程会横向对比 indextts2、火山豆包、阿里云、edge |

**为什么我们自己用 edge-tts 做底**：
1. 剪映的热门声线（吴敏霞、慢播讲故事等）没有公开 API，只能手动进剪映点选，无法在视频流水线里自动批量生成；而且这几个声线 B 站上已经用得很滥。
2. GPT-SoVITS 克隆需要参考人声，现有素材要么有版权风险，要么是别的 up 主/角色的声线，不适合做固定频道声。
3. edge-tts 免费、可脚本化、音色稳定，配合固定的 EQ / 压缩 / 响度处理可以做出**我们自己的频道声线**——同一个 preset 每次输出一致，不会今天一个声音明天一个声音。

## 二、我们自己的声线

当前默认 preset：**`channel`（频道女声，播客/解说感）**

| preset | 底声 | 处理 | 适用 |
|---|---|---|---|
| `channel`（默认） | 晓晓 Xiaoxiao | 语速 -2%、音高 -6Hz、暖色 EQ、轻度压缩、-16 LUFS | 常规视频/模组介绍/更新说明 |
| `podcast` | 晓晓 | 语速 +2%、音高 -10Hz、更松弛的压缩 | 长口播、闲聊向 |
| `male` | 云健 Yunjian | 语速 +3%、音高 -5Hz | 游戏解说、燃向 |
| `youth` | 云希 Yunxi | 语速 +6% | 资讯、整活、快节奏 |

试听样音在 `samples/`：
- `samples/channel.mp3`、`samples/podcast.mp3`、`samples/male.mp3`、`samples/youth.mp3`
- `samples/channel-srt.mp3` + `.srt`：带逐句字幕的版本
- `samples/script-demo/`：分镜脚本模式产物（`audio/shot-*.mp3` + `voice.mp3` + `subtitles.srt` + `props.json`）

## 三、用法

需要 `edge-tts`（已在 `~/.local/bin`）和 `ffmpeg`（已随仓库 `.tools/ffmpeg/` 提供）。

```powershell
# 1. 一句话 / 一段文案 -> 一条配音
python .tools\voice\voice.py --text "大家好，这里是耶坦尼娅频道。" --out voice.mp3

# 2. 同时出逐句 SRT
python .tools\voice\voice.py --text "……" --srt --out voice.mp3

# 3. 分镜脚本（推荐给视频流水线）：每镜一条音轨 + 总音轨 + 字幕 + 帧级 props
python .tools\voice\voice.py --script script.json --outdir build/voice

# 4. 换 preset / 临时调参
python .tools\voice\voice.py --text "……" --preset male --out voice.mp3
python .tools\voice\voice.py --text "……" --preset channel --rate=-8% --pitch=-10Hz --out voice.mp3

# 5. 看看有哪些 preset
python .tools\voice\voice.py --list-presets
```

`script.json` 格式：

```json
{
  "fps": 30,
  "shots": [
    { "narration": "第一镜的旁白。" },
    { "narration": "第二镜的旁白。" }
  ]
}
```

输出：`audio/shot-XX.mp3`（每镜单独音轨，方便剪辑对齐）、`voice.mp3`（整条，含 0.35s 镜间停顿）、`subtitles.srt`、`props.json`（fps、每镜起止帧、时长）。

## 四、约定

- 固定用 `channel`；需要男声/快节奏时用 `male` / `youth`，但同一条视频里不要混用。
- 修改声线只改 `presets.json` 的 `voice/rate/pitch/chain`；`samples/` 里的样音重新生成一份存档。
- 合成缓存放在 `cache/`，可以随时删；不要提交到 git。
- 音色底是微软 edge 神经网络语音，是否商用请按微软服务条款自行确认（B 站同类教程普遍直接使用）。

## 五、参考

- [从夯到拉锐评剪映几个热门的 ai 配音（BV1bZBHBqEGW）](https://www.bilibili.com/video/BV1bZBHBqEGW)：吴敏霞 / 真人播客女 / 慢播讲故事 / 台湾腔甜妹等热门选项
- [当雾都夜话 OP 也有普通话版本（剪映 AI 配音:解说小帅，BV1861SBME38）](https://www.bilibili.com/video/BV1861SBME38)
- [Whipser 语音转文字 + edge_tts 文字转语音（BV1Cc411i7Yr）](https://www.bilibili.com/video/BV1Cc411i7Yr)
- [营销号 AI 配音哪里来的？微软 edge-tts（BV1gy4y1K7bz）](https://www.bilibili.com/video/BV1gy4y1K7bz)
- [5 分钟学会克隆声音，本地运行 GPT-SoVITS（BV1GZ421h7Zb）](https://www.bilibili.com/video/BV1GZ421h7Zb)
- [解说猫 TTS：indextts2 / 火山豆包 / 阿里云 / edge 对比（BV15QdAB6E22）](https://www.bilibili.com/video/BV15QdAB6E22)
- [赛博女友，完美变声，如今 AI 语音有多超乎想象（BV1uM411t7ZJ）](https://www.bilibili.com/video/BV1uM411t7ZJ)
