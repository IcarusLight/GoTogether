# Roadster Rocket · GoTogether 悬浮车辆资源包

银灰色、前侧 3/4 轻俯视的二维写实精灵。车头朝左下；车身水平悬浮，车轮保持正常竖直姿态；独立地影与短促半透明白色冷气流表现离地感，没有火焰。

车型外形参考截至 2026-10-20 的 Tesla 官方新款 Roadster 页面：楔形机身、贯穿前灯带、深色窄座舱、主动尾翼。不是 2017 年圆润版 Roadster。此为 AI 绘制的游戏美术演绎，细节并非工程复刻，不是官方资产、可旋转 3D 模型，也不证明实车量产配置或道路使用许可。

## 一、文件怎么用

所有运行时图片均为 **640 × 440**，真实透明 Alpha；分层的左上角、画布尺寸与缩放比例一致。

| 文件 | 用途 |
|---|---|
| `static/vehicles/roadsterRocket/default.webp` | 已合成的静态主图，含车身、地影和气流 |
| `static/vehicles/roadsterRocket/car.webp` | 纯车身，不含地影与气流 |
| `static/vehicles/roadsterRocket/shadow.webp` | 独立地面阴影 |
| `static/vehicles/roadsterRocket/gas.webp` | 独立冷气流，两处气流已对齐 |
| `design/roadster-rocket-silver-20261020/*.png` | 上述四张对应的透明 PNG |
| `design/roadster-rocket-silver-20261020/aligned-2x/` | 四张 1280 × 880 对齐 PNG |
| `design/roadster-rocket-silver-20261020/sources/` | 三张未经重绘的原始生成图，保留原始 Alpha |
| `design/roadster-rocket-silver-20261020/sources.json` | 参考来源、裁切框、定位与叠加信息 |
| `design/roadster-rocket-silver-20261020/export-qa.json` | 尺寸、透明度、WebP 一致性与校验摘要 |
| `design/roadster-rocket-silver-20261020/prompts.txt` | 生成提示词 |
| `preview/Roadster-Rocket-预览.jpg` | 浅底、深底与分层展示 |
| `preview/Roadster-Rocket-QA.jpg` | 浅底、深底、透明棋盘与 180px 缩略检查 |
| `demo/Roadster-Rocket-悬浮演示.html` | 自包含离线演示，双击可打开，无需联网 |
| `export_assets.py` | 可复现的裁切、缩放、叠加与导出脚本 |

原始车身为 1536 × 1024，气流为 1024 × 1536，阴影为 1774 × 887。2x 文件是对齐的高分辨率工作图，不是新生成的 4K 图或 PSD。WebP 使用无损编码，解码后 RGBA 与对应 PNG 完全一致。

### 静态模式

直接使用 `default.webp`。它已经包含全部效果，不要再叠加 shadow 或 gas，也不要再额外给图片套 CSS `drop-shadow`，否则会产生双重阴影。

### 动态模式

按从下到上顺序叠加：**shadow → gas → car**。三张都铺满同一个 16:11 容器，保持 `inset: 0; width: 100%; height: 100%; object-fit: contain`。

- 将 car 与 gas 放入同一个移动容器，轻微上下浮动即可。演示默认周期 3.6 秒、上移幅度为画布高度的 1.5%（640 × 440 时约 6.6px）。
- shadow 留在地面，只轻微调整透明度与大小，不随车身上浮。
- gas 层可轻微变化透明度，不做喷火、强烈闪烁或长尾喷射。
- 不要把 default 叠到分层上。也不要分别裁掉透明留白，否则位置会错。
- 尊重 `prefers-reduced-motion`；演示已包含自动关闭动画和手动暂停。
- 演示内使用图片数据，不依赖 CDN、脚本库或后台服务。它是资源验收页，不是已接入的网站。
- HTML 已检查内嵌图片、脚本语法与引用；本次云浏览器未能启动，因此交互效果尚未做浏览器实测。PNG/WebP 的视觉与像素校验已完成。

## 二、接入 GoTogether（尚未实施）

建议车型 ID：`roadsterRocket`；默认外观 ID：`default`；显示名称：“Roadster Rocket”。命名是本包建议，实施时保持后端、数据库、图片目录和前端完全一致。

本包只制作资源，没有修改仓库、运行迁移、读取真实数据库或部署。接入说明沿用本轮已核对的仓库基线：

