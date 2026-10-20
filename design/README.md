# 车辆与皮肤资源规范

本目录保留原图、参考图、提示词和历史稿；网站读取 `static/vehicles/` 中的成品。本文登记现有资源，并说明新增时需要更新的位置。

## 路径与命名

以下路径均相对于项目根目录。车辆 ID、外观 ID 使用小写英文、数字和连字符；中文名称由代码中的显示名称提供。

| 用途 | 路径规则 | 例子 |
| --- | --- | --- |
| 默认主图 | `static/vehicles/<车辆ID>/default.webp` | `static/vehicles/yadea/default.webp` |
| 颜色或皮肤主图 | `static/vehicles/<车辆ID>/<外观ID>.webp` | `static/vehicles/yadea/meituan.webp` |
| 颜色样本 | `static/vehicles/<车辆ID>/swatches/<外观ID>.png` | `static/vehicles/su7/swatches/default.png` |
| 设计素材批次 | `design/<车辆ID>/<主题>-<YYYYMMDD>/` | `design/yadea/meituan-20261015/` |
| 多车型对比 | `design/comparisons/<日期或批次>/` | `design/comparisons/20261014-batch2/` |

默认外观固定使用 `default`。车辆 ID 和外观 ID 已用于保存用户选择，调整名称时保留 ID；确需改 ID 时同时处理已有数据和引用。

设计资源先按车型分类，再按主题和日期分批。每款车的原图、参考图、SVG 历史稿、提示词和导出记录放在同一车型目录下；文件名保留版本信息。`comparisons/` 只保存跨车型的对比页、拼图、渲染脚本和汇总索引，通过相对路径引用各车型素材。

当前目录包括 `phantom/`、`tricycle/`、`su7/`、`v800/`、`kart/`、`yadea/`、`horse-carriage/`、`wuling/`、`dayun/`、`mega/`、`ct5/`、`han/`、`mazda929/`、`droplet/`。SU7 的早期研究与官方配色分别位于 `su7/study-20261014/` 和 `su7/official-colors-20261014/`；雅迪原版与外卖皮肤分别位于 `yadea/study-20261014/` 和 `yadea/meituan-20261015/`；黑色 CT5 位于 `ct5/black-20261020/`；比亚迪汉及滴滴涂装位于 `han/skins-20261020/`；黑色马自达 929 HC 位于 `mazda929/black-20261020/`；银色三体水滴当前使用 `droplet/silver-rounded-20261020/` 的横向圆润版，初版斜向长尾素材保留在 `droplet/silver-20261020/`。

历史对比入口：[首批车型](comparisons/20261014/selected-preview-v2.html)、[首批图片与 SVG 对照](comparisons/20261014/preview-v1.html)、[第二批车型](comparisons/20261014-batch2/preview.html)。

## 图片规格与导出

| 项目 | 规范 |
| --- | --- |
| 网站主图 | WebP，640 × 440，保留真实 Alpha 透明通道 |
| 色卡 | PNG，140 × 140，界面按 28 × 28 显示 |
| 构图 | 完整车辆，等比缩放，主体朝向与同车型现有图片一致，车轮、后视镜、箱体不裁切 |
| 同车型变体 | 使用一致的视角、主体比例和画布位置；颜色变化尽量沿用相同裁切与留白 |
| 背景 | 透明；预览用的草地、浅色或深色背景不烘焙进成品 |
| 原图 | 保留原始分辨率和格式，导出写入新文件，不覆盖原图 |
| 压缩 | 文字、标志和细边缘优先考虑无损 WebP；其他图片按画质选择有损参数，并记录实际参数 |

先裁掉多余透明留白，再等比缩放和补透明画布；已有同车型导出参数时优先沿用。原图比例合适且构图已确认时，可以直接等比缩放整张画布。不要拉伸车辆以凑尺寸。

导出后核对格式、尺寸和透明通道，并在浅色、深色背景及页面常见缩略尺寸下检查轮廓、文字与主体位置。文件体积没有硬性上限；若明显大于同类成品，检查是否误用高清原图或带入无用内容。

## 当前主图对应表

共 14 种车辆、20 张在用主图。成品列相对于 `static/vehicles/`，原图与记录列相对于 `design/`。原图指实际用于导出成品的生成图；照片、官网配色图等参考材料见对应记录。

