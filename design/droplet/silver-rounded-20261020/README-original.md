# 水滴探测器 · GoTogether 素材包

按《三体》水滴意象制作的银色镜面探测器。根据最新修订要求，整体收短、头部更饱满、尾巴缩短，形成更圆润紧凑的水滴；仍为左圆头、右尖尾的横向侧视，表面光滑无机械分缝，保留轻微悬浮感与半透明软阴影。与现有车辆采用相同的 640 × 440 透明画布。

这是可直接用于网页的 **二维 2.5D 精灵图**，不是可旋转 3D 网格、CAD 模型或影视官方设定图。本包不代表《三体》相关权利人的官方授权。

## 文件

- `static/vehicles/droplet/default.webp`：网页主图，640 × 440，真实 Alpha，无损 WebP，约 84 KiB。
- `design/droplet-silver-20261020/default.png`：640 × 440 透明 PNG；解码后的 RGBA 像素与 WebP 完全一致。
- `design/droplet-silver-20261020/generated.png`：1512 × 1040 高分辨率圆润版透明生成图，未重绘、未替换透明通道。
- `design/droplet-silver-20261020/prompt.txt`：完整生成提示词。
- `design/droplet-silver-20261020/sources.json`：生成方式、风格参考、路径和来源边界。
- `design/droplet-silver-20261020/export-qa.json`：尺寸、透明度、裁切、缩放、像素一致性和 SHA-256 校验记录。
- `preview/droplet-preview.jpg`：浅底展示图；底色仅用于预览。
- `preview/droplet-contact-sheet.jpg`：浅底、深底、透明棋盘和 180px 缩略图验收。
- `preview/droplet-before-after.jpg`：同画布比较上一版长尾水滴与本版短圆水滴。
- `design/droplet-silver-20261020/history/`、`prompt-v1.txt`、`prompt-v2.txt`：保留前两版原图、PNG 和提示词，供追溯；生产路径使用本次圆润新版。
- `export_assets.py`：可重复导出脚本，仅裁切、等比缩放、补齐画布、转换格式和生成预览；不调用生成模型，不修改应用。

原图与本次编辑均使用内置图像生成完成。修订版 Alpha 范围为 0–255，导出忠实保留透明信息，未把半透明边缘或阴影硬化。脚本中的 Alpha > 10 仅用于寻找裁切范围，不用于抠图。四角完全透明，浅色和深色界面均已视觉检查。

## 接入 GoTogether（本包尚未实施）

接入参考基线：默认分支提交 `4b6762b1f91f13a5260935cdd10fd0ff762b4a03`，数据库 v9。这是本次任务提供的源码核对基线；本包制作期间未重新拉取或修改仓库，未读取真实数据库。实际实施前先读目标分支、`AGENTS.md`、现有迁移和版本入口。

### 1. 放置资源并登记选项

- 将本包 `static/vehicles/droplet/` 与 `design/droplet-silver-20261020/` 合并到项目同路径；不要覆盖整个 `static/` 或 `design/` 目录。
- 车型 ID：`droplet`；外观文件：`default.webp`；中文名称建议“水滴探测器”。
- 在 `store.py` 的 `VEHICLE_APPEARANCES` 中增加 `'droplet': '水滴探测器'`，保留所有已有车型和原默认值。
- 当前只有银色默认外观，不需新加色卡或 `VEHICLE_COLORS` 条目。现有路径约定应让 `vehicle_image('droplet')` 指向 `vehicles/droplet/default.webp`，实施时核对实际辅助函数。
- JPG 只供审阅，不要当成主图。页面为图片提供“水滴探测器”替代文本和可见车型名。

### 2. 同步新库 CHECK、旧库迁移和初始化版本

仅放置图片、增加字典不足以完成接入。

