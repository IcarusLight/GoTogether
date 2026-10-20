# 黑色 Mazda 929 HC · GoTogether 车辆素材

1980 年代后期 Mazda 929 HC 四门三厢轿车的写实 2.5D 透明精灵。车头朝左下、前侧 3/4、轻俯视；黑车漆、矩形大灯、横条格栅、镀铬细节及年代感原厂轮盖。

设计借用了《黑金》“开马自达塞车”的怀旧氛围，但未核实影片中的具体车款，因此不将本素材标注为“电影同款”或电影道具复刻。图片不含梗字、人物或片中画面。

## 文件与规格

- `static/vehicles/mazda929/default.webp`：网页主图，640 × 440，真实 Alpha，无损 WebP。
- `design/mazda929-black-20261020/default.png`：同尺寸透明 PNG；解码后与 WebP 的 RGBA 像素一致。
- `design/mazda929-black-20261020/generated.png`：1536 × 1024 原始透明生成图，保留原始 Alpha。
- `design/mazda929-black-20261020/prompt.txt`：完整生成提示词，明确区分风格参考与车型参考。
- `design/mazda929-black-20261020/sources.json`：来源、相对路径、导出参数与使用说明；`pathBase` 为 `project-root`。
- `design/mazda929-black-20261020/export-qa.json`：透明度、尺寸、像素等同性及摘要值的机器校验记录。
- `preview/mazda929-preview.jpg`：浅色背景展示图，背景仅用于预览。
- `preview/mazda929-contact-sheet.jpg`：浅/深/棋盘背景和 180px 缩略验收。
- `export_assets.py`：仅做裁切、等比缩放、补齐画布、格式导出与预览拼版的可重复脚本。

原图由内置图像生成制作；未用后期画笔重绘车身。PNG/WebP 保留半透明接触阴影与抗锯齿边缘。原图主体的 Alpha 最高为 254，导出忠实保留，没有人为把半透明边缘硬化成不透明。

## 接入 GoTogether（尚未实施）

源码核对日期：2026-10-20 02:40 UTC。默认分支 master 提交：`4b6762b1f91f13a5260935cdd10fd0ff762b4a03`；当时数据库版本为 **v9**，共有 10 种车型、15 张主图。本包没有读取本地未推送内容或真实数据库，没有修改仓库、执行应用测试、迁移、启动或部署。实施时先读目标分支与 `AGENTS.md`，以实际代码为准。

### 1. 合并资源并登记车型

- 将本包 `static/vehicles/mazda929/` 和 `design/mazda929-black-20261020/` 合并到项目同路径，勿用整个 `static/` 或 `design/` 覆盖旧目录。
- 车型 ID 为 `mazda929`，默认外观 ID 为 `default`。
- 在 `store.py` 的 `VEHICLE_APPEARANCES` 增加 `'mazda929': '马自达 929'`，保留已有车型与默认 `su7`。
- 当前仅一款默认黑色，无需 `VEHICLE_COLORS` 条目、`black.webp` 或色卡。现有 `vehicle_image('mazda929')` 会生成 `vehicles/mazda929/default.webp`，无需路径特判。
- `preview/` 是审阅图片，勿拿带底色的 JPG 替代透明主图。

### 2. 新建库 CHECK 与旧库迁移必须同时更新

- 在 `schema.sql` 的 `vehicles.appearance CHECK` 中追加 `mazda929`。保留实际目标分支全部原有枚举，尤其是可能已接入的 `ct5`、`han` 等。
- 同步 `schema.sql` 末尾 `PRAGMA user_version`。
- **为旧数据库新增顺序迁移，不可仅改 schema.sql，不可改写已执行的迁移，也不可删除旧库来绕过升级。**
- 可沿用现有 v8/v9 的做法：增加带完整车型 CHECK 的 `appearance_vN` 列 → 复制原 `appearance` → 删除旧列 → 新列重命名 → 设置 `PRAGMA user_version=N`。保留原默认值、车辆编号、活动、乘客关联及原有车型/颜色数据。
- 核对时最高迁移为 9，因此当时下一个可用编号为 10。**实际合并前重新检查：如果 CT5、汉或其他改动已占用 migration_10.sql，使用下一版本，不能覆盖、重复使用该编号或丢掉前次新增车型。**
- 沿用项目事务封装和 SQLite ≥ 3.35 的检查。