| 车辆／外观 | 成品 | 原图 | 提示词、来源与导出记录 |
| --- | --- | --- | --- |
| 劳斯莱斯幻影 | `phantom/default.webp` | `phantom/study-20261014/raster/phantom.png` | `phantom/study-20261014/sources.json`，`items[id=phantom]` |
| 农用三蹦子 | `tricycle/default.webp` | `tricycle/study-20261014/raster/tricycle-rustic-v2.png` | `tricycle/study-20261014/sources.json`，`items[id=tricycle]`，使用 `currentPrompt` |
| 小米 SU7／卡布里蓝 | `su7/default.webp` | `su7/official-colors-20261014/generated-capri-blue.png` | 同批次 `sources.json`、`prompts.json`，提示词键 `capri-blue` |
| 小米 SU7／霞光紫 | `su7/sunset-purple.webp` | `su7/official-colors-20261014/generated-sunset-purple.png` | 同批次 `sources.json`、`prompts.json`，提示词键 `sunset-purple` |
| 小米 SU7／雅灰 | `su7/elegant-gray.webp` | `su7/official-colors-20261014/generated-elegant-gray.png` | 同批次 `sources.json`、`prompts.json`，提示词键 `elegant-gray` |
| 小米 SU7／珍珠白 | `su7/pearl-white.webp` | `su7/official-colors-20261014/generated-pearl-white.png` | 同批次 `sources.json`、`prompts.json`，提示词键 `pearl-white` |
| 小米 SU7／曜石黑 | `su7/obsidian-black.webp` | `su7/official-colors-20261014/generated-obsidian-black.png` | 同批次 `sources.json`、`prompts.json`，提示词键 `obsidian-black` |
| 尊界 V800 | `v800/default.webp` | `v800/study-20261014/v800.png` | 同批次 `v800-prompt.json`、`web-assets.json` |
| 卡丁车 | `kart/default.webp` | `kart/study-20261014/kart-v2.png` | 同批次 `kart-prompt.json`、`web-assets.json` |
| 雅迪／原版 | `yadea/default.webp` | `yadea/study-20261014/yadea-v2.png` | 同批次 `yadea-prompt.json`、`web-assets.json` |
| 雅迪／美团外卖 | `yadea/meituan.webp` | `yadea/meituan-20261015/yadea-meituan.png` | 同批次 `yadea-meituan-prompt.json`；编辑输入为 `static/vehicles/yadea/default.webp` |
| 宝马马车 | `horse-carriage/default.webp` | `horse-carriage/study-20261014/horse-carriage-v2.png` | 同批次 `horse-carriage-prompt.json`、`web-assets.json` |
| 五菱宏光 | `wuling/default.webp` | `wuling/study-20261014/wuling.png` | 同批次 `prompt.json` |
| 大运卡车 | `dayun/default.webp` | `dayun/study-20261014/dayun.png` | 同批次 `prompt.json` |
| 理想 MEGA | `mega/default.webp` | `mega/study-20261014/mega.png` | 同批次 `prompt.json`；本地归档与原生成文件 SHA-256 一致 |
| 凯迪拉克 CT5／黑色 | `ct5/default.webp` | `ct5/black-20261020/generated.png` | 同批次 `sources.json`、`prompt.txt`；交付说明原文保存在 `README-original.md` |
| 比亚迪汉／红色原版 | `han/default.webp` | `han/skins-20261020/sources/han-red-source.png` | 同批次 `sources.json`、`docs/red-prompt.txt`、`docs/export-qa.json` |
| 比亚迪汉／滴滴出行 | `han/didi.webp` | `han/skins-20261020/sources/han-didi-source.png` | 同批次 `sources.json`、`docs/didi-v2-prompt.txt`、`docs/export-qa.json`；原包来源记录保存在 `sources-original.json` |
| 马自达 929 HC／黑色 | `mazda929/default.webp` | `mazda929/black-20261020/generated.png` | 同批次 `sources.json`、`prompt.txt`、`export-qa.json`；原包来源与说明保存在 `sources-original.json`、`README-original.md` |
| 三体水滴／银色横向圆润版 | `droplet/default.webp` | `droplet/silver-rounded-20261020/generated.png` | 同批次 `sources.json`、`prompt.txt`、`export-qa.json`；原包来源、清单与说明保存在 `sources-original.json`、`manifest-original.json`、`README-original.md` |