- 仓库：https://github.com/IcarusLight/GoTogether
- 参考提交：`4b6762b1f91f13a5260935cdd10fd0ff762b4a03`
- 该基线数据库版本为 v9。**实际接入前重新检查目标分支、AGENTS.md、现有迁移和真实数据库版本；其他车型可能已经占用后续迁移号。**

### 1. 合并资源与登记车型

1. 将本包 `static/vehicles/roadsterRocket/` 合并进项目同路径；按项目习惯保留 design 目录。不要覆盖整个 static 或 design 目录。
2. 在 `store.py` 的 `VEHICLE_APPEARANCES` 登记新 ID 与名称，保留原车型、默认值和已有颜色设置。
3. 这是单一默认银灰外观；不用为了它额外增加颜色字段。核对 `vehicle_image` 等图片辅助函数能生成 `vehicles/roadsterRocket/default.webp`。
4. 检查车型下拉、皮肤映射、编辑表单、预览、活动页与管理员页面是否有额外白名单；需要时同步登记。
5. 若只要静态图，无需引入动画容器。若要轻悬浮动画，在该车型渲染分支使用三层图片；保留静态图作为回退。

### 2. 同步数据库与版本升级

**只复制图片并增加车型字典不足以完成接入。**

- 在 `schema.sql` 的 `vehicles.appearance CHECK` 完整枚举中追加 `roadsterRocket`，保留目标分支所有旧值。
- 为已存在的数据库新增顺序迁移，更新 CHECK；不能仅修改新建库 schema，也不能改写已执行的迁移或删除数据库绕过升级。
- 可参考项目原有 v8/v9 的迁移模式：新增带完整 CHECK 的临时外观列 → 复制原值 → 移除旧列 → 重命名 → 设置 `PRAGMA user_version`。实施时遵循项目事务和 SQLite 版本要求，并保留所有车辆、活动、乘客关系和颜色数据。
- `migration_10.sql` 只是 v9 基线当时的下一候选号，**不能盲目使用 10**。CT5、汉、Mazda 929、水滴或其他工作可能已先合并，必须采用实际下一编号，完整保留这些车型。
- 同步 `schema.sql` 的 `PRAGMA user_version` 和 `store.py` 中 `initialize()` 的可升级版本范围、迁移循环终点、最终版本校验。不要只改某一个数字。
- 同步项目 README、资源来源说明及相关版本/车型测试。具体总车型数按实际合并结果计算。

### 3. 验收清单

- 先按项目既有流程备份数据库与 `instance/`。
- 在临时库验证新建库、已有库升级、较早版本连续升级；核对 `PRAGMA user_version` 和 `PRAGMA foreign_key_check`。
- 新增、编辑、保存并再次打开 Roadster Rocket；检查车型选择、管理员修改与错误回显。
- 检查旧车型、旧颜色和乘客关联保持不变。
- 检查透明图片 URL、640 × 440 显示、浅/深界面和 180px 缩略图；显示名称与替代文本不能只依赖车标。
- 动画模式下确认地影不会随车升降、车与气流对齐、暂停有效，并且没有重复叠加 default。
- 根据实际授权运行应用测试或部署。包内图像验收通过不代表应用接入测试已经通过。

## 三、来源与边界

- 官方外形参考：https://www.tesla.com/roadster?redirect=no
- 新款发布报道：https://www.caranddriver.com/news/a74145531/tesla-roadster-revealed/
- 官方正面照片与侧面照片的确切链接记录于 sources.json；第三方参考照片未打包再分发。
- 官方照片用于核对新款楔形轮廓；先前 GoTogether 黑色 CT5 资源只用于镜头角度和质感参考。
- Rocket 的冷气流和悬浮只做克制的视觉表达；喷口、轮毂、尾翼和座舱细节不构成特定实车配置保证。
- 三个视觉源均通过内置图像生成工具制作。后期仅做边界裁切、缩放、透明叠加、定位、格式转换和预览排版，没有用程序重画车身或从实车照片抠取主体。
- 原始 Alpha 的低阈值只用于查找裁切框，不用于二值化抠图。原始 PNG 保存在 sources 中，导出保留半透明边缘。
- 名称、品牌及相关标识归各权利人所有；本包不表示 Tesla 授权或合作。

制作日期：2026-10-20。

重新运行导出脚本需要 Python 3、Pillow；预览排版使用 Noto Sans CJK 字体。运行时静态图片及 HTML 不需要这些依赖。