### 3. 同步 initialize() 的版本入口

项目入口在 `store.py` 的 `initialize()`，没有独立的 `initializeVersion` 函数。旧版本兼容分支、迁移循环终点、最终版本校验和新建库版本必须一致。

仅当接入时目标确认仍为 v10：

- 允许版本 1–9 升级（现基线只列到 8）。
- 迁移循环从 `range(version + 1, 10)` 改为 `range(version + 1, 11)`。
- 最终版本判断从 `version != 9` 改为 `version != 10`。
- 新迁移与 `schema.sql` 都设 `PRAGMA user_version = 10`。

若目标已变为其他版本，以上位置统一使用实际版本。同步根目录 `README.md` 的车型、数据库版本及升级范围；同步 `tests/test_app.py` 的版本/车型断言；在 `design/README.md` 主图表登记新增资源与来源。只有本次单独新增一款时，总数才由 10 种/15 张变成 11 种/16 张。

### 4. 验收清单

- 升级前按项目现有 `backup.cmd` 流程备份并保留 `instance/`。
- 在临时库分别验证：全新建库、v9→目标版本、较早版本连续升级；检查 `PRAGMA user_version` 和 `PRAGMA foreign_key_check`。
- 验证新增/编辑/再次打开 Mazda 929 记录成功，旧车记录、颜色、车辆编号与乘客引用保持不变。
- 验证车型选择、主图 URL、预览、保存后的活动页、管理员修改、错误回显与切换回旧车型。
- 验证 640×440、浅色和深色背景、约 180px 移动端缩略。缩略图不能可靠展示细小徽标，界面另配“马自达 929”文字及图片替代文本。
- 按项目规则与实际授权运行测试、启动或部署。本包的通过项仅限图像导出与人工视觉验收，不代表应用接入已通过。

**仅复制图片和增加车型字典不足以完成接入；遗漏 CHECK、旧库迁移或初始化版本同步，会导致保存失败或版本不匹配。**

## 可选界面文案

正式车型名建议“马自达 929”；副标签可用“黑色经典款”或“复古座驾”。如要加电影梗，可将“开马自达也准时”作为可选趣味文案，放在界面而不是图中，避免影响缩略识别。此处仅是建议，未写入项目。

## 来源、车型边界与使用说明

- Mazda 官方历史页记载第五代 Luce（929）于 1986 年 9 月推出；官方图片用于核对同代方正轮廓、前脸与年代特征。
- Wikimedia Commons 摄影者 OSX 的实车照片明确标注为 1988 Mazda 929（HC）sedan，用于核对矩形灯组、横条格栅、侧面折线、B 柱与轮盖。未采用 1991 年后的圆润 HD/Sentia 车身。
- 相机方向、透明底与质感参照本项目之前制作的黑色 CT5；汉 EV 图片用于整体视觉一致性检查。它们不是 Mazda 车型身份参考。
- 本素材是 AI 生成的二维图像，不是可旋转 3D 模型、工程复刻或精确配置档案。细节可能与特定年款/市场配置不同。
- 本包未再分发第三方参考照片。品牌及车型标识归各权利人所有，不代表官方授权或合作。

车型来源：

- https://www.mazda.com/en/about/history/1980-1989/
- https://www.mazda.com/content/dam/mazda/corporate/mazda-com/ja/images/about/history/1980-1989/luce_1986_09_ex_0211.jpg
- https://commons.wikimedia.org/wiki/File:1987-1989_Mazda_929_(HC)_sedan_(2011-04-28)_01.jpg

源码依据：

- https://github.com/IcarusLight/GoTogether/commit/4b6762b1f91f13a5260935cdd10fd0ff762b4a03
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/design/README.md
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/store.py
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/schema.sql
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/migrations/migration_9.sql

制作日期：2026-10-20。