SU7 的 `capri-blue.png`、`sunset-purple.png` 等不带 `generated-` 前缀的图片是配色参考图，导出车辆主图使用表中的生成图。

## 色卡与历史资源

SU7 色卡是直接使用的官方 `goodsImg` PNG，当前成品自身就是留存的源文件，没有单独的高清源图副本。来源接口及请求 ID 记录在 `su7/official-colors-20261014/sources.json` 的 `officialSwatches` 中；现有记录未保存每张色卡的独立下载 URL。

| 颜色 | 源文件／网站成品（相对于 `static/vehicles/`） |
| --- | --- |
| 卡布里蓝 | `su7/swatches/default.png` |
| 霞光紫 | `su7/swatches/sunset-purple.png` |
| 雅灰 | `su7/swatches/elegant-gray.png` |
| 珍珠白 | `su7/swatches/pearl-white.png` |
| 曜石黑 | `su7/swatches/obsidian-black.png` |

旧版 SU7 的生成原图为 `design/su7/study-20261014/raster/su7.png`，旧成品为同批次的 `su7-legacy.webp`，来源和提示词见同批次 `sources.json`。它用于历史设计参考，当前默认车辆图使用上表的卡布里蓝版本。未选中的初稿和 SVG 探索稿随车型归档，跨车型预览拼图放在 `comparisons/` 的对应批次。

## 新增时的记录格式

每个新批次放一份 `sources.json`，至少写清车辆 ID、外观 ID、原图、成品、提示词或提示词文件、参考来源和导出参数。新记录中的本地路径统一相对于项目根目录；记录文件显式声明 `pathBase`。旧记录保留各自已有的相对路径语义。

```json
{
  "pathBase": "project-root",
  "vehicleId": "yadea",
  "variantId": "new-skin",
  "sourceFile": "design/yadea/new-skin-20261015/generated.png",
  "productionFile": "static/vehicles/yadea/new-skin.webp",
  "promptFile": "design/yadea/new-skin-20261015/prompt.json",
  "references": [],
  "export": {
    "width": 640,
    "height": 440,
    "format": "webp",
    "lossless": true,
    "resize": "Lanczos, full canvas, preserve alpha"
  }
}
```

以上为填写示例，实际参数按制作过程记录。有参考材料时，在 `references` 中补上 URL、本地副本和已知授权信息；未知项如实注明。发生裁切、补边或有损压缩时，补充裁切区域、留白和质量参数。生成工具的临时绝对路径可作为历史信息保留，同时必须给出仓库内的原图路径。

## 接入步骤

1. 确定车辆及外观 ID，将原图、参考材料和制作记录放入 `design/<车辆ID>/<主题>-<YYYYMMDD>/`，按规格导出到 `static/vehicles/`。多车型对比资料单独放入 `design/comparisons/`，引用各车型目录中的素材。
2. 新增车辆时更新 `store.py` 的 `VEHICLE_APPEARANCES`、`schema.sql` 中的车辆枚举约束，并为已有数据库新增迁移；同步数据库版本及升级说明。不要修改已执行迁移来替代新迁移。
3. 新增颜色或皮肤时更新 `VEHICLE_COLORS`，保留 `default` 项。已有车辆新增外观通常无需数据库迁移；颜色和皮肤 ID 共用 `vehicles.color` 字段。
4. 检查选择器行为。模板和保存逻辑共用 `store.py` 的 `VEHICLE_SKIN_FIELDS` 映射，雅迪使用 `skin`，比亚迪汉使用 `skin_han`；新车型增加皮肤时登记独立的表单字段。颜色选项需要对应色卡，皮肤选项使用车辆缩略图。新增车型专属提示时同步调整 `templates/travel.html`。
5. 主图 URL 统一通过 `vehicle_image()` 生成，前端预览读取模板输出的 URL。保持规定路径时无需增加文件路径特判。
6. 更新本文对应表及批次来源记录，检查本地路径、图片规格、缩略图效果与代码差异。测试和应用启动遵守项目 `AGENTS.md` 的授权规则。