- 在 `schema.sql` 的 `vehicles.appearance CHECK` 中追加 `droplet`，保留目标分支完整枚举，尤其是可能已接入的 `ct5`、`han`、`mazda929` 等。
- 为旧库新增顺序迁移，不能只改 `schema.sql`。不要改写已执行的迁移，也不要删库重建来绕过升级。
- 可参考项目 v8/v9 的迁移模式：增加含完整车型 CHECK 的 `appearance_vN` 列，复制旧值，移除旧列，重命名新列，设置 `PRAGMA user_version=N`。必须保留已有默认值、车辆编号、活动、乘客关系与颜色数据，并沿用项目事务处理和 SQLite 版本要求。
- 参考基线最高迁移为 9，因此当时下一编号是 10。**合并前重新检查；CT5、汉、Mazda 929 或其他改动可能已占用 migration_10.sql。使用实际下一编号，不能覆盖或重复使用版本，也不能丢掉前次新增车型。**
- 同步 `schema.sql` 的 `PRAGMA user_version`、`store.py` 中 `initialize()` 的可升级旧版本范围、迁移循环终点和最终版本校验。该基线没有独立的 `initializeVersion` 函数。
- 仅当目标实际仍是 v10 时，迁移循环终点应包含迁移 10（例如 `range(version + 1, 11)`），最终版本校验及新建库版本均应为 10；目标为更高版本时全部统一为实际值。
- 同步根目录 `README.md` 的车型与版本说明、`design/README.md` 的资源来源以及相关测试断言；总车型/图片数按实际合并后的结果更新，不直接沿用旧计数。

### 3. 验收

- 升级前按项目现有备份流程保留数据库和 `instance/`。
- 在临时库验证全新建库、v9 至实际目标版本升级、较早版本连续升级，检查 `PRAGMA user_version` 与 `PRAGMA foreign_key_check`。
- 新增、编辑、保存、再次打开“水滴探测器”记录；确认车型选择、活动页主图、管理员修改与错误回显均正常。
- 检查旧车型/颜色仍可保存、旧记录与乘客关联保持不变。
- 检查 640 × 440、浅/深背景和约 180px 移动端显示。尖尾不应被布局裁掉，必要时使用 `object-fit: contain`。
- 按项目规则和授权执行应用测试、启动或部署。本包仅通过图像导出与视觉验收，不代表项目接入已完成。

## 视觉与来源说明

- 设计要求来自本次资源制作任务：银色镜面、圆头尖尾、无缝表面、轻悬浮软阴影、无轮子/机械面板/喷焰/文字。后续先要求“形状更加规整，并且横着不是倾斜着”，再要求“我感觉不需要这么宽，整体圆润一点”；因此本版保持横向，同时明显收短、增加头部饱满度并缩短尖尾。
- 透明画布和写实质感参照此前制作的黑色 CT5、红色汉和黑色 Mazda 929 HC 图片；首版采用车辆式斜向视角，修订版依照最新要求改为水平侧视。没有把车辆图改绘成水滴。
- 未复用影片画面、演员肖像、第三方水滴渲染图或官方标志；本包为 AI 生成的主题演绎，不承诺与某一影视/动画版本逐项一致。名称和作品相关权利归各权利人所有。
- 生成工具：内置图像生成；没有调用 CLI/API，也不需要用户 API Key。

源码参考链接：

- https://github.com/IcarusLight/GoTogether/commit/4b6762b1f91f13a5260935cdd10fd0ff762b4a03
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/store.py
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/schema.sql
- https://github.com/IcarusLight/GoTogether/blob/4b6762b1f91f13a5260935cdd10fd0ff762b4a03/migrations/migration_9.sql

制作日期：2026-10-20。

## 修订记录

第二版（2026-10-20，历史版本）：通过内置图像编辑调整原图方向和形状；没有用后期旋转或几何变形模拟本次修改。成品仍为 640 × 440。以主体高 Alpha 轮廓逐列中点进行栅格近似测量，中心轴拟合偏角约 0.10°，中线高度跨度约 2px；视觉上为水平，上下轮廓基本对称。该测量用于图像验收，不表示 CAD 级精确对称。图片、预览、原图和完整包均更新原 Library 文件版本，保留历史。

第三版（2026-10-20，当前版本）：通过内置图像编辑重塑头部与尾部，主体长高比从上一版约 4.3:1 降至约 2.34:1。导出时等比缩放至 560px 最大内容框并居中于原 640 × 440 画布，主体约宽 537px、高 230px，左右各约 51px 留白；不采用非等比挤压。图像轴线近似偏角约 0.69°，视觉保持横向，不宣称工程级对称。浅/深背景、真实 Alpha、完整轮廓和 180px 缩略图均已检查。PNG/WebP 解码像素一致。
